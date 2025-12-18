from decimal import Decimal
from datetime import timedelta
from collections import defaultdict

from django.db.models import F, Sum, Count, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.utils import get_user_company
from expense.models.bills import Bill
from financial.models.account_payable.payment import BillPayment
from financial.enums import BillsStatusChoices
from financial.serializers.account_payable.ap_dashboard import APDashboardSerializer


class APDashboardView(APIView):
    """
    Comprehensive AP Dashboard API that returns all key metrics.
    All data comes from the Bill model (expenses.bills).

    Returns:
    - Key Performance Indicators (KPIs)
    - AP Health Status
    - GST Summary
    - TDS Summary
    - Cash Outflow Projections
    - Ageing Distribution
    - Key Insights
    - Ageing Breakdown
    """

    permission_classes = [IsAuthenticated]

    @staticmethod
    def _in_lakhs(amount: Decimal) -> str:
        """Convert amount to lakhs format (₹XX.XXL)"""
        if amount == 0:
            return "₹0"
        lakhs = amount / Decimal("100000")
        return f"₹{lakhs.quantize(Decimal('0.01'))}L"

    @staticmethod
    def _in_thousands(amount: Decimal) -> str:
        """Convert amount to thousands format (₹XX.XXK)"""
        if amount == 0:
            return "₹0"
        thousands = amount / Decimal("1000")
        return f"₹{thousands.quantize(Decimal('0.01'))}K"

    @staticmethod
    def _format_amount_display(amount: Decimal) -> str:
        """Format amount as K or L based on value"""
        if amount >= Decimal("100000"):
            return APDashboardView._in_lakhs(amount)
        else:
            return APDashboardView._in_thousands(amount)

    def _calculate_dpo(self, total_payables, total_billed_last_90_days):
        """Calculate Days Payable Outstanding (DPO)"""
        if total_billed_last_90_days == 0:
            return 0
        # DPO = (Total Payables / Total Billed) * Number of Days
        dpo = (total_payables / total_billed_last_90_days) * 90
        return int(dpo)

    def _calculate_payment_efficiency(self, on_time_payments, total_payments):
        """Calculate Payment Efficiency percentage"""
        if total_payments == 0:
            return 100.0  # If no payments, assume 100% (no data)
        efficiency = (on_time_payments / total_payments) * 100
        return round(float(efficiency), 1)

    def _calculate_avg_days_delinquent(self, overdue_bills, today):
        """Calculate average days delinquent for overdue bills"""
        if not overdue_bills:
            return 0

        total_days = 0
        count = 0
        for bill in overdue_bills:
            if bill.due_date and bill.due_date < today:
                days_delinquent = (today - bill.due_date).days
                total_days += days_delinquent
                count += 1

        return int(total_days / count) if count > 0 else 0

    def _calculate_payment_trend_mom(self, company, today):
        """Calculate payment trend month over month"""
        current_month_start = today.replace(day=1)
        last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
        last_month_end = current_month_start - timedelta(days=1)

        # Current month payments
        current_month_payments = BillPayment.objects.filter(
            company=company,
            payment_date__gte=current_month_start,
            payment_date__lte=today,
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        # Last month payments
        last_month_payments = BillPayment.objects.filter(
            company=company,
            payment_date__gte=last_month_start,
            payment_date__lte=last_month_end,
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        # Calculate percentage change
        if last_month_payments > 0:
            mom_percentage = (
                (current_month_payments - last_month_payments) / last_month_payments
            ) * 100
        else:
            mom_percentage = (
                Decimal("0.00") if current_month_payments == 0 else Decimal("100.00")
            )

        return current_month_payments, last_month_payments, float(mom_percentage)

    def _calculate_vendor_concentration(self, outstanding_bills):
        """Calculate vendor concentration risk"""
        if not outstanding_bills:
            return 0.0, "Low"

        vendor_totals = defaultdict(Decimal)
        total_outstanding = Decimal("0")

        for bill in outstanding_bills:
            balance = bill.balance_amount
            vendor_key = (
                bill.vendor_id if bill.vendor else bill.vendor_name or "Unknown"
            )
            vendor_totals[vendor_key] += balance
            total_outstanding += balance

        if total_outstanding == 0:
            return 0.0, "Low"

        # Get top vendor percentage
        if vendor_totals:
            top_vendor_amount = max(vendor_totals.values())
            top_vendor_percentage = (top_vendor_amount / total_outstanding) * 100

            # Determine risk level
            if top_vendor_percentage >= 60:
                risk = "High"
            elif top_vendor_percentage >= 40:
                risk = "Medium"
            else:
                risk = "Low"

            return float(top_vendor_percentage), risk

        return 0.0, "Low"

    def _get_ap_health_status(
        self, overdue_percentage, avg_days_delinquent, dpo, dpo_target
    ):
        """Determine overall AP health status"""
        if overdue_percentage >= 50 or dpo > dpo_target * 2 or avg_days_delinquent > 60:
            return "Critical"
        elif (
            overdue_percentage >= 30
            or dpo > dpo_target * 1.5
            or avg_days_delinquent > 30
        ):
            return "Needs Attention"
        else:
            return "Healthy"

    def _calculate_ageing_buckets(self, bills, today):
        """Calculate ageing buckets based on overdue days"""
        buckets = {
            "current": Decimal("0"),  # Not overdue
            "overdue_1_30": Decimal("0"),  # 1-30 days overdue
            "overdue_31_60": Decimal("0"),  # 31-60 days overdue
            "overdue_61_90": Decimal("0"),  # 61-90 days overdue
            "overdue_90_plus": Decimal("0"),  # 90+ days overdue
        }

        for bill in bills:
            balance = bill.balance_amount
            if balance <= 0:
                continue

            if not bill.due_date:
                continue

            days_overdue = (today - bill.due_date).days if bill.due_date < today else 0

            if days_overdue <= 0:
                buckets["current"] += balance
            elif days_overdue <= 30:
                buckets["overdue_1_30"] += balance
            elif days_overdue <= 60:
                buckets["overdue_31_60"] += balance
            elif days_overdue <= 90:
                buckets["overdue_61_90"] += balance
            else:
                buckets["overdue_90_plus"] += balance

        return buckets

    def get(self, request, *args, **kwargs):
        """Calculate and return comprehensive AP dashboard data - all from Bill model"""
        # Use get_user_company to get company from logged-in user only
        company = get_user_company(request.user)
        if not company:
            return Response(
                {"error": "Company not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        today = timezone.now().date()
        last_90_days_start = today - timedelta(days=90)
        last_month_start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        last_month_end = today.replace(day=1) - timedelta(days=1)

        # Get all bills from Bill model (excluding cancelled)
        all_bills = (
            Bill.objects.filter(company=company)
            .exclude(status=BillsStatusChoices.CANCELLED)
            .select_related("vendor")
        )

        # Get outstanding bills (using total instead of amount)
        outstanding_bills = all_bills.filter(total__gt=F("paid_amount")).exclude(
            status=BillsStatusChoices.PAID
        )

        # Calculate Total Payables from Bill model
        total_payables = sum(bill.balance_amount for bill in outstanding_bills)

        # Calculate Overdue from Bill model
        overdue_bills = [bill for bill in outstanding_bills if bill.is_overdue]
        overdue_amount = sum(bill.balance_amount for bill in overdue_bills)
        overdue_percentage = (
            (overdue_amount / total_payables * 100) if total_payables > 0 else 0.0
        )

        # Calculate DPO from Bill model
        total_billed_last_90_days = all_bills.filter(
            bill_date__gte=last_90_days_start
        ).aggregate(total=Sum("total"))["total"] or Decimal("0.00")
        dpo = self._calculate_dpo(total_payables, total_billed_last_90_days)
        dpo_target = 45  # Standard target (as shown in image)

        # Calculate Payment Efficiency
        paid_bills = all_bills.filter(status=BillsStatusChoices.PAID)
        on_time_payments = 0
        total_payments_count = 0

        for bill in paid_bills:
            first_payment = bill.payments.order_by("payment_date").first()
            if first_payment:
                total_payments_count += 1
                payment_days = (first_payment.payment_date - bill.bill_date).days
                due_days = (bill.due_date - bill.bill_date).days if bill.due_date else 0
                if payment_days <= due_days:
                    on_time_payments += 1

        payment_efficiency = self._calculate_payment_efficiency(
            on_time_payments, total_payments_count
        )

        # Calculate Discounts Captured from BillPayment model
        all_payments = BillPayment.objects.filter(company=company)
        discounts_captured = sum(payment.discount_taken for payment in all_payments)

        # Calculate GST Summary from Bill model
        total_cgst = sum(bill.cgst_amount for bill in outstanding_bills)
        total_sgst = sum(bill.sgst_amount for bill in outstanding_bills)
        total_igst = sum(bill.igst_amount for bill in outstanding_bills)
        total_gst = total_cgst + total_sgst + total_igst

        # ITC Available = Total GST (pending to claim)
        itc_available = total_gst

        # Calculate TDS Summary from Bill model
        total_tds = sum(bill.tds_amount for bill in outstanding_bills)
        tds_by_section = defaultdict(Decimal)
        tds_bill_counts = defaultdict(int)

        for bill in outstanding_bills:
            if bill.tds_section and bill.tds_amount > 0:
                tds_by_section[bill.tds_section] += bill.tds_amount
                tds_bill_counts[bill.tds_section] += 1

        # Net Payable = Total Payables - TDS
        net_payable = total_payables - total_tds

        # Calculate Average Days Delinquent
        avg_days_delinquent = self._calculate_avg_days_delinquent(overdue_bills, today)

        # Calculate Payment Trend (MOM)
        current_month_payments, last_month_payments, mom_percentage = (
            self._calculate_payment_trend_mom(company, today)
        )

        # Calculate Vendor Concentration
        vendor_concentration_percentage, vendor_concentration_risk = (
            self._calculate_vendor_concentration(outstanding_bills)
        )

        # Calculate Cash Outflow Projections
        next_7_days = today + timedelta(days=7)
        next_30_days = today + timedelta(days=30)
        next_60_days = today + timedelta(days=60)
        next_90_days = today + timedelta(days=90)

        cash_outflow_7 = Decimal("0")
        cash_outflow_30 = Decimal("0")
        cash_outflow_60 = Decimal("0")
        cash_outflow_90 = Decimal("0")

        for bill in outstanding_bills:
            if not bill.due_date:
                continue
            balance = bill.balance_amount
            if bill.due_date <= next_7_days:
                cash_outflow_7 += balance
            if bill.due_date <= next_30_days:
                cash_outflow_30 += balance
            if bill.due_date <= next_60_days:
                cash_outflow_60 += balance
            if bill.due_date <= next_90_days:
                cash_outflow_90 += balance

        # Calculate Ageing Distribution
        current_amount = total_payables - overdue_amount

        # Calculate Ageing Breakdown (overdue buckets)
        ageing_buckets = self._calculate_ageing_buckets(outstanding_bills, today)

        # Get AP Health Status
        ap_health_status = self._get_ap_health_status(
            overdue_percentage, avg_days_delinquent, dpo, dpo_target
        )
        status_message = (
            f"{payment_efficiency}% on-time • {avg_days_delinquent} days avg delinquent"
        )

        # Generate Key Insights
        key_insights = []
        if len(overdue_bills) > 0:
            key_insights.append(
                {
                    "text": f"{len(overdue_bills)} overdue bills",
                    "type": "danger",
                    "color": "#EF4444",
                }
            )
        if dpo > dpo_target * 1.5:
            key_insights.append(
                {
                    "text": f"High DPO ({dpo} days)",
                    "type": "warning",
                    "color": "#F59E0B",
                }
            )
        if avg_days_delinquent > 30:
            key_insights.append(
                {
                    "text": f"High Delinquency ({avg_days_delinquent} days)",
                    "type": "warning",
                    "color": "#F59E0B",
                }
            )
        if itc_available > 0:
            key_insights.append(
                {
                    "text": f"ITC Pending: {self._format_amount_display(itc_available)}",
                    "type": "info",
                    "color": "#3B82F6",
                }
            )
        if discounts_captured > 0:
            key_insights.append(
                {
                    "text": f"{self._format_amount_display(discounts_captured)} discounts captured",
                    "type": "success",
                    "color": "#10B981",
                }
            )
        if payment_efficiency >= 90:
            key_insights.append(
                {
                    "text": "Excellent payment record",
                    "type": "success",
                    "color": "#10B981",
                }
            )

        # Calculate average bill value
        total_bills_count = all_bills.count()
        avg_bill_value = (
            total_payables / total_bills_count
            if total_bills_count > 0
            else Decimal("0")
        )

        # Prepare TDS by section details
        tds_by_section_list = []
        for section, amount in tds_by_section.items():
            tds_by_section_list.append(
                {
                    "section": section,
                    "amount": float(amount),
                    "amount_display": self._format_amount_display(amount),
                    "bill_count": tds_bill_counts.get(section, 0),
                }
            )

        response_data = {
            "kpis": {
                "total_payables": float(total_payables),
                "total_payables_display": self._format_amount_display(total_payables),
                "outstanding_balance_percentage": round(overdue_percentage, 1),
                "dpo": dpo,
                "dpo_target": dpo_target,
                "dpo_above_benchmark": round(
                    ((dpo - dpo_target) / dpo_target * 100) if dpo_target > 0 else 0, 1
                ),
                "payment_efficiency": payment_efficiency,
                "on_time_payment_rate": payment_efficiency,
                "overdue_amount": float(overdue_amount),
                "overdue_amount_display": self._format_amount_display(overdue_amount),
                "overdue_bills_count": len(overdue_bills),
                "overdue_percentage": round(overdue_percentage, 1),
                "total_gst_payable": float(total_gst),
                "total_gst_payable_display": self._format_amount_display(total_gst),
                "cgst_amount": float(total_cgst),
                "cgst_amount_display": self._format_amount_display(total_cgst),
                "sgst_amount": float(total_sgst),
                "sgst_amount_display": self._format_amount_display(total_sgst),
                "igst_amount": float(total_igst),
                "igst_amount_display": self._format_amount_display(total_igst),
                "itc_available": float(itc_available),
                "itc_available_display": self._format_amount_display(itc_available),
                "itc_pending": float(itc_available),
                "itc_pending_display": self._format_amount_display(itc_available),
                "tds_payable": float(total_tds),
                "tds_payable_display": self._format_amount_display(total_tds),
                "tds_total": float(total_tds),
                "tds_total_display": self._format_amount_display(total_tds),
                "net_payable": float(net_payable),
                "net_payable_display": self._format_amount_display(net_payable),
                "avg_days_delinquent": avg_days_delinquent,
                "payment_trend_mom": float(current_month_payments),
                "payment_trend_mom_display": self._format_amount_display(
                    current_month_payments
                ),
                "payment_trend_mom_percentage": round(mom_percentage, 1),
                "last_month_payments": float(last_month_payments),
                "last_month_payments_display": self._format_amount_display(
                    last_month_payments
                ),
                "discounts_captured": float(discounts_captured),
                "discounts_captured_display": self._format_amount_display(
                    discounts_captured
                ),
                "early_payment_savings_percentage": 0.0,
                "vendor_concentration": round(vendor_concentration_percentage, 0),
                "vendor_concentration_risk": vendor_concentration_risk,
                "total_bills": total_bills_count,
                "avg_bill_value": float(avg_bill_value),
                "avg_bill_value_display": self._format_amount_display(avg_bill_value),
            },
            "ap_health_status": {
                "status": ap_health_status,
                "on_time_payment_rate": payment_efficiency,
                "avg_days_delinquent": avg_days_delinquent,
                "status_message": status_message,
            },
            "gst_summary": {
                "total_gst": float(total_gst),
                "total_gst_display": self._format_amount_display(total_gst),
                "cgst": float(total_cgst),
                "cgst_display": self._format_amount_display(total_cgst),
                "sgst": float(total_sgst),
                "sgst_display": self._format_amount_display(total_sgst),
                "igst": float(total_igst),
                "igst_display": self._format_amount_display(total_igst),
                "itc_available": float(itc_available),
                "itc_available_display": self._format_amount_display(itc_available),
                "itc_status": "Pending to Claim" if itc_available > 0 else "No ITC",
            },
            "tds_summary": {
                "total_tds": float(total_tds),
                "total_tds_display": self._format_amount_display(total_tds),
                "tds_payable": float(total_tds),
                "tds_payable_display": self._format_amount_display(total_tds),
                "by_section": tds_by_section_list,
            },
            "cash_outflow_projections": {
                "this_week": float(cash_outflow_7),
                "this_week_display": self._format_amount_display(cash_outflow_7),
                "days_30": float(cash_outflow_30),
                "days_30_display": self._format_amount_display(cash_outflow_30),
                "days_60": float(cash_outflow_60),
                "days_60_display": self._format_amount_display(cash_outflow_60),
                "days_90": float(cash_outflow_90),
                "days_90_display": self._format_amount_display(cash_outflow_90),
            },
            "ageing_distribution": {
                "current": float(current_amount),
                "current_display": self._format_amount_display(current_amount),
                "overdue": float(overdue_amount),
                "overdue_display": self._format_amount_display(overdue_amount),
                "overdue_breakdown": {
                    "days_1_30": float(ageing_buckets["overdue_1_30"]),
                    "days_1_30_display": self._format_amount_display(
                        ageing_buckets["overdue_1_30"]
                    ),
                    "days_31_60": float(ageing_buckets["overdue_31_60"]),
                    "days_31_60_display": self._format_amount_display(
                        ageing_buckets["overdue_31_60"]
                    ),
                    "days_61_90": float(ageing_buckets["overdue_61_90"]),
                    "days_61_90_display": self._format_amount_display(
                        ageing_buckets["overdue_61_90"]
                    ),
                    "days_90_plus": float(ageing_buckets["overdue_90_plus"]),
                    "days_90_plus_display": self._format_amount_display(
                        ageing_buckets["overdue_90_plus"]
                    ),
                },
            },
            "key_insights": key_insights,
            "ageing_breakdown": {
                "current": float(ageing_buckets["current"]),
                "current_display": self._format_amount_display(
                    ageing_buckets["current"]
                ),
                "days_1_30": float(ageing_buckets["overdue_1_30"]),
                "days_1_30_display": self._format_amount_display(
                    ageing_buckets["overdue_1_30"]
                ),
                "days_31_60": float(ageing_buckets["overdue_31_60"]),
                "days_31_60_display": self._format_amount_display(
                    ageing_buckets["overdue_31_60"]
                ),
                "days_61_90": float(ageing_buckets["overdue_61_90"]),
                "days_61_90_display": self._format_amount_display(
                    ageing_buckets["overdue_61_90"]
                ),
                "days_90_plus": float(ageing_buckets["overdue_90_plus"]),
                "days_90_plus_display": self._format_amount_display(
                    ageing_buckets["overdue_90_plus"]
                ),
            },
        }

        serializer = APDashboardSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data, status=status.HTTP_200_OK)
