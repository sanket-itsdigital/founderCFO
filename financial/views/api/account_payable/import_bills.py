from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from django.core.exceptions import ValidationError
from openpyxl import load_workbook
from openpyxl.utils.datetime import from_excel
from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Company
from financial.enums import BillsStatusChoices, InvoicesPaymentTerms
from financial.models.account_payable.bills import Bill
from financial.models.account_payable.vendor import Vendor
from financial.views.api.account_receivable.ar_aging import get_company_from_request


@dataclass
class ImportResult:
    """Result of Excel import operation"""

    created: int = 0
    updated: int = 0
    skipped: List[Tuple[int, str]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class BillImportError(Exception):
    """Custom exception for bill import errors"""

    pass


class BillImportView(APIView):
    """
    Excel Import API for Bills
    Accepts an Excel file and imports bill data into the database.

    Expected Excel columns:
    1. bill_number
    2. vendor_name
    3. bill_date
    4. due_date
    5. amount
    6. tax_amount (optional, not stored in Bill model)
    7. total_amount (if provided, used instead of amount)
    8. status
    9. payment_terms (optional, stored in Vendor if vendor is created)
    10. credit_period_days (optional, not stored in Bill model)
    11. early_payment_discount_pct (optional, not stored in Bill model)
    12. category
    13. purchase_order_ref (optional, not stored in Bill model)
    14. notes
    """

    permission_classes = [IsAuthenticated]

    # Expected column headers (case-insensitive)
    EXPECTED_COLUMNS = [
        "bill_number",
        "vendor_name",
        "bill_date",
        "due_date",
        "amount",
        "tax_amount",
        "total_amount",
        "status",
        "payment_terms",
        "credit_period_days",
        "early_payment_discount_pct",
        "category",
        "purchase_order_ref",
        "notes",
    ]

    # Required columns
    REQUIRED_COLUMNS = [
        "bill_number",
        "vendor_name",
        "bill_date",
        "due_date",
    ]

    def post(self, request):
        """Import bills from Excel file"""
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
            result = self._import_bills_from_excel(uploaded_file, company, request.user)

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

        except BillImportError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"error": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _import_bills_from_excel(
        self, uploaded_file, company: Company, user
    ) -> ImportResult:
        """Read the Excel file and create/update Bill records"""
        try:
            uploaded_file.seek(0)
        except (AttributeError, OSError):
            pass

        try:
            workbook = load_workbook(uploaded_file, data_only=True)
        except Exception as exc:
            raise BillImportError("Unable to read the uploaded Excel file.") from exc

        if not workbook.sheetnames:
            raise BillImportError("The Excel file does not contain any sheets.")

        # Use the first sheet
        sheet = workbook[workbook.sheetnames[0]]

        if sheet.max_row < 2:
            raise BillImportError("The sheet does not contain any data rows.")

        # Locate header row
        header_map, header_row_index = self._locate_header_row(sheet)
        if not header_map or header_row_index is None:
            raise BillImportError(
                "Could not detect the header row. Please ensure the first row contains column headers."
            )

        # Check for required columns
        missing_columns = [
            col
            for col in self.REQUIRED_COLUMNS
            if col.lower() not in [h.lower() for h in header_map.values()]
        ]
        if missing_columns:
            raise BillImportError(
                f"Missing required columns: {', '.join(missing_columns)}"
            )

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
                bill_data = self._transform_row_payload(row_payload, date1904, company)
            except ValueError as exc:
                result.skipped.append((row_number, str(exc)))
                continue

            # Validate required fields
            missing_required = [
                field
                for field in ["bill_number", "vendor_name", "bill_date", "due_date"]
                if not bill_data.get(field)
            ]
            if missing_required:
                result.skipped.append(
                    (
                        row_number,
                        f"Missing required values: {', '.join(missing_required)}",
                    )
                )
                continue

            # Ensure amount is set
            if not bill_data.get("amount"):
                result.skipped.append(
                    (row_number, "Missing required value: amount or total_amount")
                )
                continue

            # Create or update bill
            try:
                created = self._persist_bill(bill_data, company, user)
                if created:
                    result.created += 1
                else:
                    result.updated += 1
            except ValidationError as exc:
                result.skipped.append((row_number, self._flatten_validation_error(exc)))
                continue
            except Exception as exc:
                result.skipped.append((row_number, str(exc)))
                continue

        return result

    def _locate_header_row(
        self, sheet
    ) -> Tuple[Optional[Dict[int, str]], Optional[int]]:
        """Locate the header row in the sheet"""
        # Check first 10 rows for headers
        for row_idx in range(1, min(11, sheet.max_row + 1)):
            row = sheet[row_idx]
            header_map = self._build_header_map(row)

            # Check if we found expected columns
            found_columns = [col.lower() for col in header_map.values()]
            expected_lower = [col.lower() for col in self.EXPECTED_COLUMNS]

            # If we found at least the required columns, consider this the header row
            required_found = sum(
                1 for col in self.REQUIRED_COLUMNS if col.lower() in found_columns
            )

            if required_found >= len(self.REQUIRED_COLUMNS):
                return header_map, row_idx

        return None, None

    def _build_header_map(self, header_row) -> Dict[int, str]:
        """Build a map of column index to header name"""
        header_map: Dict[int, str] = {}
        for cell in header_row:
            if cell.value:
                # Normalize header name (strip whitespace, convert to lowercase for matching)
                header_name = str(cell.value).strip()
                header_map[cell.column] = header_name
        return header_map

    def _extract_row_payload(self, row, header_map: Dict[int, str]) -> Dict[str, any]:
        """Extract data from a row based on header map"""
        payload = {}
        for cell in row:
            if cell.column in header_map:
                header_name = header_map[cell.column]
                payload[header_name] = cell.value
        return payload

    def _row_is_empty(self, row_payload: Dict) -> bool:
        """Check if a row is empty"""
        # Check if all values are None or empty strings
        return all(
            value is None or (isinstance(value, str) and not value.strip())
            for value in row_payload.values()
        )

    def _transform_row_payload(
        self, row_payload: Dict, date1904: bool, company: Company
    ) -> Dict[str, any]:
        """Transform Excel row data to bill model data"""
        bill_data = {}

        # Map bill_number
        if "bill_number" in row_payload:
            bill_data["bill_number"] = str(row_payload["bill_number"]).strip()

        # Map vendor_name and get/create vendor
        if "vendor_name" in row_payload and row_payload["vendor_name"]:
            vendor_name = str(row_payload["vendor_name"]).strip()
            bill_data["vendor_name"] = vendor_name

            # Get or create vendor
            vendor, created = Vendor.objects.get_or_create(
                company=company,
                name=vendor_name,
                defaults={
                    "created_by": None,  # Will be set in _persist_bill if needed
                    "updated_by": None,
                },
            )
            bill_data["vendor"] = vendor

            # Update vendor payment_terms if provided
            if "payment_terms" in row_payload and row_payload["payment_terms"]:
                payment_terms_value = self._match_payment_terms(
                    str(row_payload["payment_terms"]).strip()
                )
                if payment_terms_value:
                    vendor.payment_terms = payment_terms_value
                    vendor.save(update_fields=["payment_terms"])

        # Map bill_date
        if "bill_date" in row_payload:
            bill_data["bill_date"] = self._parse_date(
                row_payload["bill_date"], date1904
            )

        # Map due_date
        if "due_date" in row_payload:
            bill_data["due_date"] = self._parse_date(row_payload["due_date"], date1904)

        # Map amount - prefer total_amount if provided, otherwise use amount
        if "total_amount" in row_payload and row_payload["total_amount"]:
            bill_data["amount"] = self._parse_decimal(row_payload["total_amount"])
        elif "amount" in row_payload and row_payload["amount"]:
            bill_data["amount"] = self._parse_decimal(row_payload["amount"])

        # Note: tax_amount is not stored in Bill model, so we skip it
        # If needed, it could be added to notes or a separate field

        # Map status (with enum matching)
        if "status" in row_payload and row_payload["status"]:
            status_value = self._match_status(str(row_payload["status"]).strip())
            if status_value:
                bill_data["status"] = status_value
            else:
                raise ValueError(
                    f"Invalid status value: {row_payload['status']}. "
                    f"Valid values: {', '.join([s[1] for s in BillsStatusChoices.choices])}"
                )

        # Map category
        if "category" in row_payload and row_payload["category"]:
            bill_data["category"] = str(row_payload["category"]).strip()

        # Map notes - include additional info if available
        notes_parts = []
        if "notes" in row_payload and row_payload["notes"]:
            notes_parts.append(str(row_payload["notes"]).strip())

        # Add optional fields to notes if they exist but aren't in model
        additional_info = []
        if "tax_amount" in row_payload and row_payload["tax_amount"]:
            tax_amt = self._parse_decimal(row_payload["tax_amount"])
            additional_info.append(f"Tax Amount: {tax_amt}")
        if "credit_period_days" in row_payload and row_payload["credit_period_days"]:
            additional_info.append(
                f"Credit Period: {row_payload['credit_period_days']} days"
            )
        if (
            "early_payment_discount_pct" in row_payload
            and row_payload["early_payment_discount_pct"]
        ):
            additional_info.append(
                f"Early Payment Discount: {row_payload['early_payment_discount_pct']}%"
            )
        if "purchase_order_ref" in row_payload and row_payload["purchase_order_ref"]:
            additional_info.append(f"PO Reference: {row_payload['purchase_order_ref']}")

        if additional_info:
            notes_parts.append(" | ".join(additional_info))

        if notes_parts:
            bill_data["notes"] = "\n".join(notes_parts)

        return bill_data

    def _parse_date(self, value, date1904: bool = False):
        """Parse date from Excel value"""
        if value is None:
            return None

        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, str):
            # Try parsing common date formats
            for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d"]:
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

    def _match_status(self, status_str: str) -> Optional[str]:
        """Match status string to enum value"""
        status_str_lower = status_str.lower().strip()

        # Direct match
        for value, label in BillsStatusChoices.choices:
            if status_str_lower == value.lower() or status_str_lower == label.lower():
                return value

        # Fuzzy matching
        status_mapping = {
            "pending": BillsStatusChoices.PENDING,
            "partial": BillsStatusChoices.PARTIAL,
            "paid": BillsStatusChoices.PAID,
            "overdue": BillsStatusChoices.OVERDUE,
            "cancelled": BillsStatusChoices.CANCELLED,
            "canceled": BillsStatusChoices.CANCELLED,
        }

        return status_mapping.get(status_str_lower)

    def _match_payment_terms(self, payment_terms_str: str) -> Optional[str]:
        """Match payment terms string to enum value"""
        payment_terms_str_lower = payment_terms_str.lower().strip()

        # Direct match
        for value, label in InvoicesPaymentTerms.choices:
            if (
                payment_terms_str_lower == value.lower()
                or payment_terms_str_lower == label.lower()
            ):
                return value

        # Fuzzy matching
        payment_terms_mapping = {
            "cod": InvoicesPaymentTerms.COD,
            "net 7": InvoicesPaymentTerms.NET_7,
            "net7": InvoicesPaymentTerms.NET_7,
            "net 15": InvoicesPaymentTerms.NET_15,
            "net15": InvoicesPaymentTerms.NET_15,
            "net 30": InvoicesPaymentTerms.NET_30,
            "net30": InvoicesPaymentTerms.NET_30,
            "net 45": InvoicesPaymentTerms.NET_45,
            "net45": InvoicesPaymentTerms.NET_45,
            "net 60": InvoicesPaymentTerms.NET_60,
            "net60": InvoicesPaymentTerms.NET_60,
            "net 90": InvoicesPaymentTerms.NET_90,
            "net90": InvoicesPaymentTerms.NET_90,
        }

        return payment_terms_mapping.get(payment_terms_str_lower)

    def _persist_bill(self, bill_data: Dict, company: Company, user) -> bool:
        """Create or update a bill"""
        bill_number = bill_data.get("bill_number")

        # Check if bill already exists
        try:
            bill = Bill.objects.get(company=company, bill_number=bill_number)
            # Update existing bill
            for key, value in bill_data.items():
                if key != "vendor":  # Handle vendor separately
                    setattr(bill, key, value)
                else:
                    bill.vendor = value
            bill.updated_by = user
            bill.save()
            return False  # Updated, not created
        except Bill.DoesNotExist:
            # Create new bill
            bill = Bill.objects.create(
                company=company,
                created_by=user,
                updated_by=user,
                **bill_data,
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
