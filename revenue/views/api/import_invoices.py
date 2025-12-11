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
from financial.enums import InvoicesStatusChoices, InvoicesPaymentTerms
from revenue.models.invoice import Invoice
from sales.views.api.utils import get_company_from_request


@dataclass
class ImportResult:
    """Result of Excel import operation"""

    created: int = 0
    updated: int = 0
    skipped: List[Tuple[int, str]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class RevenueInvoiceImportError(Exception):
    """Custom exception for revenue invoice import errors"""

    pass


class RevenueInvoiceImportView(APIView):
    """
    Excel Import API for Revenue Invoices
    Accepts an Excel file and imports invoice data into the database.

    Expected Excel columns (all fields from revenue invoice model):
    1. invoice_number (required)
    2. invoice_date (required)
    3. due_date (required)
    4. customer_name (required)
    5. customer_gstin
    6. product_name (required)
    7. service_type
    8. hsn_sac_code
    9. place_of_supply
    10. quantity
    11. unit_price
    12. taxable_value
    13. cgst_rate
    14. cgst_amount
    15. sgst_rate
    16. sgst_amount
    17. igst_rate
    18. igst_amount
    19. total_amount (required)
    20. status
    21. payment_terms
    22. salesperson
    23. region
    24. territory
    25. department
    26. branch
    27. branch_gstin
    28. project_id
    29. project_name
    30. billing_type
    31. billable_hours
    32. is_recurring
    33. notes
    """

    permission_classes = [IsAuthenticated]

    # Mapping from Excel column names (various formats) to model field names
    EXCEL_TO_FIELD_MAPPING = {
        # Invoice Number variations
        "invoice number": "invoice_number",
        "invoice_number": "invoice_number",
        "invoicenumber": "invoice_number",
        # Invoice Date variations
        "invoice date": "invoice_date",
        "invoice_date": "invoice_date",
        "invoicedate": "invoice_date",
        # Due Date variations
        "due date": "due_date",
        "due_date": "due_date",
        "duedate": "due_date",
        # Customer Name variations
        "customer name": "customer_name",
        "customer_name": "customer_name",
        "customername": "customer_name",
        # Customer GSTIN variations
        "customer gstin": "customer_gstin",
        "customer_gstin": "customer_gstin",
        "customergstin": "customer_gstin",
        # Product Name variations
        "product name": "product_name",
        "product_name": "product_name",
        "productname": "product_name",
        # Service Type variations
        "service type": "service_type",
        "service_type": "service_type",
        "servicetype": "service_type",
        # HSN/SAC Code variations
        "hsn/sac code": "hsn_sac_code",
        "hsn_sac_code": "hsn_sac_code",
        "hsnsaccode": "hsn_sac_code",
        "hsn sac code": "hsn_sac_code",
        # Place of Supply variations
        "place of supply": "place_of_supply",
        "place_of_supply": "place_of_supply",
        "placeofsupply": "place_of_supply",
        # Quantity
        "quantity": "quantity",
        # Unit Price variations
        "unit price": "unit_price",
        "unit_price": "unit_price",
        "unitprice": "unit_price",
        # Taxable Value variations
        "taxable value": "taxable_value",
        "taxable_value": "taxable_value",
        "taxablevalue": "taxable_value",
        # CGST Rate variations
        "cgst rate": "cgst_rate",
        "cgst_rate": "cgst_rate",
        "cgstrate": "cgst_rate",
        # CGST Amount variations
        "cgst amount": "cgst_amount",
        "cgst_amount": "cgst_amount",
        "cgstamount": "cgst_amount",
        # SGST Rate variations
        "sgst rate": "sgst_rate",
        "sgst_rate": "sgst_rate",
        "sgstrate": "sgst_rate",
        # SGST Amount variations
        "sgst amount": "sgst_amount",
        "sgst_amount": "sgst_amount",
        "sgstamount": "sgst_amount",
        # IGST Rate variations
        "igst rate": "igst_rate",
        "igst_rate": "igst_rate",
        "igstrate": "igst_rate",
        # IGST Amount variations
        "igst amount": "igst_amount",
        "igst_amount": "igst_amount",
        "igstamount": "igst_amount",
        # Total Amount variations
        "total amount": "total_amount",
        "total_amount": "total_amount",
        "totalamount": "total_amount",
        # Status
        "status": "status",
        # Payment Terms variations
        "payment terms": "payment_terms",
        "payment_terms": "payment_terms",
        "paymentterms": "payment_terms",
        # Salesperson
        "salesperson": "salesperson",
        # Region
        "region": "region",
        # Territory
        "territory": "territory",
        # Department
        "department": "department",
        # Branch
        "branch": "branch",
        # Branch GSTIN variations
        "branch gstin": "branch_gstin",
        "branch_gstin": "branch_gstin",
        "branchgstin": "branch_gstin",
        # Project ID variations
        "project id": "project_id",
        "project_id": "project_id",
        "projectid": "project_id",
        # Project Name variations
        "project name": "project_name",
        "project_name": "project_name",
        "projectname": "project_name",
        # Billing Type variations
        "billing type": "billing_type",
        "billing_type": "billing_type",
        "billingtype": "billing_type",
        # Billable Hours variations
        "billable hours": "billable_hours",
        "billable_hours": "billable_hours",
        "billablehours": "billable_hours",
        # Is Recurring variations
        "is recurring": "is_recurring",
        "is_recurring": "is_recurring",
        "isrecurring": "is_recurring",
        # Notes
        "notes": "notes",
    }

    # Expected model field names (for validation)
    EXPECTED_COLUMNS = list(set(EXCEL_TO_FIELD_MAPPING.values()))

    # Required columns (model field names)
    REQUIRED_COLUMNS = [
        "invoice_number",
        "invoice_date",
        "due_date",
        "customer_name",
        "product_name",
        "total_amount",
    ]

    def post(self, request):
        """Import revenue invoices from Excel file"""
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

        except RevenueInvoiceImportError as e:
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
            raise RevenueInvoiceImportError(
                "Unable to read the uploaded Excel file."
            ) from exc

        if not workbook.sheetnames:
            raise RevenueInvoiceImportError(
                "The Excel file does not contain any sheets."
            )

        # Use the first sheet
        sheet = workbook[workbook.sheetnames[0]]

        if sheet.max_row < 2:
            raise RevenueInvoiceImportError("The sheet does not contain any data rows.")

        # Locate header row
        header_map, header_row_index = self._locate_header_row(sheet)
        if not header_map or header_row_index is None:
            raise RevenueInvoiceImportError(
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
            raise RevenueInvoiceImportError(error_msg)

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
                    "invoice_date",
                    "due_date",
                    "customer_name",
                    "product_name",
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

    def _extract_row_payload(self, row, header_map: Dict[int, str]) -> Dict[str, any]:
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
        self, row_payload: Dict, date1904: bool
    ) -> Dict[str, any]:
        """Transform Excel row data to invoice model data"""
        invoice_data = {}

        # Basic Invoice Information
        if "invoice_number" in row_payload and row_payload["invoice_number"]:
            invoice_data["invoice_number"] = str(row_payload["invoice_number"]).strip()

        if "invoice_date" in row_payload and row_payload["invoice_date"]:
            invoice_data["invoice_date"] = self._parse_date(
                row_payload["invoice_date"], date1904
            )

        if "due_date" in row_payload and row_payload["due_date"]:
            invoice_data["due_date"] = self._parse_date(
                row_payload["due_date"], date1904
            )

        # Customer Information
        if "customer_name" in row_payload and row_payload["customer_name"]:
            invoice_data["customer_name"] = str(row_payload["customer_name"]).strip()

        if "customer_gstin" in row_payload and row_payload["customer_gstin"]:
            invoice_data["customer_gstin"] = str(row_payload["customer_gstin"]).strip()

        # Product/Service Information
        if "product_name" in row_payload and row_payload["product_name"]:
            invoice_data["product_name"] = str(row_payload["product_name"]).strip()

        if "service_type" in row_payload and row_payload["service_type"]:
            invoice_data["service_type"] = str(row_payload["service_type"]).strip()

        if "hsn_sac_code" in row_payload and row_payload["hsn_sac_code"]:
            invoice_data["hsn_sac_code"] = str(row_payload["hsn_sac_code"]).strip()

        # Location Information
        if "place_of_supply" in row_payload and row_payload["place_of_supply"]:
            invoice_data["place_of_supply"] = str(
                row_payload["place_of_supply"]
            ).strip()

        # Quantity and Pricing
        if "quantity" in row_payload and row_payload["quantity"] is not None:
            invoice_data["quantity"] = self._parse_decimal(row_payload["quantity"])

        if "unit_price" in row_payload and row_payload["unit_price"] is not None:
            invoice_data["unit_price"] = self._parse_decimal(row_payload["unit_price"])

        if "taxable_value" in row_payload and row_payload["taxable_value"] is not None:
            invoice_data["taxable_value"] = self._parse_decimal(
                row_payload["taxable_value"]
            )

        # GST Details
        if "cgst_rate" in row_payload and row_payload["cgst_rate"] is not None:
            invoice_data["cgst_rate"] = self._parse_decimal(row_payload["cgst_rate"])

        if "cgst_amount" in row_payload and row_payload["cgst_amount"] is not None:
            invoice_data["cgst_amount"] = self._parse_decimal(
                row_payload["cgst_amount"]
            )

        if "sgst_rate" in row_payload and row_payload["sgst_rate"] is not None:
            invoice_data["sgst_rate"] = self._parse_decimal(row_payload["sgst_rate"])

        if "sgst_amount" in row_payload and row_payload["sgst_amount"] is not None:
            invoice_data["sgst_amount"] = self._parse_decimal(
                row_payload["sgst_amount"]
            )

        if "igst_rate" in row_payload and row_payload["igst_rate"] is not None:
            invoice_data["igst_rate"] = self._parse_decimal(row_payload["igst_rate"])

        if "igst_amount" in row_payload and row_payload["igst_amount"] is not None:
            invoice_data["igst_amount"] = self._parse_decimal(
                row_payload["igst_amount"]
            )

        # Total Amount
        if "total_amount" in row_payload and row_payload["total_amount"] is not None:
            invoice_data["total_amount"] = self._parse_decimal(
                row_payload["total_amount"]
            )

        # Status and Payment
        if "status" in row_payload and row_payload["status"]:
            status_value = self._match_status(str(row_payload["status"]).strip())
            if status_value:
                invoice_data["status"] = status_value
            else:
                raise ValueError(
                    f"Invalid status value: {row_payload['status']}. "
                    f"Valid values: {', '.join([s[1] for s in InvoicesStatusChoices.choices])}"
                )

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

        # Sales Information
        if "salesperson" in row_payload and row_payload["salesperson"]:
            invoice_data["salesperson"] = str(row_payload["salesperson"]).strip()

        # Geographic Information
        if "region" in row_payload and row_payload["region"]:
            invoice_data["region"] = str(row_payload["region"]).strip()

        if "territory" in row_payload and row_payload["territory"]:
            invoice_data["territory"] = str(row_payload["territory"]).strip()

        # Organizational Information
        if "department" in row_payload and row_payload["department"]:
            invoice_data["department"] = str(row_payload["department"]).strip()

        # Branch Information
        if "branch" in row_payload and row_payload["branch"]:
            invoice_data["branch"] = str(row_payload["branch"]).strip()

        if "branch_gstin" in row_payload and row_payload["branch_gstin"]:
            invoice_data["branch_gstin"] = str(row_payload["branch_gstin"]).strip()

        # Project Information
        if "project_id" in row_payload and row_payload["project_id"]:
            invoice_data["project_id"] = str(row_payload["project_id"]).strip()

        if "project_name" in row_payload and row_payload["project_name"]:
            invoice_data["project_name"] = str(row_payload["project_name"]).strip()

        # Billing Information
        if "billing_type" in row_payload and row_payload["billing_type"]:
            invoice_data["billing_type"] = str(row_payload["billing_type"]).strip()

        if (
            "billable_hours" in row_payload
            and row_payload["billable_hours"] is not None
        ):
            invoice_data["billable_hours"] = self._parse_decimal(
                row_payload["billable_hours"]
            )

        # Recurring Information
        if "is_recurring" in row_payload and row_payload["is_recurring"] is not None:
            invoice_data["is_recurring"] = self._parse_boolean(
                row_payload["is_recurring"]
            )

        # Additional Information
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

    def _parse_boolean(self, value) -> bool:
        """Parse boolean from Excel value"""
        if value is None:
            return False

        if isinstance(value, bool):
            return value

        if isinstance(value, (int, float)):
            return bool(value)

        if isinstance(value, str):
            value_lower = value.lower().strip()
            if value_lower in ["true", "yes", "y", "1", "on"]:
                return True
            elif value_lower in ["false", "no", "n", "0", "off", ""]:
                return False

        raise ValueError(f"Unable to parse boolean: {value}")

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
