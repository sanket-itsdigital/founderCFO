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
from hr.models.recruitment import (
    Recruitment,
    RecruitmentStatusChoices,
    RecruitmentSourceChoices,
)
from hr.models.department import Department
from sales.views.api.utils import get_company_from_request


@dataclass
class ImportResult:
    """Result of Excel import operation"""

    created: int = 0
    updated: int = 0
    skipped: List[Tuple[int, str]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class RecruitmentImportError(Exception):
    """Custom exception for recruitment import errors"""

    pass


class RecruitmentImportView(APIView):
    """
    Excel Import API for HR Recruitment
    Accepts an Excel file and imports recruitment data into the database.
    
    Expected Excel columns:
    1. job title (required) - Job title
    2. department - Department name (will be created if doesn't exist)
    3. status - Recruitment status (open, in progress, filled)
    4. positions_required - Number of positions required
    5. applications_received - Number of applications received
    6. interviews_conducted - Number of interviews conducted
    7. offers_made - Number of offers made
    8. offers_accepted - Number of offers accepted
    9. cost_spent - Total cost spent on recruitment
    10. source - Recruitment source (Company Website, LinkedIn, Naukri, etc.)
    11. posting_date (required) - Date when job was posted
    12. target_close_date - Target date to close the position
    13. actual_close_date - Actual date when position was closed
    14. salary_range_min - Minimum salary in range
    15. salary_range_max - Maximum salary in range
    """

    permission_classes = [IsAuthenticated]

    # Mapping from Excel column names (various formats) to model field names
    EXCEL_TO_FIELD_MAPPING = {
        # Job Title
        "job title": "job_title",
        "job_title": "job_title",
        "jobtitle": "job_title",
        "title": "job_title",
        # Department
        "department": "department",
        # Status
        "status": "status",
        # Positions Required
        "positions required": "positions_required",
        "positions_required": "positions_required",
        "positionsrequired": "positions_required",
        "positions": "positions_required",
        # Applications Received
        "applications received": "applications_received",
        "applications_received": "applications_received",
        "applicationsreceived": "applications_received",
        "applications": "applications_received",
        # Interviews Conducted
        "interviews conducted": "interviews_conducted",
        "interviews_conducted": "interviews_conducted",
        "interviewsconducted": "interviews_conducted",
        "interviews": "interviews_conducted",
        # Offers Made
        "offers made": "offers_made",
        "offers_made": "offers_made",
        "offersmade": "offers_made",
        "offers": "offers_made",
        # Offers Accepted
        "offers accepted": "offers_accepted",
        "offers_accepted": "offers_accepted",
        "offersaccepted": "offers_accepted",
        "accepted": "offers_accepted",
        # Cost Spent
        "cost spent": "cost_spent",
        "cost_spent": "cost_spent",
        "costspent": "cost_spent",
        "cost": "cost_spent",
        # Source
        "source": "source",
        # Posting Date
        "posting date": "posting_date",
        "posting_date": "posting_date",
        "postingdate": "posting_date",
        "posted date": "posting_date",
        # Target Close Date
        "target close date": "target_close_date",
        "target_close_date": "target_close_date",
        "targetclosedate": "target_close_date",
        "target date": "target_close_date",
        # Actual Close Date
        "actual close date": "actual_close_date",
        "actual_close_date": "actual_close_date",
        "actualclosedate": "actual_close_date",
        "close date": "actual_close_date",
        "closed date": "actual_close_date",
        # Salary Range Min
        "salary range min": "salary_range_min",
        "salary_range_min": "salary_range_min",
        "salaryrangemin": "salary_range_min",
        "min salary": "salary_range_min",
        "salary min": "salary_range_min",
        # Salary Range Max
        "salary range max": "salary_range_max",
        "salary_range_max": "salary_range_max",
        "salaryrangemax": "salary_range_max",
        "max salary": "salary_range_max",
        "salary max": "salary_range_max",
    }

    # Expected model field names (for validation)
    EXPECTED_COLUMNS = list(set(EXCEL_TO_FIELD_MAPPING.values()))

    # Required columns (model field names)
    REQUIRED_COLUMNS = [
        "job_title",
        "posting_date",
    ]

    def post(self, request):
        """Import recruitment from Excel file"""
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
            result = self._import_recruitment_from_excel(
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

        except RecruitmentImportError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"error": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _import_recruitment_from_excel(
        self, uploaded_file, company: Company, user
    ) -> ImportResult:
        """Read the Excel file and create/update Recruitment records"""
        try:
            uploaded_file.seek(0)
        except (AttributeError, OSError):
            pass

        try:
            workbook = load_workbook(uploaded_file, data_only=True)
        except Exception as exc:
            raise RecruitmentImportError(
                "Unable to read the uploaded Excel file."
            ) from exc

        if not workbook.sheetnames:
            raise RecruitmentImportError(
                "The Excel file does not contain any sheets."
            )

        # Use the first sheet
        sheet = workbook[workbook.sheetnames[0]]

        if sheet.max_row < 2:
            raise RecruitmentImportError("The sheet does not contain any data rows.")

        # Locate header row
        header_map, header_row_index = self._locate_header_row(sheet)
        if not header_map or header_row_index is None:
            raise RecruitmentImportError(
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
            raise RecruitmentImportError(error_msg)

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
                recruitment_data = self._transform_row_payload(
                    row_payload, date1904, company, user
                )
            except ValueError as exc:
                result.skipped.append((row_number, str(exc)))
                continue

            # Validate required fields
            missing_required = [
                field
                for field in ["job_title", "posting_date"]
                if not recruitment_data.get(field)
            ]
            if missing_required:
                result.skipped.append(
                    (
                        row_number,
                        f"Missing required values: {', '.join(missing_required)}",
                    )
                )
                continue

            # Create or update recruitment
            try:
                created = self._persist_recruitment(recruitment_data, company, user)
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
        """Transform Excel row data to recruitment model data"""
        recruitment_data = {}

        # Job Title (required)
        if "job_title" in row_payload and row_payload["job_title"]:
            recruitment_data["job_title"] = str(row_payload["job_title"]).strip()

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
                    recruitment_data["department"] = department
                except Exception as e:
                    # If get_or_create fails, try to get existing
                    try:
                        department = Department.objects.get(
                            company=company, name=department_name
                        )
                        recruitment_data["department"] = department
                    except Department.DoesNotExist:
                        raise ValueError(
                            f"Unable to create or find department: {department_name}"
                        )

        # Status (enum)
        if "status" in row_payload and row_payload["status"]:
            status_value = self._match_status(str(row_payload["status"]).strip())
            if status_value:
                recruitment_data["status"] = status_value
            else:
                raise ValueError(
                    f"Invalid status value: {row_payload['status']}. "
                    f"Valid values: {', '.join([s[1] for s in RecruitmentStatusChoices.choices])}"
                )

        # Positions Required
        if (
            "positions_required" in row_payload
            and row_payload["positions_required"] is not None
        ):
            recruitment_data["positions_required"] = self._parse_integer(
                row_payload["positions_required"]
            )

        # Applications Received
        if (
            "applications_received" in row_payload
            and row_payload["applications_received"] is not None
        ):
            recruitment_data["applications_received"] = self._parse_integer(
                row_payload["applications_received"]
            )

        # Interviews Conducted
        if (
            "interviews_conducted" in row_payload
            and row_payload["interviews_conducted"] is not None
        ):
            recruitment_data["interviews_conducted"] = self._parse_integer(
                row_payload["interviews_conducted"]
            )

        # Offers Made
        if "offers_made" in row_payload and row_payload["offers_made"] is not None:
            recruitment_data["offers_made"] = self._parse_integer(
                row_payload["offers_made"]
            )

        # Offers Accepted
        if (
            "offers_accepted" in row_payload
            and row_payload["offers_accepted"] is not None
        ):
            recruitment_data["offers_accepted"] = self._parse_integer(
                row_payload["offers_accepted"]
            )

        # Cost Spent
        if "cost_spent" in row_payload and row_payload["cost_spent"] is not None:
            recruitment_data["cost_spent"] = self._parse_decimal(
                row_payload["cost_spent"]
            )

        # Source (enum)
        if "source" in row_payload and row_payload["source"]:
            source_value = self._match_source(str(row_payload["source"]).strip())
            if source_value:
                recruitment_data["source"] = source_value
            else:
                raise ValueError(
                    f"Invalid source value: {row_payload['source']}. "
                    f"Valid values: {', '.join([s[1] for s in RecruitmentSourceChoices.choices])}"
                )

        # Posting Date (required)
        if "posting_date" in row_payload and row_payload["posting_date"]:
            recruitment_data["posting_date"] = self._parse_date(
                row_payload["posting_date"], date1904
            )

        # Target Close Date
        if (
            "target_close_date" in row_payload
            and row_payload["target_close_date"]
        ):
            recruitment_data["target_close_date"] = self._parse_date(
                row_payload["target_close_date"], date1904
            )

        # Actual Close Date
        if (
            "actual_close_date" in row_payload
            and row_payload["actual_close_date"]
        ):
            recruitment_data["actual_close_date"] = self._parse_date(
                row_payload["actual_close_date"], date1904
            )

        # Salary Range Min
        if (
            "salary_range_min" in row_payload
            and row_payload["salary_range_min"] is not None
        ):
            recruitment_data["salary_range_min"] = self._parse_decimal(
                row_payload["salary_range_min"]
            )

        # Salary Range Max
        if (
            "salary_range_max" in row_payload
            and row_payload["salary_range_max"] is not None
        ):
            recruitment_data["salary_range_max"] = self._parse_decimal(
                row_payload["salary_range_max"]
            )

        return recruitment_data

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

    def _parse_integer(self, value) -> int:
        """Parse integer from Excel value"""
        if value is None:
            return 0

        if isinstance(value, int):
            return value

        if isinstance(value, float):
            return int(value)

        if isinstance(value, str):
            # Remove commas and other formatting
            cleaned = value.replace(",", "").strip()
            try:
                return int(float(cleaned))  # Convert to float first to handle "1.0" format
            except ValueError:
                raise ValueError(f"Unable to parse integer: {value}")

        raise ValueError(f"Unable to parse integer: {value}")

    def _match_status(self, status_str: str) -> Optional[str]:
        """Match status string to enum value"""
        status_str_lower = status_str.lower().strip()
        
        # Normalize underscores and spaces
        normalized = status_str_lower.replace("_", " ").replace("-", " ")

        # Direct match
        for value, label in RecruitmentStatusChoices.choices:
            value_lower = value.lower()
            label_lower = label.lower()
            if (
                status_str_lower == value_lower
                or status_str_lower == label_lower
                or normalized == value_lower
                or normalized == label_lower
            ):
                return value

        # Fuzzy matching
        status_mapping = {
            "open": RecruitmentStatusChoices.OPEN,
            "in progress": RecruitmentStatusChoices.IN_PROGRESS,
            "in_progress": RecruitmentStatusChoices.IN_PROGRESS,
            "progress": RecruitmentStatusChoices.IN_PROGRESS,
            "filled": RecruitmentStatusChoices.FILLED,
            "closed": RecruitmentStatusChoices.FILLED,
            "completed": RecruitmentStatusChoices.FILLED,
        }

        return status_mapping.get(status_str_lower) or status_mapping.get(normalized)

    def _match_source(self, source_str: str) -> Optional[str]:
        """Match source string to enum value"""
        source_str_lower = source_str.lower().strip()

        # Direct match
        for value, label in RecruitmentSourceChoices.choices:
            if (
                source_str_lower == value.lower()
                or source_str_lower == label.lower()
            ):
                return value

        # Fuzzy matching
        source_mapping = {
            "company website": RecruitmentSourceChoices.COMPANY_WEBSITE,
            "website": RecruitmentSourceChoices.COMPANY_WEBSITE,
            "campus hiring": RecruitmentSourceChoices.CAMPUS_HIRING,
            "campus": RecruitmentSourceChoices.CAMPUS_HIRING,
            "linkedin": RecruitmentSourceChoices.LINKEDIN,
            "naukri": RecruitmentSourceChoices.NAUKRI,
            "employee referral": RecruitmentSourceChoices.EMPLOYEE_REFERRAL,
            "referral": RecruitmentSourceChoices.EMPLOYEE_REFERRAL,
            "referrals": RecruitmentSourceChoices.EMPLOYEE_REFERRAL,
            "agency": RecruitmentSourceChoices.AGENCY,
            "job board": RecruitmentSourceChoices.JOB_BOARD,
            "jobboard": RecruitmentSourceChoices.JOB_BOARD,
            "other": RecruitmentSourceChoices.OTHER,
        }

        return source_mapping.get(source_str_lower)

    def _persist_recruitment(
        self, recruitment_data: Dict, company: Company, user
    ) -> bool:
        """Create or update a recruitment"""
        job_title = recruitment_data.get("job_title")
        posting_date = recruitment_data.get("posting_date")
        department = recruitment_data.get("department")

        # Try to find existing recruitment by job_title, posting_date, and department
        # This helps avoid duplicates while allowing multiple postings of the same role
        try:
            query = Recruitment.objects.filter(
                company=company,
                job_title=job_title,
                posting_date=posting_date,
            )
            if department:
                query = query.filter(department=department)
            else:
                query = query.filter(department__isnull=True)

            recruitment = query.first()

            if recruitment:
                # Update existing recruitment
                for key, value in recruitment_data.items():
                    setattr(recruitment, key, value)
                recruitment.company = company
                recruitment.updated_by = user
                recruitment.save()
                return False  # Updated, not created
        except Recruitment.MultipleObjectsReturned:
            # If multiple found, update the first one
            recruitment = query.first()
            for key, value in recruitment_data.items():
                setattr(recruitment, key, value)
            recruitment.company = company
            recruitment.updated_by = user
            recruitment.save()
            return False

        # Create new recruitment
        recruitment = Recruitment.objects.create(
            company=company,
            created_by=user,
            updated_by=user,
            **recruitment_data,
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

