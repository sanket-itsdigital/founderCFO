from collections import defaultdict
from decimal import Decimal

from django.db.models import F, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Company
from financial.models.account_receivable import Invoice
from financial.enums import InvoicesStatusChoices
from financial.serializers.customer_segments import CustomerSegmentsSerializer
from financial.views.api.ar_aging import get_company_from_request


class CustomerSegmentsView(APIView):
    """
    API view to get Customer Segments based on payment behavior.

    Segments:
    1. Premium Payers: Pay within 15 days, < 10% overdue rate, High revenue
    2. Reliable Partners: Pay within terms, < 20% overdue rate, Consistent
    3. Watch List: Pay 30-45 days, 20-40% overdue rate, Need monitoring
    4. High Risk: Pay > 45 days, > 40% overdue rate, Credit risk
    """

    permission_classes = [IsAuthenticated]

    # Segment definitions
    SEGMENT_PREMIUM_PAYERS = "Premium Payers"
    SEGMENT_RELIABLE_PARTNERS = "Reliable Partners"
    SEGMENT_WATCH_LIST = "Watch List"
    SEGMENT_HIGH_RISK = "High Risk"

    @staticmethod
    def _in_lakhs(amount: Decimal) -> str:
        """Convert amount to lakhs format (₹XX.XXL)"""
        if amount == 0:
            return "₹0.00L"
        lakhs = amount / Decimal("100000")
        return f"₹{lakhs.quantize(Decimal('0.01'))}L"

    def _calculate_payment_days(self, invoice):
        """
        Calculate payment days for an invoice.
        Payment days = days from invoice_date to when payment was received (or expected).
        Since we don't have payment_date, we estimate:
        - For paid invoices: assume paid on due_date (payment terms duration)
        - For overdue invoices: payment terms + days overdue
        - For partial/pending: days since invoice_date (current outstanding)
        """
        today = timezone.now().date()
        payment_terms_days = (invoice.due_date - invoice.invoice_date).days

        if invoice.status == InvoicesStatusChoices.PAID:
            # For paid invoices, assume they paid on the due_date (payment terms)
            # This is a reasonable estimate since we don't have actual payment_date
            return max(0, payment_terms_days)
        elif invoice.status == InvoicesStatusChoices.OVERDUE:
            # For overdue invoices, calculate: payment terms + days overdue
            days_overdue = (today - invoice.due_date).days
            return max(0, payment_terms_days + days_overdue)
        elif invoice.status == InvoicesStatusChoices.PARTIAL:
            # For partial payments, use days since invoice (still outstanding)
            days_since_invoice = (today - invoice.invoice_date).days
            return max(0, days_since_invoice)
        else:
            # For pending/draft invoices, use days since invoice
            days_since_invoice = (today - invoice.invoice_date).days
            return max(0, days_since_invoice)

    def _calculate_customer_metrics(self, invoices):
        """
        Calculate metrics for a customer based on their invoices.
        Returns: (avg_payment_days, overdue_rate, total_revenue)
        """
        if not invoices:
            return 0, 0.0, Decimal("0.00")

        total_revenue = Decimal("0.00")
        payment_days_list = []
        overdue_count = 0
        total_invoices = len(invoices)

        for invoice in invoices:
            total_revenue += invoice.total_amount

            # Calculate payment days
            payment_days = self._calculate_payment_days(invoice)
            payment_days_list.append(payment_days)

            # Check if overdue
            if invoice.is_overdue:
                overdue_count += 1

        # Calculate average payment days
        avg_payment_days = (
            int(sum(payment_days_list) / len(payment_days_list))
            if payment_days_list
            else 0
        )

        # Calculate overdue rate
        overdue_rate = (
            (overdue_count / total_invoices * 100) if total_invoices > 0 else 0.0
        )

        return avg_payment_days, overdue_rate, total_revenue

    def _assign_segment(self, avg_payment_days, overdue_rate, total_revenue):
        """
        Assign customer to a segment based on characteristics.

        Criteria (checked in order of priority):
        1. High Risk: Pay > 45 days OR > 40% overdue rate
        2. Premium Payers: Pay within 15 days AND < 10% overdue rate
        3. Reliable Partners: Pay within terms (<=30 days) AND < 20% overdue rate (but not Premium)
        4. Watch List: Pay 30-45 days OR 20-40% overdue rate (but not High Risk)
        5. Default: Watch List for any remaining cases
        """
        # High Risk: Pay > 45 days OR > 40% overdue rate (check first - most critical)
        if avg_payment_days > 45 or overdue_rate > 40:
            return self.SEGMENT_HIGH_RISK

        # Premium Payers: Pay within 15 days AND < 10% overdue rate (most restrictive positive)
        if avg_payment_days <= 15 and overdue_rate < 10:
            return self.SEGMENT_PREMIUM_PAYERS

        # Reliable Partners: Pay within terms (<=30 days) AND < 20% overdue rate
        # Exclude those that would be Premium Payers (already handled above)
        if avg_payment_days <= 30 and overdue_rate < 20:
            return self.SEGMENT_RELIABLE_PARTNERS

        # Watch List: Pay 30-45 days OR 20-40% overdue rate
        # This catches customers that don't fit the above categories
        if (30 <= avg_payment_days <= 45) or (20 <= overdue_rate <= 40):
            return self.SEGMENT_WATCH_LIST

        # Default to Watch List for any edge cases
        return self.SEGMENT_WATCH_LIST

    def _get_segment_characteristics(self, segment_name):
        """Get characteristics for a segment"""
        characteristics_map = {
            self.SEGMENT_PREMIUM_PAYERS: [
                "Pay within 15 days",
                "< 10% overdue rate",
                "High revenue",
            ],
            self.SEGMENT_RELIABLE_PARTNERS: [
                "Pay within terms",
                "< 20% overdue rate",
                "Consistent",
            ],
            self.SEGMENT_WATCH_LIST: [
                "Pay 30-45 days",
                "20-40% overdue rate",
                "Need monitoring",
            ],
            self.SEGMENT_HIGH_RISK: [
                "Pay > 45 days",
                "> 40% overdue rate",
                "Credit risk",
            ],
        }
        return characteristics_map.get(segment_name, [])

    def _get_segment_risk_level(self, segment_name):
        """Get risk level for a segment"""
        risk_level_map = {
            self.SEGMENT_PREMIUM_PAYERS: "Low Risk",
            self.SEGMENT_RELIABLE_PARTNERS: "Low Risk",
            self.SEGMENT_WATCH_LIST: "Medium Risk",
            self.SEGMENT_HIGH_RISK: "High Risk",
        }
        return risk_level_map.get(segment_name, "Medium Risk")

    def get(self, request, *args, **kwargs):
        """Calculate and return customer segments"""
        company = get_company_from_request(request)
        if not company:
            # Return all segments with zero values
            empty_segments = []
            empty_segment_details = []
            segment_order = [
                self.SEGMENT_PREMIUM_PAYERS,
                self.SEGMENT_RELIABLE_PARTNERS,
                self.SEGMENT_WATCH_LIST,
                self.SEGMENT_HIGH_RISK,
            ]
            for segment_name in segment_order:
                empty_segments.append(
                    {
                        "segment_name": segment_name,
                        "customer_count": 0,
                        "total_revenue": 0.0,
                        "total_revenue_display": "₹0.00L",
                        "avg_payment_days": 0,
                        "risk_level": self._get_segment_risk_level(segment_name),
                        "characteristics": self._get_segment_characteristics(
                            segment_name
                        ),
                        "customers": [],
                    }
                )
                empty_segment_details.append(
                    {
                        "segment": segment_name,
                        "customers": 0,
                        "total_revenue": 0.0,
                        "total_revenue_display": "₹0.00L",
                        "avg_payment_days": 0,
                        "risk_level": self._get_segment_risk_level(segment_name),
                        "characteristics": self._get_segment_characteristics(
                            segment_name
                        ),
                    }
                )
            return Response(
                {
                    "segments": empty_segments,
                    "segment_details": empty_segment_details,
                    "customer_distribution": {
                        self.SEGMENT_PREMIUM_PAYERS: 0,
                        self.SEGMENT_RELIABLE_PARTNERS: 0,
                        self.SEGMENT_WATCH_LIST: 0,
                        self.SEGMENT_HIGH_RISK: 0,
                    },
                    "revenue_by_segment": {
                        self.SEGMENT_PREMIUM_PAYERS: 0.0,
                        self.SEGMENT_RELIABLE_PARTNERS: 0.0,
                        self.SEGMENT_WATCH_LIST: 0.0,
                        self.SEGMENT_HIGH_RISK: 0.0,
                    },
                },
                status=status.HTTP_200_OK,
            )

        # Get all invoices for the company (excluding cancelled)
        invoices = Invoice.objects.filter(company=company).exclude(
            status=InvoicesStatusChoices.CANCELLED
        )

        # Group invoices by customer
        customer_invoices = defaultdict(list)
        for invoice in invoices:
            customer_invoices[invoice.customer_name].append(invoice)

        # Calculate metrics and assign segments
        segments_data = defaultdict(
            lambda: {
                "customers": [],
                "total_revenue": Decimal("0.00"),
                "total_payment_days": 0,
                "customer_count": 0,
            }
        )

        for customer_name, customer_inv_list in customer_invoices.items():
            avg_payment_days, overdue_rate, total_revenue = (
                self._calculate_customer_metrics(customer_inv_list)
            )
            segment = self._assign_segment(
                avg_payment_days, overdue_rate, total_revenue
            )

            segments_data[segment]["customers"].append(
                {
                    "customer_name": customer_name,
                    "invoice_count": len(customer_inv_list),
                    "total_revenue": float(total_revenue),
                    "total_revenue_display": self._in_lakhs(total_revenue),
                    "avg_payment_days": avg_payment_days,
                    "risk_level": self._get_segment_risk_level(segment),
                }
            )

            segments_data[segment]["total_revenue"] += total_revenue
            segments_data[segment]["total_payment_days"] += avg_payment_days
            segments_data[segment]["customer_count"] += 1

        # Build segment summaries
        segments_list = []
        segment_details_list = []
        segment_order = [
            self.SEGMENT_PREMIUM_PAYERS,
            self.SEGMENT_RELIABLE_PARTNERS,
            self.SEGMENT_WATCH_LIST,
            self.SEGMENT_HIGH_RISK,
        ]

        customer_distribution = {}
        revenue_by_segment = {}

        for segment_name in segment_order:
            data = segments_data[segment_name]
            customer_count = data["customer_count"]
            total_revenue = data["total_revenue"]

            # Calculate average payment days for segment
            avg_payment_days = 0
            if customer_count > 0:
                avg_payment_days = int(data["total_payment_days"] / customer_count)

            # Build segment summary with customer details
            segments_list.append(
                {
                    "segment_name": segment_name,
                    "customer_count": customer_count,
                    "total_revenue": float(total_revenue),
                    "total_revenue_display": self._in_lakhs(total_revenue),
                    "avg_payment_days": avg_payment_days,
                    "risk_level": self._get_segment_risk_level(segment_name),
                    "characteristics": self._get_segment_characteristics(segment_name),
                    "customers": data["customers"],
                }
            )

            # Build segment details table row (without customer details)
            segment_details_list.append(
                {
                    "segment": segment_name,
                    "customers": customer_count,
                    "total_revenue": float(total_revenue),
                    "total_revenue_display": self._in_lakhs(total_revenue),
                    "avg_payment_days": avg_payment_days,
                    "risk_level": self._get_segment_risk_level(segment_name),
                    "characteristics": self._get_segment_characteristics(segment_name),
                }
            )

            # Build distribution data
            customer_distribution[segment_name] = customer_count
            revenue_by_segment[segment_name] = float(total_revenue)

        response_data = {
            "segments": segments_list,
            "segment_details": segment_details_list,
            "customer_distribution": customer_distribution,
            "revenue_by_segment": revenue_by_segment,
        }

        # Validate with serializer
        serializer = CustomerSegmentsSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data, status=status.HTTP_200_OK)
