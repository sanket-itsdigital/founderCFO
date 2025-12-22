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
from hr.models.budget import Budget
from hr.models.category import Category
from hr.models.department import Department
from sales.views.api.utils import get_company_from_request


@dataclass
class ImportResult:
    """Result of Excel import operation"""

    created: int = 0
    updated: int = 0
    skipped: List[Tuple[int, str]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class BudgetImportError(Exception):
    """Custom exception for budget import errors"""

    pass


class BudgetImportView(APIView):
    """
    Excel Import API for HR Budget
    Accepts an Excel file and imports budget data into the database.
    
    Expected Excel columns:
    1. period (required) - Budget period date
    2. category (required) - Budget category name (will be created if doesn't exist)
    3. department - Department name (will be created if doesn't exist, optional)
    4. budget_amount (required) - Budgeted amount
    5. actual_amount (required) - Actual amount spent
    6. notes - Additional notes
    """

    permission_classes = [IsAuthenticated]

    # Mapping from Excel column names (various formats) to model field names
    EXCEL_TO_FIELD_MAPPING = {
        # Period
        "period": "period",
        # Category
        "category": "category",
        # Department
        "department": "department",
        # Budget Amount
        "budget amount": "budget_amount",
        "budget_amount": "budget_amount",
        "budgetamount": "budget_amount",
        "budget": "budget_amount",
        # Actual Amount
        "actual amount": "actual_amount",
        "actual_amount": "actual_amount",
        "actualamount": "actual_amount",
        "actual": "actual_amount",
        # Notes
        "notes": "notes",
        "note": "notes",
    }

    # Expected model field names (for validation)
    EXPECTED_COLUMNS = list(set(EXCEL_TO_FIELD_MAPPING.values()))

    # Required columns (model field names)
    REQUIRED_COLUMNS = [
        "period",
        "category",
        "budget_amount",
        "actual_amount",
    ]

    def post(self, request):
        """Import budget from Excel file"""
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
            result = self._import_budget_from_excel(
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

        except BudgetImportError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"error": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _import_budget_from_excel(
        self, uploaded_file, company: Company, user
    ) -> ImportResult:
        """Read the Excel file and create/update Budget records"""
        try:
            uploaded_file.seek(0)
        except (AttributeError, OSError):
            pass

        try:
            workbook = load_workbook(uploaded_file, data_only=True)
        except Exception as exc:
            raise BudgetImportError(
                "Unable to read the uploaded Excel file."
            ) from exc

        if not workbook.sheetnames:
            raise BudgetImportError(
                "The Excel file does not contain any sheets."
            )

        # Use the first sheet
        sheet = workbook[workbook.sheetnames[0]]

        if sheet.max_row < 2:
            raise BudgetImportError("The sheet does not contain any data rows.")

        # Locate header row
        header_map, header_row_index = self._locate_header_row(sheet)
        if not header_map or header_row_index is None:
            raise BudgetImportError(
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
            raise BudgetImportError(error_msg)

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
                budget_data = self._transform_row_payload(
                    row_payload, date1904, company, user
                )
            except ValueError as exc:
                result.skipped.append((row_number, str(exc)))
                continue

            # Validate required fields
            missing_required = [
                field
                for field in ["period", "category", "budget_amount", "actual_amount"]
                if not budget_data.get(field)
            ]
            if missing_required:
                result.skipped.append(
                    (
                        row_number,
                        f"Missing required values: {', '.join(missing_required)}",
                    )
                )
                continue

            # Create or update budget
            try:
                created = self._persist_budget(budget_data, company, user)
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
        """Transform Excel row data to budget model data"""
        budget_data = {}

        # Period (required)
        if "period" in row_payload and row_payload["period"]:
            budget_data["period"] = self._parse_date(
                row_payload["period"], date1904
            )

        # Category (FK - get or create, globally unique)
        if "category" in row_payload and row_payload["category"]:
            category_name = str(row_payload["category"]).strip()
            if category_name:
                try:
                    category, _ = Category.objects.get_or_create(
                        name=category_name,
                        defaults={"created_by": user, "updated_by": user},
                    )
                    budget_data["category"] = category
                except Exception as e:
                    # If get_or_create fails, try to get existing
                    try:
                        category = Category.objects.get(name=category_name)
                        budget_data["category"] = category
                    except Category.DoesNotExist:
                        raise ValueError(
                            f"Unable to create or find category: {category_name}"
                        )

        # Department (FK - get or create, company-specific)
        if "department" in row_payload and row_payload["department"]:
            department_name = str(row_payload["department"]).strip()
            if department_name:
                try:
                    department, _ = Department.objects.get_or_create(
                        company=company,
                        name=department_name,
                        defaults={"created_by": user, "updated_by": user},
                    )
                    budget_data["department"] = department
                except Exception as e:
                    # If get_or_create fails, try to get existing
                    try:
                        department = Department.objects.get(
                            company=company, name=department_name
                        )
                        budget_data["department"] = department
                    except Department.DoesNotExist:
                        raise ValueError(
                            f"Unable to create or find department: {department_name}"
                        )

        # Budget Amount (required)
        if (
            "budget_amount" in row_payload
            and row_payload["budget_amount"] is not None
        ):
            budget_data["budget_amount"] = self._parse_decimal(
                row_payload["budget_amount"]
            )

        # Actual Amount (required)
        if (
            "actual_amount" in row_payload
            and row_payload["actual_amount"] is not None
        ):
            budget_data["actual_amount"] = self._parse_decimal(
                row_payload["actual_amount"]
            )

        # Notes
        if "notes" in row_payload and row_payload["notes"]:
            budget_data["notes"] = str(row_payload["notes"]).strip()

        return budget_data

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

    def _persist_budget(
        self, budget_data: Dict, company: Company, user
    ) -> bool:
        """Create or update a budget"""
        period = budget_data.get("period")
        category = budget_data.get("category")
        department = budget_data.get("department")

        # Try to find existing budget by unique_together constraint
        # unique_together = [company, period, category, department]
        try:
            query = Budget.objects.filter(
                company=company,
                period=period,
                category=category,
            )
            if department:
                query = query.filter(department=department)
            else:
                query = query.filter(department__isnull=True)

            budget = query.first()

            if budget:
                # Update existing budget
                for key, value in budget_data.items():
                    setattr(budget, key, value)
                budget.company = company
                budget.updated_by = user
                budget.save()
                return False  # Updated, not created
        except Budget.MultipleObjectsReturned:
            # If multiple found, update the first one
            budget = query.first()
            for key, value in budget_data.items():
                setattr(budget, key, value)
            budget.company = company
            budget.updated_by = user
            budget.save()
            return False

        # Create new budget
        budget = Budget.objects.create(
            company=company,
            created_by=user,
            updated_by=user,
            **budget_data,
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

