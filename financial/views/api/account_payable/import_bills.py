import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from django.core.exceptions import ValidationError
from openpyxl import load_workbook
from openpyxl.utils.datetime import from_excel
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Company
from financial.enums import BillsStatusChoices, InvoicesPaymentTerms
from financial.models.expenses.bills import Bill
from financial.models.account_payable.vendor import Vendor
from financial.views.api.account_payable.ap_aging import get_company_from_request


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
    Excel Import API for Expense Bills
    Accepts an Excel file and imports bill data into the database.

    Expected Excel columns (all fields from Bill model):
    Required:
    - bill_number
    - bill_date
    - vendor_name (or vendor can be matched)
    - subtotal

    Optional:
    - due_date (will be calculated from bill_date + payment_terms if not provided)
    - vendor_gstin
    - vendor_pan
    - is_vendor_out_of_india
    - item_name
    - hsn_sac
    - category
    - place_of_supply
    - cgst_percentage
    - sgst_percentage
    - igst_percentage
    - tds_section
    - tds_percentage
    - payment_terms
    - paid_amount
    - status
    - branch
    - branch_gstin
    - department
    - eligibility
    - is_recurring
    - notes
    """

    permission_classes = [IsAuthenticated]

    # Mapping from Excel column names (various formats) to model field names
    EXCEL_TO_FIELD_MAPPING = {
        # Bill Number variations
        "bill number": "bill_number",
        "bill_number": "bill_number",
        "billnumber": "bill_number",
        "bill no": "bill_number",
        "bill_no": "bill_number",
        # Bill Date variations
        "bill date": "bill_date",
        "bill_date": "bill_date",
        "billdate": "bill_date",
        "date": "bill_date",
        # Due Date variations
        "due date": "due_date",
        "due_date": "due_date",
        "duedate": "due_date",
        # Vendor Name variations
        "vendor name": "vendor_name",
        "vendor_name": "vendor_name",
        "vendorname": "vendor_name",
        "vendor": "vendor_name",
        "supplier": "vendor_name",
        "supplier name": "vendor_name",
        # Vendor GSTIN variations
        "vendor gstin": "vendor_gstin",
        "vendor_gstin": "vendor_gstin",
        "vendorgstin": "vendor_gstin",
        "gstin": "vendor_gstin",
        "gst number": "vendor_gstin",
        # Vendor PAN variations
        "vendor pan": "vendor_pan",
        "vendor_pan": "vendor_pan",
        "vendorpan": "vendor_pan",
        "pan": "vendor_pan",
        "pan number": "vendor_pan",
        # Is Vendor Out of India
        "is vendor out of india": "is_vendor_out_of_india",
        "is_vendor_out_of_india": "is_vendor_out_of_india",
        "vendor out of india": "is_vendor_out_of_india",
        "overseas vendor": "is_vendor_out_of_india",
        # Item Name variations
        "item name": "item_name",
        "item_name": "item_name",
        "itemname": "item_name",
        "item": "item_name",
        "product": "item_name",
        # HSN/SAC variations
        "hsn sac": "hsn_sac",
        "hsn_sac": "hsn_sac",
        "hsnsac": "hsn_sac",
        "hsn": "hsn_sac",
        "sac": "hsn_sac",
        "hsn/sac": "hsn_sac",
        # Category variations
        "category": "category",
        # Place of Supply variations
        "place of supply": "place_of_supply",
        "place_of_supply": "place_of_supply",
        "placeofsupply": "place_of_supply",
        # Subtotal variations
        "subtotal": "subtotal",
        "sub total": "subtotal",
        "sub_total": "subtotal",
        "base amount": "subtotal",
        "base_amount": "subtotal",
        # CGST Percentage variations
        "cgst %": "cgst_percentage",
        "cgst_percentage": "cgst_percentage",
        "cgst percentage": "cgst_percentage",
        "cgst%": "cgst_percentage",
        "cgst rate": "cgst_percentage",
        "cgst_rate": "cgst_percentage",
        # CGST Amount variations
        "cgst amount": "cgst_amount",
        "cgst_amount": "cgst_amount",
        "cgstamount": "cgst_amount",
        # SGST Percentage variations
        "sgst %": "sgst_percentage",
        "sgst_percentage": "sgst_percentage",
        "sgst percentage": "sgst_percentage",
        "sgst%": "sgst_percentage",
        "sgst rate": "sgst_percentage",
        "sgst_rate": "sgst_percentage",
        # SGST Amount variations
        "sgst amount": "sgst_amount",
        "sgst_amount": "sgst_amount",
        "sgstamount": "sgst_amount",
        # IGST Percentage variations
        "igst %": "igst_percentage",
        "igst_percentage": "igst_percentage",
        "igst percentage": "igst_percentage",
        "igst%": "igst_percentage",
        "igst rate": "igst_percentage",
        "igst_rate": "igst_percentage",
        # IGST Amount variations
        "igst amount": "igst_amount",
        "igst_amount": "igst_amount",
        "igstamount": "igst_amount",
        # TDS Section variations
        "tds section": "tds_section",
        "tds_section": "tds_section",
        "tdssection": "tds_section",
        # TDS Percentage variations
        "tds %": "tds_percentage",
        "tds_percentage": "tds_percentage",
        "tds percentage": "tds_percentage",
        "tds%": "tds_percentage",
        "tds rate": "tds_percentage",
        "tds_rate": "tds_percentage",
        # TDS Amount variations
        "tds amount": "tds_amount",
        "tds_amount": "tds_amount",
        "tdsamount": "tds_amount",
        # Total variations
        "total": "total",
        "total amount": "total",
        "total_amount": "total",
        # Payment Terms variations
        "payment terms": "payment_terms",
        "payment_terms": "payment_terms",
        "paymentterms": "payment_terms",
        "terms": "payment_terms",
        # Paid Amount variations
        "paid amount": "paid_amount",
        "paid_amount": "paid_amount",
        "paidamount": "paid_amount",
        # Status variations
        "status": "status",
        # Branch variations
        "branch": "branch",
        # Branch GSTIN variations
        "branch gstin": "branch_gstin",
        "branch_gstin": "branch_gstin",
        "branchgstin": "branch_gstin",
        # Department variations
        "department": "department",
        # Eligibility variations
        "eligibility": "eligibility",
        # Is Recurring variations
        "is recurring": "is_recurring",
        "is_recurring": "is_recurring",
        "isrecurring": "is_recurring",
        "recurring": "is_recurring",
        # Notes variations
        "notes": "notes",
        "note": "notes",
        "remarks": "notes",
    }

    # Expected model field names (for validation)
    EXPECTED_COLUMNS = list(set(EXCEL_TO_FIELD_MAPPING.values()))

    # Required columns (model field names)
    REQUIRED_COLUMNS = [
        "bill_date",
        "vendor_name",
        "subtotal",
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
        normalized_headers = set()
        for excel_header in header_map.values():
            field_name = self._normalize_excel_header(excel_header)
            if field_name:
                normalized_headers.add(field_name)

        missing_columns = [
            col for col in self.REQUIRED_COLUMNS if col not in normalized_headers
        ]
        if missing_columns:
            found_headers = list(header_map.values())[:10]
            error_msg = (
                f"Missing required columns: {', '.join(missing_columns)}. "
                f"Found Excel headers: {', '.join(found_headers)}"
            )
            raise BillImportError(error_msg)

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

            try:
                # Transform row data to bill data
                bill_data = self._transform_row_payload(
                    row_payload, date1904, company, user, row_number
                )

                # Create or update bill
                bill, created = Bill.objects.update_or_create(
                    company=company,
                    bill_number=bill_data["bill_number"],
                    defaults=bill_data,
                )

                if created:
                    result.created += 1
                else:
                    result.updated += 1

            except Exception as e:
                result.skipped.append((row_number, f"Error processing row: {str(e)}"))
                result.errors.append(f"Row {row_number}: {str(e)}")

        return result

    def _normalize_excel_header(self, header: str) -> Optional[str]:
        """Normalize Excel header to model field name"""
        if not header:
            return None
        header_lower = str(header).strip().lower()
        return self.EXCEL_TO_FIELD_MAPPING.get(header_lower)

    def _locate_header_row(
        self, sheet
    ) -> Tuple[Optional[Dict[int, str]], Optional[int]]:
        """Locate the header row in the sheet"""
        # Try first 5 rows
        for row_idx in range(1, min(6, sheet.max_row + 1)):
            row = sheet[row_idx]
            header_map = {}
            for cell in row:
                if cell.value:
                    header_name = self._normalize_excel_header(str(cell.value))
                    if header_name:
                        header_map[cell.column] = str(cell.value)
            if len(header_map) >= 3:  # At least 3 valid headers found
                return header_map, row_idx
        return None, None

    def _extract_row_payload(self, row, header_map: Dict[int, str]) -> Dict[str, any]:
        """Extract data from a row based on header mapping"""
        payload = {}
        for cell in row:
            if cell.column in header_map:
                field_name = self._normalize_excel_header(header_map[cell.column])
                if field_name:
                    payload[field_name] = cell.value
        return payload

    def _row_is_empty(self, row_payload: Dict) -> bool:
        """Check if a row is empty"""
        return all(
            value is None or (isinstance(value, str) and not value.strip())
            for value in row_payload.values()
        )

    def _parse_date(self, value, date1904: bool = False):
        """Parse date from Excel value"""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            try:
                # Try common date formats
                for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"]:
                    try:
                        return datetime.strptime(value.strip(), fmt).date()
                    except ValueError:
                        continue
            except:
                pass
        try:
            if isinstance(value, (int, float)):
                return from_excel(value, date1904).date()
        except:
            pass
        return None

    def _parse_decimal(self, value) -> Decimal:
        """Parse decimal from value"""
        if value is None:
            return Decimal("0.00")
        if isinstance(value, Decimal):
            return value
        if isinstance(value, (int, float)):
            return Decimal(str(value))
        if isinstance(value, str):
            # Remove currency symbols and commas
            cleaned = re.sub(r"[₹$,\s]", "", value.strip())
            try:
                return Decimal(cleaned)
            except (InvalidOperation, ValueError):
                return Decimal("0.00")
        return Decimal("0.00")

    def _parse_boolean(self, value) -> bool:
        """Parse boolean from value"""
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ["true", "yes", "1", "y"]
        if isinstance(value, (int, float)):
            return bool(value)
        return False

    def _parse_payment_terms(self, value) -> str:
        """Parse payment terms and match to enum"""
        if not value:
            return ""
        value_str = str(value).strip()
        # Try to match to enum choices
        for choice_value, choice_label in InvoicesPaymentTerms.choices:
            if value_str.lower() in [choice_value.lower(), choice_label.lower()]:
                return choice_value
        # Return as-is if no match
        return value_str

    def _parse_status(self, value) -> str:
        """Parse status and match to enum"""
        if not value:
            return BillsStatusChoices.PENDING
        value_str = str(value).strip().lower()
        for choice_value, choice_label in BillsStatusChoices.choices:
            if value_str == choice_value.lower() or value_str == choice_label.lower():
                return choice_value
        return BillsStatusChoices.PENDING

    def _transform_row_payload(
        self,
        row_payload: Dict,
        date1904: bool,
        company: Company,
        user,
        row_number: int = None,
    ) -> Dict[str, any]:
        """Transform Excel row data to bill model data"""
        bill_data = {}

        # Parse bill_date first (needed for bill number generation)
        bill_date = self._parse_date(row_payload.get("bill_date"), date1904)
        if not bill_date:
            raise ValueError("bill_date is required and must be a valid date")
        bill_data["bill_date"] = bill_date

        # Bill number - generate if not provided
        bill_number = str(row_payload.get("bill_number", "")).strip()
        if not bill_number:
            # Auto-generate bill number: BILL-YYYY-MMDD-XXXX
            date_str = bill_date.strftime("%Y-%m%d")
            # Use row number or timestamp for uniqueness
            suffix = (
                f"{row_number:04d}" if row_number else datetime.now().strftime("%H%M%S")
            )
            bill_number = f"BILL-{date_str}-{suffix}"
        bill_data["bill_number"] = bill_number

        vendor_name = str(row_payload.get("vendor_name", "")).strip()
        if not vendor_name:
            raise ValueError("vendor_name is required")
        bill_data["vendor_name"] = vendor_name

        subtotal = self._parse_decimal(row_payload.get("subtotal"))
        if subtotal <= 0:
            raise ValueError("subtotal must be greater than 0")
        bill_data["subtotal"] = subtotal

        # Get or create vendor
        vendor, created = Vendor.objects.get_or_create(
            company=company,
            name=vendor_name,
            defaults={
                "created_by": user,
                "updated_by": user,
            },
        )
        bill_data["vendor"] = vendor

        # Update vendor GSTIN/PAN if provided
        if row_payload.get("vendor_gstin"):
            vendor.gstin = str(row_payload.get("vendor_gstin")).strip()
        if row_payload.get("vendor_pan"):
            vendor.pan = str(row_payload.get("vendor_pan")).strip()
        if created or vendor.gstin or vendor.pan:
            vendor.save()

        # Optional fields
        if row_payload.get("due_date"):
            due_date = self._parse_date(row_payload.get("due_date"), date1904)
            if due_date:
                bill_data["due_date"] = due_date
        else:
            # Calculate due_date from payment_terms if provided
            payment_terms = self._parse_payment_terms(row_payload.get("payment_terms"))
            if payment_terms:
                bill_data["payment_terms"] = payment_terms
                # Calculate due_date
                days = self._parse_payment_terms_days(payment_terms)
                if days > 0:
                    bill_data["due_date"] = bill_date + timedelta(days=days)
                else:
                    bill_data["due_date"] = bill_date
            else:
                bill_data["due_date"] = bill_date

        bill_data["vendor_gstin"] = str(row_payload.get("vendor_gstin", "")).strip()
        bill_data["vendor_pan"] = str(row_payload.get("vendor_pan", "")).strip()
        bill_data["is_vendor_out_of_india"] = self._parse_boolean(
            row_payload.get("is_vendor_out_of_india")
        )
        bill_data["item_name"] = str(row_payload.get("item_name", "")).strip()
        bill_data["hsn_sac"] = str(row_payload.get("hsn_sac", "")).strip()
        bill_data["category"] = str(row_payload.get("category", "")).strip()
        bill_data["place_of_supply"] = str(
            row_payload.get("place_of_supply", "")
        ).strip()

        # GST fields
        bill_data["cgst_percentage"] = self._parse_decimal(
            row_payload.get("cgst_percentage")
        )
        bill_data["sgst_percentage"] = self._parse_decimal(
            row_payload.get("sgst_percentage")
        )
        bill_data["igst_percentage"] = self._parse_decimal(
            row_payload.get("igst_percentage")
        )

        # TDS fields
        bill_data["tds_section"] = str(row_payload.get("tds_section", "")).strip()
        bill_data["tds_percentage"] = self._parse_decimal(
            row_payload.get("tds_percentage")
        )

        # Payment and status
        if row_payload.get("payment_terms"):
            bill_data["payment_terms"] = self._parse_payment_terms(
                row_payload.get("payment_terms")
            )
        bill_data["paid_amount"] = self._parse_decimal(row_payload.get("paid_amount"))
        bill_data["status"] = self._parse_status(row_payload.get("status"))

        # Organizational fields
        bill_data["branch"] = str(row_payload.get("branch", "")).strip()
        bill_data["branch_gstin"] = str(row_payload.get("branch_gstin", "")).strip()
        bill_data["department"] = str(row_payload.get("department", "")).strip()
        bill_data["eligibility"] = str(row_payload.get("eligibility", "")).strip()
        bill_data["is_recurring"] = self._parse_boolean(row_payload.get("is_recurring"))
        bill_data["notes"] = str(row_payload.get("notes", "")).strip()

        # Set user fields
        bill_data["created_by"] = user
        bill_data["updated_by"] = user

        # Note: CGST/SGST/IGST amounts, TDS amount, and Total will be calculated
        # automatically in the Bill model's save() method

        return bill_data

    def _parse_payment_terms_days(self, payment_terms: str) -> int:
        """Parse payment terms string to get number of days"""
        if not payment_terms:
            return 0
        if payment_terms.upper() == "COD":
            return 0
        match = re.search(r"\d+", payment_terms)
        if match:
            return int(match.group())
        return 0
