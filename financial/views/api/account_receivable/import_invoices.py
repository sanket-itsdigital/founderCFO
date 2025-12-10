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
from financial.enums import (
    InvoicesCategoryChoices,
    InvoicesPaymentTerms,
    InvoicesStatusChoices,
)
from revenue.models.invoice import Invoice
from financial.views.api.account_receivable.ar_aging import get_company_from_request


@dataclass
class ImportResult:
    """Result of Excel import operation"""

    created: int = 0
    updated: int = 0
    skipped: List[Tuple[int, str]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class InvoiceImportError(Exception):
    """Custom exception for invoice import errors"""

    pass


class InvoiceImportView(APIView):
    """
    Excel Import API for Invoices
    Accepts an Excel file and imports invoice data into the database.

    Expected Excel columns:
    1. invoice_number
    2. customer_name
    3. invoice_date
    4. due_date
    5. amount
    6. tax_amount
    7. status
    8. payment_terms
    9. category
    10. sales_order_ref
    11. notes
    """

    permission_classes = [IsAuthenticated]

    # Expected column headers (case-insensitive)
    EXPECTED_COLUMNS = [
        "invoice_number",
        "customer_name",
        "invoice_date",
        "due_date",
        "amount",
        "tax_amount",
        "status",
        "payment_terms",
        "category",
        "sales_order_ref",
        "notes",
    ]

    # Required columns
    REQUIRED_COLUMNS = [
        "invoice_number",
        "customer_name",
        "invoice_date",
        "due_date",
        "amount",
    ]

    def post(self, request):
        """Import invoices from Excel file"""
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
            result = self._import_invoices_from_excel(
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

        except InvoiceImportError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"error": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _import_invoices_from_excel(
        self, uploaded_file, company: Company, user
    ) -> ImportResult:
        """Read the Excel file and create/update Invoice records"""
        try:
            uploaded_file.seek(0)
        except (AttributeError, OSError):
            pass

        try:
            workbook = load_workbook(uploaded_file, data_only=True)
        except Exception as exc:
            raise InvoiceImportError("Unable to read the uploaded Excel file.") from exc

        if not workbook.sheetnames:
            raise InvoiceImportError("The Excel file does not contain any sheets.")

        # Use the first sheet
        sheet = workbook[workbook.sheetnames[0]]

        if sheet.max_row < 2:
            raise InvoiceImportError("The sheet does not contain any data rows.")

        # Locate header row
        header_map, header_row_index = self._locate_header_row(sheet)
        if not header_map or header_row_index is None:
            raise InvoiceImportError(
                "Could not detect the header row. Please ensure the first row contains column headers."
            )

        # Check for required columns
        missing_columns = [
            col
            for col in self.REQUIRED_COLUMNS
            if col.lower() not in [h.lower() for h in header_map.values()]
        ]
        if missing_columns:
            raise InvoiceImportError(
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
                invoice_data = self._transform_row_payload(row_payload, date1904)
            except ValueError as exc:
                result.skipped.append((row_number, str(exc)))
                continue

            # Validate required fields
            missing_required = [
                field
                for field in [
                    "invoice_number",
                    "customer_name",
                    "invoice_date",
                    "due_date",
                    "total_amount",
                ]
                if not invoice_data.get(field)
            ]
            if missing_required:
                result.skipped.append(
                    (
                        row_number,
                        f"Missing required values: {', '.join(missing_required)}",
                    )
                )
                continue

            # Create or update invoice
            try:
                created = self._persist_invoice(invoice_data, company, user)
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
        self, row_payload: Dict, date1904: bool
    ) -> Dict[str, any]:
        """Transform Excel row data to invoice model data"""
        invoice_data = {}

        # Map invoice_number
        if "invoice_number" in row_payload:
            invoice_data["invoice_number"] = str(row_payload["invoice_number"]).strip()

        # Map customer_name
        if "customer_name" in row_payload:
            invoice_data["customer_name"] = str(row_payload["customer_name"]).strip()

        # Map invoice_date
        if "invoice_date" in row_payload:
            invoice_data["invoice_date"] = self._parse_date(
                row_payload["invoice_date"], date1904
            )

        # Map due_date
        if "due_date" in row_payload:
            invoice_data["due_date"] = self._parse_date(
                row_payload["due_date"], date1904
            )

        # Map amount -> total_amount
        if "amount" in row_payload:
            invoice_data["total_amount"] = self._parse_decimal(row_payload["amount"])

        # Map tax_amount
        if "tax_amount" in row_payload:
            invoice_data["tax_amount"] = self._parse_decimal(row_payload["tax_amount"])

        # Map status (with enum matching)
        if "status" in row_payload and row_payload["status"]:
            status_value = self._match_status(str(row_payload["status"]).strip())
            if status_value:
                invoice_data["status"] = status_value
            else:
                raise ValueError(
                    f"Invalid status value: {row_payload['status']}. "
                    f"Valid values: {', '.join([s[1] for s in InvoicesStatusChoices.choices])}"
                )

        # Map payment_terms (with enum matching)
        if "payment_terms" in row_payload and row_payload["payment_terms"]:
            payment_terms_value = self._match_payment_terms(
                str(row_payload["payment_terms"]).strip()
            )
            if payment_terms_value:
                invoice_data["payment_terms"] = payment_terms_value
            else:
                raise ValueError(
                    f"Invalid payment_terms value: {row_payload['payment_terms']}. "
                    f"Valid values: {', '.join([pt[1] for pt in InvoicesPaymentTerms.choices])}"
                )

        # Map category (with enum matching)
        if "category" in row_payload and row_payload["category"]:
            category_value = self._match_category(str(row_payload["category"]).strip())
            if category_value:
                invoice_data["category"] = category_value

        # Map sales_order_ref -> sales_order_reference
        if "sales_order_ref" in row_payload and row_payload["sales_order_ref"]:
            invoice_data["sales_order_reference"] = str(
                row_payload["sales_order_ref"]
            ).strip()

        # Map notes
        if "notes" in row_payload and row_payload["notes"]:
            invoice_data["notes"] = str(row_payload["notes"]).strip()

        return invoice_data

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
        for value, label in InvoicesStatusChoices.choices:
            if status_str_lower == value.lower() or status_str_lower == label.lower():
                return value

        # Fuzzy matching
        status_mapping = {
            "draft": InvoicesStatusChoices.DRAFT,
            "pending": InvoicesStatusChoices.PENDING,
            "partial": InvoicesStatusChoices.PARTIAL,
            "paid": InvoicesStatusChoices.PAID,
            "overdue": InvoicesStatusChoices.OVERDUE,
            "cancelled": InvoicesStatusChoices.CANCELLED,
            "canceled": InvoicesStatusChoices.CANCELLED,
            "bad debt": InvoicesStatusChoices.BAD_DEBT,
            "baddebt": InvoicesStatusChoices.BAD_DEBT,
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

    def _match_category(self, category_str: str) -> Optional[str]:
        """Match category string to enum value"""
        category_str_lower = category_str.lower().strip()

        # Direct match
        for value, label in InvoicesCategoryChoices.choices:
            if (
                category_str_lower == value.lower()
                or category_str_lower == label.lower()
            ):
                return value

        # Fuzzy matching
        category_mapping = {
            "products sales": InvoicesCategoryChoices.PRODUCTS_SALES,
            "product sales": InvoicesCategoryChoices.PRODUCTS_SALES,
            "products": InvoicesCategoryChoices.PRODUCTS_SALES,
            "services": InvoicesCategoryChoices.SERVICES,
            "service": InvoicesCategoryChoices.SERVICES,
            "subscriptions": InvoicesCategoryChoices.SUBSCRIPTIONS,
            "subscription": InvoicesCategoryChoices.SUBSCRIPTIONS,
            "consulting": InvoicesCategoryChoices.CONSULTING,
            "maintenance": InvoicesCategoryChoices.MAINTENANCE,
            "other": InvoicesCategoryChoices.OTHER,
        }

        return category_mapping.get(category_str_lower)

    def _persist_invoice(self, invoice_data: Dict, company: Company, user) -> bool:
        """Create or update an invoice"""
        invoice_number = invoice_data.get("invoice_number")

        # Check if invoice already exists
        try:
            invoice = Invoice.objects.get(
                company=company, invoice_number=invoice_number
            )
            # Update existing invoice
            for key, value in invoice_data.items():
                setattr(invoice, key, value)
            invoice.updated_by = user
            invoice.save()
            return False  # Updated, not created
        except Invoice.DoesNotExist:
            # Create new invoice
            invoice = Invoice.objects.create(
                company=company,
                created_by=user,
                updated_by=user,
                **invoice_data,
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
