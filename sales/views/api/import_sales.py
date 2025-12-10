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
from sales.enums import (
    SalesNextStepChoices,
    SalesProductChoices,
    SalesSourceChoices,
    SalesStageStatusChoices,
)
from sales.models import Sales, SalesTeam
from sales.views.api.utils import get_company_from_request


@dataclass
class ImportResult:
    """Result of Excel import operation"""

    created: int = 0
    updated: int = 0
    skipped: List[Tuple[int, str]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class SalesImportError(Exception):
    """Custom exception for sales import errors"""

    pass


class SalesImportView(APIView):
    """
    Excel Import API for Sales
    Accepts an Excel file and imports sales/deal data into the database.

    Expected Excel columns:
    1. deal_id
    2. account
    3. deal_name
    4. amount
    5. mrr
    6. stage
    7. owner
    8. probability
    9. close_date
    10. product
    11. contract_term
    12. days_in_stage
    13. last_activity
    14. source
    15. next_step
    16. loss_reason
    17. competitor
    18. notes
    """

    permission_classes = [IsAuthenticated]

    # Expected column headers (case-insensitive)
    EXPECTED_COLUMNS = [
        "deal_id",
        "account",
        "deal_name",
        "amount",
        "mrr",
        "stage",
        "owner",
        "probability",
        "close_date",
        "product",
        "contract_term",
        "days_in_stage",
        "last_activity",
        "source",
        "next_step",
        "loss_reason",
        "competitor",
        "notes",
    ]

    # Required columns
    REQUIRED_COLUMNS = [
        "deal_id",
        "deal_name",
        "account",
    ]

    def post(self, request):
        """Import sales from Excel file"""
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
            result = self._import_sales_from_excel(uploaded_file, company, request.user)

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

        except SalesImportError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"error": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _import_sales_from_excel(
        self, uploaded_file, company: Company, user
    ) -> ImportResult:
        """Read the Excel file and create/update Sales records"""
        try:
            uploaded_file.seek(0)
        except (AttributeError, OSError):
            pass

        try:
            workbook = load_workbook(uploaded_file, data_only=True)
        except Exception as exc:
            raise SalesImportError("Unable to read the uploaded Excel file.") from exc

        if not workbook.sheetnames:
            raise SalesImportError("The Excel file does not contain any sheets.")

        # Use the first sheet
        sheet = workbook[workbook.sheetnames[0]]

        if sheet.max_row < 2:
            raise SalesImportError("The sheet does not contain any data rows.")

        # Locate header row
        header_map, header_row_index = self._locate_header_row(sheet)
        if not header_map or header_row_index is None:
            raise SalesImportError(
                "Could not detect the header row. Please ensure the first row contains column headers."
            )

        # Check for required columns
        missing_columns = [
            col
            for col in self.REQUIRED_COLUMNS
            if col.lower() not in [h.lower() for h in header_map.values()]
        ]
        if missing_columns:
            raise SalesImportError(
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
                sales_data = self._transform_row_payload(row_payload, date1904, company)
            except ValueError as exc:
                result.skipped.append((row_number, str(exc)))
                continue

            # Validate required fields
            missing_required = [
                field
                for field in ["deal_id", "deal_name", "client"]
                if not sales_data.get(field)
            ]
            if missing_required:
                result.skipped.append(
                    (
                        row_number,
                        f"Missing required values: {', '.join(missing_required)}",
                    )
                )
                continue

            # Create or update sales record
            try:
                created = self._persist_sales(sales_data, company, user)
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
        """Transform Excel row data to sales model data"""
        sales_data = {}

        # Map deal_id
        if "deal_id" in row_payload:
            sales_data["deal_id"] = str(row_payload["deal_id"]).strip()

        # Map account -> client
        if "account" in row_payload:
            sales_data["client"] = str(row_payload["account"]).strip()

        # Map deal_name
        if "deal_name" in row_payload:
            sales_data["deal_name"] = str(row_payload["deal_name"]).strip()

        # Map amount
        if "amount" in row_payload and row_payload["amount"]:
            sales_data["amount"] = self._parse_decimal(row_payload["amount"])

        # Map mrr
        if "mrr" in row_payload and row_payload["mrr"]:
            sales_data["mrr"] = self._parse_decimal(row_payload["mrr"])

        # Map stage (with enum matching)
        if "stage" in row_payload and row_payload["stage"]:
            stage_value = self._match_stage(str(row_payload["stage"]).strip())
            if stage_value:
                sales_data["stage"] = stage_value
            else:
                raise ValueError(
                    f"Invalid stage value: {row_payload['stage']}. "
                    f"Valid values: {', '.join([s[1] for s in SalesStageStatusChoices.choices])}"
                )

        # Map owner -> sales_team (create/get SalesTeam)
        if "owner" in row_payload and row_payload["owner"]:
            owner_name = str(row_payload["owner"]).strip()
            # Get or create sales team member
            sales_team, created = SalesTeam.objects.get_or_create(
                company=company,
                name=owner_name,
                defaults={
                    "created_by": None,  # Will be set in _persist_sales if needed
                    "updated_by": None,
                },
            )
            sales_data["sales_team"] = sales_team

        # Map probability
        if "probability" in row_payload and row_payload["probability"]:
            probability = self._parse_decimal(row_payload["probability"])
            # Validate probability is between 0 and 100
            if probability < Decimal("0.00") or probability > Decimal("100.00"):
                raise ValueError("Probability must be between 0.00 and 100.00")
            sales_data["probability"] = probability

        # Map close_date
        if "close_date" in row_payload and row_payload["close_date"]:
            sales_data["close_date"] = self._parse_date(
                row_payload["close_date"], date1904
            )

        # Map product -> subscription_product (with enum matching)
        if "product" in row_payload and row_payload["product"]:
            product_value = self._match_product(str(row_payload["product"]).strip())
            if product_value:
                sales_data["subscription_product"] = product_value

        # Map contract_term -> contract_term_months
        if "contract_term" in row_payload and row_payload["contract_term"]:
            try:
                contract_term = int(float(row_payload["contract_term"]))
                if contract_term > 0:
                    sales_data["contract_term_months"] = contract_term
            except (ValueError, TypeError):
                pass  # Skip if can't parse

        # Map days_in_stage
        if "days_in_stage" in row_payload and row_payload["days_in_stage"]:
            try:
                days = int(float(row_payload["days_in_stage"]))
                if days >= 0:
                    sales_data["days_in_stage"] = days
            except (ValueError, TypeError):
                pass  # Skip if can't parse

        # Map last_activity
        if "last_activity" in row_payload and row_payload["last_activity"]:
            sales_data["last_activity"] = self._parse_date(
                row_payload["last_activity"], date1904
            )

        # Map source (with enum matching)
        if "source" in row_payload and row_payload["source"]:
            source_value = self._match_source(str(row_payload["source"]).strip())
            if source_value:
                sales_data["source"] = source_value

        # Map next_step (with enum matching)
        if "next_step" in row_payload and row_payload["next_step"]:
            next_step_value = self._match_next_step(
                str(row_payload["next_step"]).strip()
            )
            if next_step_value:
                sales_data["next_step"] = next_step_value

        # Map loss_reason -> lost_reason
        if "loss_reason" in row_payload and row_payload["loss_reason"]:
            sales_data["lost_reason"] = str(row_payload["loss_reason"]).strip()

        # Map competitor -> competitors
        if "competitor" in row_payload and row_payload["competitor"]:
            sales_data["competitors"] = str(row_payload["competitor"]).strip()

        # Map notes
        if "notes" in row_payload and row_payload["notes"]:
            sales_data["notes"] = str(row_payload["notes"]).strip()

        return sales_data

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

    def _match_stage(self, stage_str: str) -> Optional[str]:
        """Match stage string to enum value"""
        stage_str_lower = stage_str.lower().strip()

        # Direct match
        for value, label in SalesStageStatusChoices.choices:
            if stage_str_lower == value.lower() or stage_str_lower == label.lower():
                return value

        # Fuzzy matching
        stage_mapping = {
            "discovery": SalesStageStatusChoices.DISCOVERY,
            "qualification": SalesStageStatusChoices.QUALIFICATION,
            "proposal": SalesStageStatusChoices.PROPOSAL,
            "negotiation": SalesStageStatusChoices.NEGOTIATION,
            "closed won": SalesStageStatusChoices.CLOSED_WON,
            "closedwon": SalesStageStatusChoices.CLOSED_WON,
            "won": SalesStageStatusChoices.CLOSED_WON,
            "closed lost": SalesStageStatusChoices.CLOSED_LOST,
            "closedlost": SalesStageStatusChoices.CLOSED_LOST,
            "lost": SalesStageStatusChoices.CLOSED_LOST,
            "unqualified": SalesStageStatusChoices.UNQUALIFIED,
        }

        return stage_mapping.get(stage_str_lower)

    def _match_product(self, product_str: str) -> Optional[str]:
        """Match product string to enum value"""
        product_str_lower = product_str.lower().strip()

        # Direct match
        for value, label in SalesProductChoices.choices:
            if product_str_lower == value.lower() or product_str_lower == label.lower():
                return value

        # Fuzzy matching
        product_mapping = {
            "enterprise": SalesProductChoices.ENTERPRISE,
            "pro": SalesProductChoices.PRO,
            "starter": SalesProductChoices.STARTER,
        }

        return product_mapping.get(product_str_lower)

    def _match_source(self, source_str: str) -> Optional[str]:
        """Match source string to enum value"""
        source_str_lower = source_str.lower().strip()

        # Direct match
        for value, label in SalesSourceChoices.choices:
            if source_str_lower == value.lower() or source_str_lower == label.lower():
                return value

        # Fuzzy matching
        source_mapping = {
            "outbound": SalesSourceChoices.OUTBOUND,
            "inbound": SalesSourceChoices.INBOUND,
            "referral": SalesSourceChoices.REFERRAL,
            "event": SalesSourceChoices.EVENT,
            "partner": SalesSourceChoices.PARTNER,
            "social media": SalesSourceChoices.SOCIAL_MEDIA,
            "socialmedia": SalesSourceChoices.SOCIAL_MEDIA,
            "other": SalesSourceChoices.OTHER,
        }

        return source_mapping.get(source_str_lower)

    def _match_next_step(self, next_step_str: str) -> Optional[str]:
        """Match next_step string to enum value"""
        next_step_str_lower = next_step_str.lower().strip()

        # Direct match
        for value, label in SalesNextStepChoices.choices:
            if (
                next_step_str_lower == value.lower()
                or next_step_str_lower == label.lower()
            ):
                return value

        # Fuzzy matching for common variations
        next_step_mapping = {
            "completed": SalesNextStepChoices.COMPLETED,
            "lost": SalesNextStepChoices.LOST,
            "contract review": SalesNextStepChoices.CONTRACT_REVIEW,
            "legal review": SalesNextStepChoices.LEGAL_REVIEW,
            "pricing discussion": SalesNextStepChoices.PRICING_DISCUSSION,
            "final approval": SalesNextStepChoices.FINAL_APPROVAL,
            "proposal presentation": SalesNextStepChoices.PROPOSAL_PRESENTATION,
            "technical validation": SalesNextStepChoices.TECHNICAL_VALIDATION,
            "roi presentation": SalesNextStepChoices.ROI_PRESENTATION,
            "demo follow-up": SalesNextStepChoices.DEMO_FOLLOW_UP,
            "demo followup": SalesNextStepChoices.DEMO_FOLLOW_UP,
            "discovery call": SalesNextStepChoices.DISCOVERY_CALL,
            "technical scoping": SalesNextStepChoices.TECHNICAL_SCOPING,
            "stakeholder mapping": SalesNextStepChoices.STAKEHOLDER_MAPPING,
            "initial assessment": SalesNextStepChoices.INITIAL_ASSESSMENT,
            "intro meeting scheduled": SalesNextStepChoices.INTRO_MEETING_SCHEDULED,
            "demo scheduled": SalesNextStepChoices.DEMO_SCHEDULED,
            "initial contact": SalesNextStepChoices.INITIAL_CONTACT,
            "qualification call": SalesNextStepChoices.QUALIFICATION_CALL,
        }

        return next_step_mapping.get(next_step_str_lower)

    def _persist_sales(self, sales_data: Dict, company: Company, user) -> bool:
        """Create or update a sales record"""
        deal_id = sales_data.get("deal_id")

        # Check if sales record already exists
        try:
            sales = Sales.objects.get(company=company, deal_id=deal_id)
            # Update existing sales record
            for key, value in sales_data.items():
                if key != "sales_team":  # Handle sales_team separately
                    setattr(sales, key, value)
                else:
                    sales.sales_team = value
            sales.updated_by = user
            sales.save()
            return False  # Updated, not created
        except Sales.DoesNotExist:
            # Create new sales record
            sales = Sales.objects.create(
                company=company,
                created_by=user,
                updated_by=user,
                **sales_data,
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
