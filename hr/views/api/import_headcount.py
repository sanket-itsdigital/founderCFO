import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from django.core.exceptions import ValidationError
from openpyxl import load_workbook
from openpyxl.utils.datetime import from_excel
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Company
from hr.enums import EmploymentStatus, EmploymentType, Gender, Level
from hr.models.headcount import Headcount
from hr.models.department import Department
from hr.models.role import Role
from sales.views.api.utils import get_company_from_request


@dataclass
class ImportResult:
    """Result of Excel import operation"""

    created: int = 0
    updated: int = 0
    skipped: List[Tuple[int, str]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class HeadcountImportError(Exception):
    """Custom exception for headcount import errors"""

    pass


class HeadcountImportView(APIView):
    """
    Excel Import API for HR Headcount
    Accepts an Excel file and imports headcount data into the database.
    
    Expected Excel columns:
    1. name (required) - Employee name
    2. email (required) - Employee email
    3. department - Department name (will be created if doesn't exist)
    4. role - Role name (will be created if doesn't exist)
    5. level - Employee level (VP, Director, Manager, Lead, Senior, Mid, Junior)
    6. status - Employment status (Active, Resigned, Inactive)
    7. employment type - Employment type (Full-time, Part-time, Contractor, Intern)
    8. gender - Gender (Male, Female)
    9. location - Location
    10. salary annual (required) - Annual salary
    11. bonus percent - Bonus percentage
    12. benefit annual - Annual benefits
    13. start date (required) - Start date
    14. exit date - Exit/end date
    15. exit reason - Exit reason
    """

    permission_classes = [IsAuthenticated]

    # Mapping from Excel column names (various formats) to model field names
    EXCEL_TO_FIELD_MAPPING = {
        # Name
        "name": "name",
        # Email
        "email": "email",
        "emial": "email",  # Handle typo
        # Department
        "department": "department",
        # Role
        "role": "role",
        # Level
        "level": "level",
        "leve": "level",  # Handle typo
        # Status
        "status": "status",
        # Employment Type
        "employment type": "employment",
        "employment_type": "employment",
        "employmenttype": "employment",
        "employment": "employment",
        # Gender
        "gender": "gender",
        # Location
        "location": "location",
        # Salary Annual
        "salary annual": "salary_annual",
        "salary_annual": "salary_annual",
        "salaryannual": "salary_annual",
        "salary": "salary_annual",
        # Bonus Percent
        "bonus percent": "bouns_percent",
        "bonus_percent": "bouns_percent",
        "bonuspercent": "bouns_percent",
        "bounspercent": "bouns_percent",
        "bonus": "bouns_percent",
        # Benefit Annual
        "benefit annual": "benefits_annual",
        "benefit_annual": "benefits_annual",
        "benefitannual": "benefits_annual",
        "benefits annual": "benefits_annual",
        "benefits_annual": "benefits_annual",
        "benefits": "benefits_annual",
        # Start Date
        "start date": "start_date",
        "start_date": "start_date",
        "startdate": "start_date",
        # Exit Date
        "exit date": "end_date",
        "exit_date": "end_date",
        "exitdate": "end_date",
        "end date": "end_date",
        "end_date": "end_date",
        # Exit Reason
        "exit reason": "exit_reason",
        "exit_reason": "exit_reason",
        "exitreason": "exit_reason",
    }

    # Expected model field names (for validation)
    EXPECTED_COLUMNS = list(set(EXCEL_TO_FIELD_MAPPING.values()))

    # Required columns (model field names)
    REQUIRED_COLUMNS = [
        "name",
        "email",
        "salary_annual",
        "start_date",
    ]

    def post(self, request):
        """Import headcount from Excel file"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {
                    "error": "Company not found. Please provide company_id in query params."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if file is provided
        if "file" not in request.FILES:
            return Response(
                {
                    "error": "Excel file is required. Please provide 'file' in the request."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        uploaded_file = request.FILES["file"]

        # Validate file extension
        if not uploaded_file.name.endswith((".xlsx", ".xls")):
            return Response(
                {
                    "error": "Invalid file format. Please upload an Excel file (.xlsx or .xls)."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = self._import_headcount_from_excel(
                uploaded_file, company, request.user
            )

            response_data = {
                "success": True,
                "message": f"Import completed: {result.created} created, {result.updated} updated, {len(result.skipped)} skipped",
                "created": result.created,
                "updated": result.updated,
                "skipped_count": len(result.skipped),
                "skipped": [
                    {"row": row_num, "reason": reason}
                    for row_num, reason in result.skipped
                ],
            }

            if result.errors:
                response_data["errors"] = result.errors

            return Response(response_data, status=status.HTTP_200_OK)

        except HeadcountImportError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"error": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _import_headcount_from_excel(
        self, uploaded_file, company: Company, user
    ) -> ImportResult:
        """Read the Excel file and create/update Headcount records"""
        try:
            uploaded_file.seek(0)
        except (AttributeError, OSError):
            pass

        try:
            workbook = load_workbook(uploaded_file, data_only=True)
        except Exception as exc:
            raise HeadcountImportError(
                "Unable to read the uploaded Excel file."
            ) from exc

        if not workbook.sheetnames:
            raise HeadcountImportError(
                "The Excel file does not contain any sheets."
            )

        # Use the first sheet
        sheet = workbook[workbook.sheetnames[0]]

        if sheet.max_row < 2:
            raise HeadcountImportError("The sheet does not contain any data rows.")

        # Locate header row
        header_map, header_row_index = self._locate_header_row(sheet)
        if not header_map or header_row_index is None:
            raise HeadcountImportError(
                "Could not detect the header row. Please ensure the first row contains column headers."
            )

        # Check for required columns by normalizing Excel headers to field names
        normalized_headers = set()
        header_mapping_debug = {}  # For debugging
        for excel_header in header_map.values():
            field_name = self._normalize_excel_header(excel_header)
            if field_name:
                normalized_headers.add(field_name)
                header_mapping_debug[excel_header] = field_name

        missing_columns = [
            col for col in self.REQUIRED_COLUMNS if col not in normalized_headers
        ]
        if missing_columns:
            # Provide helpful error message with found headers
            found_headers = list(header_map.values())
            found_normalized = list(normalized_headers)
            error_msg = (
                f"Missing required columns: {', '.join(missing_columns)}. "
                f"Found Excel headers: {', '.join(found_headers[:10])}. "
                f"Mapped to fields: {', '.join(found_normalized[:10])}"
            )
            raise HeadcountImportError(error_msg)

        date1904 = bool(getattr(workbook.properties, "date1904", False))
        result = ImportResult()

        # Process data rows
        for row in sheet.iter_rows(min_row=header_row_index + 1, values_only=False):
            row_number = row[0].row
            if row_number <= header_row_index:
                continue

            # Extract row data
            row_payload = self._extract_row_payload(row, header_map)

            # Skip empty rows
            if self._row_is_empty(row_payload):
                continue

            # Transform row data
            try:
                headcount_data = self._transform_row_payload(
                    row_payload, date1904, company, user
                )
            except ValueError as exc:
                result.skipped.append((row_number, str(exc)))
                continue

            # Validate required fields
            missing_required = [
                field
                for field in ["name", "email", "salary_annual", "start_date"]
                if not headcount_data.get(field)
            ]
            if missing_required:
                result.skipped.append(
                    (
                        row_number,
                        f"Missing required values: {', '.join(missing_required)}",
                    )
                )
                continue

            # Create or update headcount
            try:
                created = self._persist_headcount(headcount_data, company, user)
                if created:
                    result.created += 1
                else:
                    result.updated += 1
            except ValidationError as exc:
                result.skipped.append(
                    (row_number, self._flatten_validation_error(exc))
                )
                continue
            except Exception as exc:
                result.skipped.append((row_number, str(exc)))
                continue

        return result

    def _normalize_excel_header(self, header: str) -> Optional[str]:
        """Normalize Excel header to model field name"""
        if not header:
            return None

        # Convert to string and clean up
        header_str = str(header).strip()
        if not header_str:
            return None

        # Normalize: lowercase, strip, replace multiple spaces with single space
        # Also remove any non-printable characters
        normalized = " ".join(header_str.lower().split())

        # Remove any special characters that might interfere (keep alphanumeric, spaces, underscores, slashes)
        normalized = re.sub(r"[^\w\s/]", "", normalized)
        normalized = " ".join(normalized.split())  # Clean up spaces again

        # Check direct mapping
        if normalized in self.EXCEL_TO_FIELD_MAPPING:
            return self.EXCEL_TO_FIELD_MAPPING[normalized]

        # Try replacing spaces with underscores
        normalized_underscore = normalized.replace(" ", "_")
        if normalized_underscore in self.EXCEL_TO_FIELD_MAPPING:
            return self.EXCEL_TO_FIELD_MAPPING[normalized_underscore]

        # Try removing spaces
        normalized_no_space = normalized.replace(" ", "").replace("/", "")
        if normalized_no_space in self.EXCEL_TO_FIELD_MAPPING:
            return self.EXCEL_TO_FIELD_MAPPING[normalized_no_space]

        return None

    def _locate_header_row(
        self, sheet
    ) -> Tuple[Optional[Dict[int, str]], Optional[int]]:
        """Locate the header row in the sheet"""
        # Check first 10 rows for headers
        for row_idx in range(1, min(11, sheet.max_row + 1)):
            row = sheet[row_idx]
            header_map = self._build_header_map(row)

            # Check if we found expected columns by normalizing Excel headers
            found_field_names = set()
            for excel_header in header_map.values():
                field_name = self._normalize_excel_header(excel_header)
                if field_name:
                    found_field_names.add(field_name)

            # If we found at least the required columns, consider this the header row
            required_found = sum(
                1 for col in self.REQUIRED_COLUMNS if col in found_field_names
            )

            if required_found >= len(self.REQUIRED_COLUMNS):
                return header_map, row_idx

        return None, None

    def _build_header_map(self, header_row) -> Dict[int, str]:
        """Build a map of column index to header name"""
        header_map: Dict[int, str] = {}
        for cell in header_row:
            if cell.value:
                # Normalize header name (strip whitespace)
                header_name = str(cell.value).strip()
                header_map[cell.column] = header_name
        return header_map

    def _extract_row_payload(
        self, row, header_map: Dict[int, str]
    ) -> Dict[str, any]:
        """Extract data from a row based on header map, converting Excel headers to model field names"""
        payload = {}
        for cell in row:
            if cell.column in header_map:
                excel_header = header_map[cell.column]
                # Normalize Excel header to model field name
                field_name = self._normalize_excel_header(excel_header)
                if field_name:
                    payload[field_name] = cell.value
                else:
                    # Keep original header if no mapping found (for debugging)
                    payload[excel_header] = cell.value
        return payload

    def _row_is_empty(self, row_payload: Dict) -> bool:
        """Check if a row is empty"""
        # Check if all values are None or empty strings
        return all(
            value is None or (isinstance(value, str) and not value.strip())
            for value in row_payload.values()
        )

    def _transform_row_payload(
        self, row_payload: Dict, date1904: bool, company: Company, user=None
    ) -> Dict[str, any]:
        """Transform Excel row data to headcount model data"""
        headcount_data = {}

        # Name (required)
        if "name" in row_payload and row_payload["name"]:
            headcount_data["name"] = str(row_payload["name"]).strip()

        # Email (required)
        if "email" in row_payload and row_payload["email"]:
            email = str(row_payload["email"]).strip().lower()
            if email:
                headcount_data["email"] = email

        # Department (FK - get or create)
        if "department" in row_payload and row_payload["department"]:
            department_name = str(row_payload["department"]).strip()
            if department_name:
                try:
                    department, _ = Department.objects.get_or_create(
                        company=company,
                        name=department_name,
                        defaults={"created_by": user, "updated_by": user},
                    )
                    headcount_data["department"] = department
                except Exception as e:
                    # If get_or_create fails, try to get existing
                    try:
                        department = Department.objects.get(
                            company=company, name=department_name
                        )
                        headcount_data["department"] = department
                    except Department.DoesNotExist:
                        raise ValueError(f"Unable to create or find department: {department_name}")

        # Role (FK - get or create)
        if "role" in row_payload and row_payload["role"]:
            role_name = str(row_payload["role"]).strip()
            if role_name:
                try:
                    role, _ = Role.objects.get_or_create(
                        company=company,
                        name=role_name,
                        defaults={"created_by": user, "updated_by": user},
                    )
                    headcount_data["role"] = role
                except Exception as e:
                    # If get_or_create fails, try to get existing
                    try:
                        role = Role.objects.get(company=company, name=role_name)
                        headcount_data["role"] = role
                    except Role.DoesNotExist:
                        raise ValueError(f"Unable to create or find role: {role_name}")

        # Level (enum)
        if "level" in row_payload and row_payload["level"]:
            level_value = self._match_level(str(row_payload["level"]).strip())
            if level_value:
                headcount_data["level"] = level_value
            else:
                raise ValueError(
                    f"Invalid level value: {row_payload['level']}. "
                    f"Valid values: {', '.join([l[1] for l in Level.choices])}"
                )

        # Status (enum)
        if "status" in row_payload and row_payload["status"]:
            status_value = self._match_status(str(row_payload["status"]).strip())
            if status_value:
                headcount_data["status"] = status_value
            else:
                raise ValueError(
                    f"Invalid status value: {row_payload['status']}. "
                    f"Valid values: {', '.join([s[1] for s in EmploymentStatus.choices])}"
                )

        # Employment Type (enum)
        if "employment" in row_payload and row_payload["employment"]:
            employment_value = self._match_employment_type(
                str(row_payload["employment"]).strip()
            )
            if employment_value:
                headcount_data["employment"] = employment_value
            else:
                raise ValueError(
                    f"Invalid employment type value: {row_payload['employment']}. "
                    f"Valid values: {', '.join([e[1] for e in EmploymentType.choices])}"
                )

        # Gender (enum)
        if "gender" in row_payload and row_payload["gender"]:
            gender_value = self._match_gender(str(row_payload["gender"]).strip())
            if gender_value:
                headcount_data["gender"] = gender_value
            else:
                raise ValueError(
                    f"Invalid gender value: {row_payload['gender']}. "
                    f"Valid values: {', '.join([g[1] for g in Gender.choices])}"
                )

        # Location
        if "location" in row_payload and row_payload["location"]:
            headcount_data["location"] = str(row_payload["location"]).strip()

        # Salary Annual (required)
        if "salary_annual" in row_payload and row_payload["salary_annual"] is not None:
            headcount_data["salary_annual"] = self._parse_decimal(
                row_payload["salary_annual"]
            )

        # Bonus Percent
        if "bouns_percent" in row_payload and row_payload["bouns_percent"] is not None:
            headcount_data["bouns_percent"] = self._parse_decimal(
                row_payload["bouns_percent"]
            )

        # Benefits Annual
        if (
            "benefits_annual" in row_payload
            and row_payload["benefits_annual"] is not None
        ):
            headcount_data["benefits_annual"] = self._parse_decimal(
                row_payload["benefits_annual"]
            )

        # Start Date (required)
        if "start_date" in row_payload and row_payload["start_date"]:
            headcount_data["start_date"] = self._parse_date(
                row_payload["start_date"], date1904
            )

        # Exit Date (end_date)
        if "end_date" in row_payload and row_payload["end_date"]:
            headcount_data["end_date"] = self._parse_date(
                row_payload["end_date"], date1904
            )

        # Exit Reason
        if "exit_reason" in row_payload and row_payload["exit_reason"]:
            headcount_data["exit_reason"] = str(row_payload["exit_reason"]).strip()

        return headcount_data

    def _parse_date(self, value, date1904: bool = False):
        """Parse date from Excel value"""
        if value is None:
            return None

        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, str):
            # Try parsing common date formats
            for fmt in [
                "%Y-%m-%d",
                "%d/%m/%Y",
                "%m/%d/%Y",
                "%d-%m-%Y",
                "%Y/%m/%d",
                "%d-%b-%Y",
                "%d-%B-%Y",
            ]:
                try:
                    return datetime.strptime(value.strip(), fmt).date()
                except ValueError:
                    continue
            raise ValueError(f"Unable to parse date: {value}")

        # Try Excel date conversion
        try:
            if isinstance(value, (int, float)):
                return from_excel(value, date1904).date()
        except Exception:
            pass

        raise ValueError(f"Unable to parse date: {value}")

    def _parse_decimal(self, value) -> Decimal:
        """Parse decimal from Excel value"""
        if value is None:
            return Decimal("0.00")

        if isinstance(value, Decimal):
            return value

        if isinstance(value, (int, float)):
            return Decimal(str(value))

        if isinstance(value, str):
            # Remove currency symbols and commas
            cleaned = value.replace("₹", "").replace("$", "").replace(",", "").strip()
            try:
                return Decimal(cleaned)
            except InvalidOperation:
                raise ValueError(f"Unable to parse decimal: {value}")

        raise ValueError(f"Unable to parse decimal: {value}")

    def _match_level(self, level_str: str) -> Optional[str]:
        """Match level string to enum value"""
        level_str_lower = level_str.lower().strip()

        # Direct match
        for value, label in Level.choices:
            if level_str_lower == value.lower() or level_str_lower == label.lower():
                return value

        # Fuzzy matching
        level_mapping = {
            "vp": Level.VP,
            "director": Level.DIRECTOR,
            "manager": Level.MANAGER,
            "lead": Level.LEAD,
            "senior": Level.SENIOR,
            "mid": Level.MID,
            "middle": Level.MID,
            "junior": Level.JUNIOR,
        }

        return level_mapping.get(level_str_lower)

    def _match_status(self, status_str: str) -> Optional[str]:
        """Match status string to enum value"""
        status_str_lower = status_str.lower().strip()

        # Direct match
        for value, label in EmploymentStatus.choices:
            if status_str_lower == value.lower() or status_str_lower == label.lower():
                return value

        # Fuzzy matching
        status_mapping = {
            "active": EmploymentStatus.ACTIVE,
            "resigned": EmploymentStatus.RESIGNED,
            "inactive": EmploymentStatus.INACTIVE,
            "terminated": EmploymentStatus.INACTIVE,
        }

        return status_mapping.get(status_str_lower)

    def _match_employment_type(self, employment_str: str) -> Optional[str]:
        """Match employment type string to enum value"""
        employment_str_lower = employment_str.lower().strip()
        
        # Normalize underscores to hyphens for matching
        normalized = employment_str_lower.replace("_", "-").replace(" ", "-")

        # Direct match
        for value, label in EmploymentType.choices:
            value_lower = value.lower()
            label_lower = label.lower()
            if (
                employment_str_lower == value_lower
                or employment_str_lower == label_lower
                or normalized == value_lower
                or normalized == label_lower
            ):
                return value

        # Fuzzy matching - handle various formats including underscores
        employment_mapping = {
            "full-time": EmploymentType.FULL_TIME,
            "fulltime": EmploymentType.FULL_TIME,
            "full time": EmploymentType.FULL_TIME,
            "full_time": EmploymentType.FULL_TIME,
            "part-time": EmploymentType.PART_TIME,
            "parttime": EmploymentType.PART_TIME,
            "part time": EmploymentType.PART_TIME,
            "part_time": EmploymentType.PART_TIME,
            "contractor": EmploymentType.CONTRACTOR,
            "contract": EmploymentType.CONTRACTOR,
            "intern": EmploymentType.INTERN,
            "internship": EmploymentType.INTERN,
        }

        return employment_mapping.get(employment_str_lower) or employment_mapping.get(normalized)

    def _match_gender(self, gender_str: str) -> Optional[str]:
        """Match gender string to enum value"""
        gender_str_lower = gender_str.lower().strip()

        # Direct match
        for value, label in Gender.choices:
            if gender_str_lower == value.lower() or gender_str_lower == label.lower():
                return value

        # Fuzzy matching
        gender_mapping = {
            "male": Gender.MALE,
            "m": Gender.MALE,
            "female": Gender.FEMALE,
            "f": Gender.FEMALE,
        }

        return gender_mapping.get(gender_str_lower)

    def _persist_headcount(
        self, headcount_data: Dict, company: Company, user
    ) -> bool:
        """Create or update a headcount"""
        email = headcount_data.get("email")

        # Check if headcount already exists
        try:
            headcount = Headcount.objects.get(email=email)
            # Update existing headcount
            for key, value in headcount_data.items():
                setattr(headcount, key, value)
            headcount.company = company
            headcount.updated_by = user
            headcount.save()
            return False  # Updated, not created
        except Headcount.DoesNotExist:
            # Create new headcount
            headcount = Headcount.objects.create(
                company=company,
                created_by=user,
                updated_by=user,
                **headcount_data,
            )
            return True  # Created

    def _flatten_validation_error(self, exc: ValidationError) -> str:
        """Flatten Django ValidationError to string"""
        if hasattr(exc, "message_dict"):
            return "; ".join(
                f"{field}: {', '.join(messages)}"
                for field, messages in exc.message_dict.items()
            )
        return str(exc)

