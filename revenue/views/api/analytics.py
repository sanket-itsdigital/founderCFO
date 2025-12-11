from decimal import Decimal
from datetime import datetime, timedelta
from collections import defaultdict
from calendar import monthrange

from django.db.models import Count, Sum, Avg, Q, F
from django.db.models.functions import (
    Coalesce,
    ExtractMonth,
    ExtractQuarter,
    ExtractYear,
)
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from revenue.models.invoice import Invoice
from sales.views.api.utils import get_company_from_request
from financial.enums import InvoicesStatusChoices


class TrendsView(APIView):
    """Unified Trends Analytics - Year-over-Year and Service KPIs"""

    permission_classes = [IsAuthenticated]

    def _in_lakhs(self, amount: Decimal) -> str:
        """Convert amount to lakhs format (₹XX.XXL)"""
        if amount == 0:
            return "₹0.00L"
        lakhs = amount / Decimal("100000")
        return f"₹{lakhs.quantize(Decimal('0.01'))}L"

    def get(self, request):
        """Get combined Trends data (Year-over-Year and Service KPIs)"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # ========== Year-over-Year Section ==========
        current_year = int(request.query_params.get("year", timezone.now().year))
        previous_year = current_year - 1

        today = timezone.now().date()
        current_month = today.month if today.year == current_year else 12

        # KPIs
        current_year_total = Invoice.objects.filter(
            company=company, invoice_date__year=current_year
        ).aggregate(total=Coalesce(Sum("total_amount"), Decimal("0.00")))[
            "total"
        ] or Decimal(
            "0.00"
        )

        previous_year_total = Invoice.objects.filter(
            company=company, invoice_date__year=previous_year
        ).aggregate(total=Coalesce(Sum("total_amount"), Decimal("0.00")))[
            "total"
        ] or Decimal(
            "0.00"
        )

        # YoY Growth
        yoy_growth = (
            ((current_year_total - previous_year_total) / previous_year_total * 100)
            if previous_year_total > 0
            else Decimal("0.00")
        )

        # YTD Growth (compare current year YTD with previous year YTD)
        ytd_current = Invoice.objects.filter(
            company=company, invoice_date__year=current_year, invoice_date__lte=today
        ).aggregate(total=Coalesce(Sum("total_amount"), Decimal("0.00")))[
            "total"
        ] or Decimal(
            "0.00"
        )

        ytd_previous = Invoice.objects.filter(
            company=company,
            invoice_date__year=previous_year,
            invoice_date__lte=today.replace(year=previous_year),
        ).aggregate(total=Coalesce(Sum("total_amount"), Decimal("0.00")))[
            "total"
        ] or Decimal(
            "0.00"
        )

        ytd_growth = (
            ((ytd_current - ytd_previous) / ytd_previous * 100)
            if ytd_previous > 0
            else Decimal("0.00")
        )

        # Monthly Revenue Data
        monthly_data = []
        for month in range(1, 13):
            current_month_revenue = Invoice.objects.filter(
                company=company,
                invoice_date__year=current_year,
                invoice_date__month=month,
            ).aggregate(total=Coalesce(Sum("total_amount"), Decimal("0.00")))[
                "total"
            ] or Decimal(
                "0.00"
            )

            previous_month_revenue = Invoice.objects.filter(
                company=company,
                invoice_date__year=previous_year,
                invoice_date__month=month,
            ).aggregate(total=Coalesce(Sum("total_amount"), Decimal("0.00")))[
                "total"
            ] or Decimal(
                "0.00"
            )

            monthly_data.append(
                {
                    "month": month,
                    "month_name": datetime(current_year, month, 1).strftime("%b"),
                    "current_year": float(current_month_revenue),
                    "current_year_display": self._in_lakhs(current_month_revenue),
                    "previous_year": float(previous_month_revenue),
                    "previous_year_display": self._in_lakhs(previous_month_revenue),
                }
            )

        # Quarterly Comparison
        quarterly_data = []
        for quarter in range(1, 5):
            quarter_start_month = (quarter - 1) * 3 + 1
            quarter_end_month = quarter * 3

            current_quarter_revenue = Invoice.objects.filter(
                company=company,
                invoice_date__year=current_year,
                invoice_date__month__gte=quarter_start_month,
                invoice_date__month__lte=quarter_end_month,
            ).aggregate(total=Coalesce(Sum("total_amount"), Decimal("0.00")))[
                "total"
            ] or Decimal(
                "0.00"
            )

            previous_quarter_revenue = Invoice.objects.filter(
                company=company,
                invoice_date__year=previous_year,
                invoice_date__month__gte=quarter_start_month,
                invoice_date__month__lte=quarter_end_month,
            ).aggregate(total=Coalesce(Sum("total_amount"), Decimal("0.00")))[
                "total"
            ] or Decimal(
                "0.00"
            )

            quarterly_data.append(
                {
                    "quarter": f"Q{quarter}",
                    "current_year": float(current_quarter_revenue),
                    "current_year_display": self._in_lakhs(current_quarter_revenue),
                    "previous_year": float(previous_quarter_revenue),
                    "previous_year_display": self._in_lakhs(previous_quarter_revenue),
                }
            )

        # Monthly Growth Analysis
        monthly_growth = []
        for month in range(1, 13):
            current_month_revenue = Invoice.objects.filter(
                company=company,
                invoice_date__year=current_year,
                invoice_date__month=month,
            ).aggregate(total=Coalesce(Sum("total_amount"), Decimal("0.00")))[
                "total"
            ] or Decimal(
                "0.00"
            )

            previous_month_revenue = Invoice.objects.filter(
                company=company,
                invoice_date__year=previous_year,
                invoice_date__month=month,
            ).aggregate(total=Coalesce(Sum("total_amount"), Decimal("0.00")))[
                "total"
            ] or Decimal(
                "0.00"
            )

            growth = (
                (
                    (current_month_revenue - previous_month_revenue)
                    / previous_month_revenue
                    * 100
                )
                if previous_month_revenue > 0
                else Decimal("0.00")
            )

            monthly_growth.append(
                {
                    "month": datetime(current_year, month, 1).strftime("%b"),
                    "current_year": float(current_month_revenue),
                    "current_year_display": (
                        f"₹{current_month_revenue:,.0f}"
                        if current_month_revenue > 0
                        else "₹0"
                    ),
                    "previous_year": float(previous_month_revenue),
                    "previous_year_display": (
                        f"₹{previous_month_revenue:,.0f}"
                        if previous_month_revenue > 0
                        else "₹0"
                    ),
                    "growth": float(growth),
                    "growth_display": f"{growth:.1f}%",
                }
            )

        # ========== Service KPIs Section ==========
        # Get employee count from query params or default
        employee_count = int(request.query_params.get("employee_count", 10))
        customer_tenure_years = int(
            request.query_params.get("customer_tenure_years", 2)
        )

        base_qs = Invoice.objects.filter(company=company)

        # Total Revenue
        total_revenue = base_qs.aggregate(
            total=Coalesce(Sum("total_amount"), Decimal("0.00"))
        )["total"] or Decimal("0.00")

        # Total Customers
        total_customers = base_qs.values("customer_name").distinct().count()

        # Revenue per Employee
        revenue_per_employee = (
            total_revenue / Decimal(str(employee_count))
            if employee_count > 0
            else Decimal("0.00")
        )

        # Avg Revenue per Customer
        avg_revenue_per_customer = (
            total_revenue / Decimal(str(total_customers))
            if total_customers > 0
            else Decimal("0.00")
        )

        # Estimated Customer LTV (Lifetime Value)
        # LTV = Avg Revenue per Customer * Estimated Lifetime (in years)
        estimated_ltv = avg_revenue_per_customer * Decimal(str(customer_tenure_years))

        # Revenue Run Rate (Annualized from current month)
        current_month = timezone.now().month
        current_year_for_run_rate = timezone.now().year
        current_month_revenue = base_qs.filter(
            invoice_date__year=current_year_for_run_rate,
            invoice_date__month=current_month,
        ).aggregate(total=Coalesce(Sum("total_amount"), Decimal("0.00")))[
            "total"
        ] or Decimal(
            "0.00"
        )

        revenue_run_rate = current_month_revenue * Decimal("12")

        # Recurring vs One-time Revenue
        recurring_revenue = base_qs.filter(is_recurring=True).aggregate(
            total=Coalesce(Sum("total_amount"), Decimal("0.00"))
        )["total"] or Decimal("0.00")

        one_time_revenue = base_qs.filter(
            Q(is_recurring=False) | Q(is_recurring__isnull=True)
        ).aggregate(total=Coalesce(Sum("total_amount"), Decimal("0.00")))[
            "total"
        ] or Decimal(
            "0.00"
        )

        recurring_percentage = (
            (recurring_revenue / total_revenue * 100)
            if total_revenue > 0
            else Decimal("0.00")
        )
        one_time_percentage = (
            (one_time_revenue / total_revenue * 100)
            if total_revenue > 0
            else Decimal("0.00")
        )

        # Revenue by Service Type
        service_revenue = (
            base_qs.filter(service_type__isnull=False)
            .exclude(service_type="")
            .values("service_type")
            .annotate(revenue=Coalesce(Sum("total_amount"), Decimal("0.00")))
            .order_by("-revenue")
        )

        service_type_data = []
        for item in service_revenue:
            service_type_data.append(
                {
                    "service_type": item["service_type"],
                    "revenue": float(item["revenue"]),
                    "revenue_display": self._in_lakhs(item["revenue"]),
                }
            )

        return Response(
            {
                "year_over_year": {
                    "kpis": {
                        "current_year_total": float(current_year_total),
                        "current_year_total_display": f"₹{current_year_total:,.0f}",
                        "previous_year_total": float(previous_year_total),
                        "previous_year_total_display": f"₹{previous_year_total:,.0f}",
                        "yoy_growth": float(yoy_growth),
                        "yoy_growth_display": f"{yoy_growth:.1f}%",
                        "ytd_growth": float(ytd_growth),
                        "ytd_growth_display": f"{ytd_growth:.1f}%",
                    },
                    "monthly_revenue": monthly_data,
                    "quarterly_comparison": quarterly_data,
                    "monthly_growth_analysis": monthly_growth,
                },
                "service_kpis": {
                    "kpis": {
                        "revenue_per_employee": float(revenue_per_employee),
                        "revenue_per_employee_display": f"₹{revenue_per_employee:,.0f}",
                        "avg_revenue_per_customer": float(avg_revenue_per_customer),
                        "avg_revenue_per_customer_display": f"₹{avg_revenue_per_customer:,.0f}",
                        "estimated_customer_ltv": float(estimated_ltv),
                        "estimated_customer_ltv_display": f"₹{estimated_ltv:,.0f}",
                        "revenue_run_rate": float(revenue_run_rate),
                        "revenue_run_rate_display": f"₹{revenue_run_rate:,.0f}",
                        "employee_count": employee_count,
                        "customer_tenure_years": customer_tenure_years,
                    },
                    "recurring_vs_one_time": {
                        "recurring_revenue": float(recurring_revenue),
                        "recurring_revenue_display": f"₹{recurring_revenue:,.0f}",
                        "recurring_percentage": float(recurring_percentage),
                        "one_time_revenue": float(one_time_revenue),
                        "one_time_revenue_display": f"₹{one_time_revenue:,.0f}",
                        "one_time_percentage": float(one_time_percentage),
                    },
                    "revenue_by_service_type": service_type_data,
                },
            },
            status=status.HTTP_200_OK,
        )


class CustomersView(APIView):
    """Unified Customer Analytics - Overview and Cohort Analysis"""

    permission_classes = [IsAuthenticated]

    def _in_lakhs(self, amount: Decimal) -> str:
        """Convert amount to lakhs format (₹XX.XXL)"""
        if amount == 0:
            return "₹0.00L"
        lakhs = amount / Decimal("100000")
        return f"₹{lakhs.quantize(Decimal('0.01'))}L"

    def get(self, request):
        """Get combined Customer Analytics data (Overview and Cohort Analysis)"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"}, status=status.HTTP_404_NOT_FOUND
            )

        base_qs = Invoice.objects.filter(company=company)

        # ========== Overview Section ==========
        # Total Customers
        total_customers = base_qs.values("customer_name").distinct().count()

        # Total Revenue
        total_revenue = base_qs.aggregate(
            total=Coalesce(Sum("total_amount"), Decimal("0.00"))
        )["total"] or Decimal("0.00")

        # Avg Revenue per Customer
        avg_revenue_per_customer = (
            total_revenue / Decimal(str(total_customers))
            if total_customers > 0
            else Decimal("0.00")
        )

        # Top 10 Customers by Revenue
        top_customers = (
            base_qs.values("customer_name")
            .annotate(
                revenue=Coalesce(Sum("total_amount"), Decimal("0.00")),
                invoices_count=Count("id"),
            )
            .order_by("-revenue")[:10]
        )

        top_customers_list = []
        for customer in top_customers:
            top_customers_list.append(
                {
                    "customer_name": customer["customer_name"],
                    "revenue": float(customer["revenue"]),
                    "revenue_display": self._in_lakhs(customer["revenue"]),
                    "invoices_count": customer["invoices_count"],
                }
            )

        # Top 5 Concentration
        top_5_revenue = sum(
            [Decimal(str(c["revenue"])) for c in top_customers_list[:5]]
        )
        top_5_concentration = (
            (top_5_revenue / total_revenue * 100)
            if total_revenue > 0
            else Decimal("0.00")
        )

        # Risk Level Assessment
        if top_5_concentration >= 80:
            risk_level = "High"
            risk_message = "High concentration risk - diversify customer base"
        elif top_5_concentration >= 60:
            risk_level = "Medium"
            risk_message = "Monitor closely"
        else:
            risk_level = "Low"
            risk_message = "Well diversified"

        # Customer Concentration Analysis (all customers with share)
        all_customers = (
            base_qs.values("customer_name")
            .annotate(
                revenue=Coalesce(Sum("total_amount"), Decimal("0.00")),
                invoices_count=Count("id"),
            )
            .order_by("-revenue")
        )

        concentration_analysis = []
        for customer in all_customers:
            share = (
                (customer["revenue"] / total_revenue * 100)
                if total_revenue > 0
                else Decimal("0.00")
            )
            concentration_analysis.append(
                {
                    "customer_name": customer["customer_name"],
                    "revenue": float(customer["revenue"]),
                    "revenue_display": self._in_lakhs(customer["revenue"]),
                    "invoices_count": customer["invoices_count"],
                    "share": float(share),
                    "share_display": f"{share:.1f}%",
                }
            )

        # ========== Cohort Analysis Section ==========
        # Get first purchase date for each customer (more efficient)
        customer_first_purchases = {}
        all_invoices = list(base_qs.order_by("invoice_date").all())

        for invoice in all_invoices:
            customer_name = invoice.customer_name
            if customer_name not in customer_first_purchases:
                customer_first_purchases[customer_name] = invoice.invoice_date

        # Group customers by cohort (first purchase month)
        cohorts = defaultdict(
            lambda: {
                "customers": set(),
                "invoices": [],
                "total_revenue": Decimal("0.00"),
            }
        )

        for invoice in all_invoices:
            customer_name = invoice.customer_name
            first_purchase_date = customer_first_purchases.get(customer_name)
            if first_purchase_date:
                cohort_key = first_purchase_date.strftime("%Y-%m")
                cohorts[cohort_key]["customers"].add(customer_name)
                cohorts[cohort_key]["invoices"].append(invoice)
                cohorts[cohort_key]["total_revenue"] += invoice.total_amount

        # Calculate cohort metrics
        cohort_performance = []
        total_cohort_customers = 0
        repeat_customers = 0
        total_ltv = Decimal("0.00")

        for cohort_key in sorted(cohorts.keys()):
            cohort = cohorts[cohort_key]
            customer_count = len(cohort["customers"])
            cohort_total_revenue = cohort["total_revenue"]
            avg_revenue = (
                cohort_total_revenue / Decimal(str(customer_count))
                if customer_count > 0
                else Decimal("0.00")
            )

            # Calculate repeat rate (customers with more than 1 invoice)
            customer_invoice_counts = defaultdict(int)
            for invoice in cohort["invoices"]:
                customer_invoice_counts[invoice.customer_name] += 1

            repeat_count = sum(
                1 for count in customer_invoice_counts.values() if count > 1
            )
            repeat_rate = (
                (Decimal(str(repeat_count)) / Decimal(str(customer_count)) * 100)
                if customer_count > 0
                else Decimal("0.00")
            )

            cohort_date = datetime.strptime(cohort_key, "%Y-%m")
            cohort_performance.append(
                {
                    "cohort": cohort_date.strftime("%b %y"),
                    "cohort_key": cohort_key,
                    "customers": customer_count,
                    "total_revenue": float(cohort_total_revenue),
                    "total_revenue_display": f"₹{cohort_total_revenue:,.0f}",
                    "avg_revenue": float(avg_revenue),
                    "avg_revenue_display": f"₹{avg_revenue:,.0f}",
                    "repeat_rate": float(repeat_rate),
                    "repeat_rate_display": f"{repeat_rate:.0f}%",
                }
            )

            total_cohort_customers += customer_count
            repeat_customers += repeat_count
            total_ltv += avg_revenue

        # Overall metrics
        overall_repeat_rate = (
            (
                Decimal(str(repeat_customers))
                / Decimal(str(total_cohort_customers))
                * 100
            )
            if total_cohort_customers > 0
            else Decimal("0.00")
        )
        avg_ltv = (
            total_ltv / Decimal(str(len(cohort_performance)))
            if len(cohort_performance) > 0
            else Decimal("0.00")
        )
        avg_cohort_size = (
            total_cohort_customers / len(cohort_performance)
            if len(cohort_performance) > 0
            else 0
        )

        # Monthly revenue by cohort
        monthly_cohort_revenue = defaultdict(lambda: defaultdict(Decimal))
        for cohort_key in cohorts.keys():
            for invoice in cohorts[cohort_key]["invoices"]:
                month_key = invoice.invoice_date.strftime("%Y-%m")
                monthly_cohort_revenue[cohort_key][month_key] += invoice.total_amount

        # New vs Repeat Customer Revenue by Month
        new_vs_repeat = defaultdict(
            lambda: {
                "new": Decimal("0.00"),
                "repeat": Decimal("0.00"),
            }
        )

        for invoice in all_invoices:
            month_key = invoice.invoice_date.strftime("%Y-%m")
            customer_first = (
                base_qs.filter(customer_name=invoice.customer_name)
                .order_by("invoice_date")
                .first()
            )

            if customer_first:
                first_month = customer_first.invoice_date.strftime("%Y-%m")
                if month_key == first_month:
                    new_vs_repeat[month_key]["new"] += invoice.total_amount
                else:
                    new_vs_repeat[month_key]["repeat"] += invoice.total_amount

        monthly_new_repeat = []
        for month_key in sorted(new_vs_repeat.keys()):
            data = new_vs_repeat[month_key]
            monthly_new_repeat.append(
                {
                    "month": month_key,
                    "new_customers": float(data["new"]),
                    "new_customers_display": self._in_lakhs(data["new"]),
                    "repeat_customers": float(data["repeat"]),
                    "repeat_customers_display": self._in_lakhs(data["repeat"]),
                }
            )

        return Response(
            {
                "overview": {
                    "kpis": {
                        "total_customers": total_customers,
                        "avg_revenue_per_customer": float(avg_revenue_per_customer),
                        "avg_revenue_per_customer_display": self._in_lakhs(
                            avg_revenue_per_customer
                        ),
                        "top_5_concentration": float(top_5_concentration),
                        "top_5_concentration_display": f"{top_5_concentration:.1f}%",
                        "risk_level": risk_level,
                        "risk_message": risk_message,
                    },
                    "top_customers": top_customers_list,
                    "concentration_analysis": concentration_analysis,
                },
                "cohort_analysis": {
                    "summary": {
                        "total_customers": total_cohort_customers,
                        "repeat_customers": repeat_customers,
                        "repeat_rate": float(overall_repeat_rate),
                        "repeat_rate_display": f"{overall_repeat_rate:.1f}%",
                        "avg_ltv": float(avg_ltv),
                        "avg_ltv_display": f"₹{avg_ltv:,.0f}",
                        "avg_cohort_size": avg_cohort_size,
                    },
                    "cohort_performance": cohort_performance,
                    "monthly_cohort_revenue": {
                        cohort_key: {
                            month: float(amount) for month, amount in months.items()
                        }
                        for cohort_key, months in monthly_cohort_revenue.items()
                    },
                    "new_vs_repeat_revenue": monthly_new_repeat,
                },
            },
            status=status.HTTP_200_OK,
        )


class SalespersonView(APIView):
    """Unified Salesperson Analytics - Overview and Performance"""

    permission_classes = [IsAuthenticated]

    def _in_lakhs(self, amount: Decimal) -> str:
        """Convert amount to lakhs format (₹XX.XXL)"""
        if amount == 0:
            return "₹0.00L"
        lakhs = amount / Decimal("100000")
        return f"₹{lakhs.quantize(Decimal('0.01'))}L"

    def get(self, request):
        """Get combined Salesperson Analytics data (Overview and Performance)"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"}, status=status.HTTP_404_NOT_FOUND
            )

        base_qs = Invoice.objects.filter(
            company=company, salesperson__isnull=False
        ).exclude(salesperson="")

        # ========== Overview Section ==========
        # Team Size
        team_size = base_qs.values("salesperson").distinct().count()

        # Total Revenue
        total_revenue = base_qs.aggregate(
            total=Coalesce(Sum("total_amount"), Decimal("0.00"))
        )["total"] or Decimal("0.00")

        # Avg per Person
        avg_per_person = (
            total_revenue / Decimal(str(team_size))
            if team_size > 0
            else Decimal("0.00")
        )

        # Top Performer
        top_performer_data = (
            base_qs.values("salesperson")
            .annotate(
                revenue=Coalesce(Sum("total_amount"), Decimal("0.00")),
            )
            .order_by("-revenue")
            .first()
        )

        top_performer = (
            {
                "name": (
                    top_performer_data["salesperson"] if top_performer_data else None
                ),
                "revenue": (
                    float(top_performer_data["revenue"]) if top_performer_data else 0.0
                ),
                "revenue_display": (
                    self._in_lakhs(top_performer_data["revenue"])
                    if top_performer_data
                    else "₹0.00L"
                ),
            }
            if top_performer_data
            else None
        )

        # Customers per Rep
        total_customers = base_qs.values("customer_name").distinct().count()
        customers_per_rep = total_customers / team_size if team_size > 0 else 0

        # Performance Leaderboard
        leaderboard = (
            base_qs.values("salesperson")
            .annotate(
                revenue=Coalesce(Sum("total_amount"), Decimal("0.00")),
                deals=Count("id"),
                customers=Count("customer_name", distinct=True),
            )
            .order_by("-revenue")
        )

        leaderboard_list = []
        for person in leaderboard:
            leaderboard_list.append(
                {
                    "salesperson": person["salesperson"],
                    "revenue": float(person["revenue"]),
                    "revenue_display": self._in_lakhs(person["revenue"]),
                    "deals": person["deals"],
                    "customers": person["customers"],
                    "quota_attainment": 0.0,  # Placeholder - would need quota data
                }
            )

        # Revenue by Department
        department_revenue = (
            base_qs.values("department")
            .annotate(
                revenue=Coalesce(Sum("total_amount"), Decimal("0.00")),
            )
            .order_by("-revenue")
        )

        department_data = []
        for dept in department_revenue:
            dept_name = dept["department"] or "Unknown"
            share = (
                (dept["revenue"] / total_revenue * 100)
                if total_revenue > 0
                else Decimal("0.00")
            )
            department_data.append(
                {
                    "department": dept_name,
                    "revenue": float(dept["revenue"]),
                    "revenue_display": self._in_lakhs(dept["revenue"]),
                    "share": float(share),
                    "share_display": f"{share:.1f}%",
                }
            )

        # ========== Performance Section ==========
        # Get top 5 salespersons
        top_5 = (
            base_qs.values("salesperson")
            .annotate(
                revenue=Coalesce(Sum("total_amount"), Decimal("0.00")),
            )
            .order_by("-revenue")[:5]
        )

        top_5_names = [person["salesperson"] for person in top_5]

        # Monthly Revenue Trend for Top 5
        current_year = timezone.now().year
        monthly_trend = defaultdict(lambda: defaultdict(Decimal))

        for person_name in top_5_names:
            person_invoices = base_qs.filter(salesperson=person_name)
            for month in range(1, 13):
                month_revenue = person_invoices.filter(
                    invoice_date__year=current_year, invoice_date__month=month
                ).aggregate(total=Coalesce(Sum("total_amount"), Decimal("0.00")))[
                    "total"
                ] or Decimal(
                    "0.00"
                )
                monthly_trend[person_name][month] = month_revenue

        monthly_trend_data = []
        for month in range(1, 13):
            month_data = {
                "month": datetime(current_year, month, 1).strftime("%b"),
                "month_num": month,
            }
            for person_name in top_5_names:
                month_data[person_name] = float(monthly_trend[person_name][month])
                month_data[f"{person_name}_display"] = self._in_lakhs(
                    monthly_trend[person_name][month]
                )
            monthly_trend_data.append(month_data)

        # Revenue by Salesperson (bar chart data)
        revenue_by_salesperson = (
            base_qs.values("salesperson")
            .annotate(
                revenue=Coalesce(Sum("total_amount"), Decimal("0.00")),
                invoices_count=Count("id"),
                customers_count=Count("customer_name", distinct=True),
            )
            .order_by("-revenue")
        )

        salesperson_list = []
        for person in revenue_by_salesperson:
            salesperson_list.append(
                {
                    "salesperson": person["salesperson"],
                    "revenue": float(person["revenue"]),
                    "revenue_display": self._in_lakhs(person["revenue"]),
                    "invoices_count": person["invoices_count"],
                    "customers_count": person["customers_count"],
                }
            )

        # Detailed Performance Table
        detailed_performance = (
            base_qs.values("salesperson")
            .annotate(
                revenue=Coalesce(Sum("total_amount"), Decimal("0.00")),
                invoices_count=Count("id"),
                customers_count=Count("customer_name", distinct=True),
            )
            .order_by("-revenue")
        )

        performance_table = []
        for person in detailed_performance:
            performance_table.append(
                {
                    "salesperson": person["salesperson"],
                    "revenue": float(person["revenue"]),
                    "revenue_display": self._in_lakhs(person["revenue"]),
                    "quota": 0.0,  # Placeholder
                    "quota_display": "₹0.00L",
                    "attainment": 0.0,
                    "attainment_display": "0.0%",
                }
            )

        return Response(
            {
                "overview": {
                    "kpis": {
                        "team_size": team_size,
                        "total_revenue": float(total_revenue),
                        "total_revenue_display": self._in_lakhs(total_revenue),
                        "top_performer": top_performer,
                        "avg_per_person": float(avg_per_person),
                        "avg_per_person_display": self._in_lakhs(avg_per_person),
                        "quota_attainment": 0.0,  # Placeholder
                        "customers_per_rep": customers_per_rep,
                    },
                    "leaderboard": leaderboard_list,
                    "revenue_by_department": department_data,
                },
                "performance": {
                    "monthly_trend": monthly_trend_data,
                    "top_5_salespersons": top_5_names,
                    "revenue_by_salesperson": salesperson_list,
                    "detailed_performance": performance_table,
                },
            },
            status=status.HTTP_200_OK,
        )


class ProductsView(APIView):
    """Unified Products Analytics - Overview and Details"""

    permission_classes = [IsAuthenticated]

    def _in_lakhs(self, amount: Decimal) -> str:
        """Convert amount to lakhs format (₹XX.XXL)"""
        if amount == 0:
            return "₹0.00L"
        lakhs = amount / Decimal("100000")
        return f"₹{lakhs.quantize(Decimal('0.01'))}L"

    def _in_thousands(self, amount: Decimal) -> str:
        """Convert amount to thousands format (₹XX.XXK)"""
        if amount == 0:
            return "₹0.00K"
        thousands = amount / Decimal("1000")
        return f"₹{thousands.quantize(Decimal('0.01'))}K"

    def get(self, request):
        """Get combined Products Overview and Details data"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"}, status=status.HTTP_404_NOT_FOUND
            )

        base_qs = Invoice.objects.filter(company=company)

        # ===== Overview Section =====
        total_products = base_qs.values("product_name").distinct().count()
        total_revenue = base_qs.aggregate(
            total=Coalesce(Sum("total_amount"), Decimal("0.00"))
        )["total"] or Decimal("0.00")

        avg_revenue_per_product = (
            total_revenue / Decimal(str(total_products))
            if total_products > 0
            else Decimal("0.00")
        )

        top_product = (
            base_qs.values("product_name")
            .annotate(revenue=Coalesce(Sum("total_amount"), Decimal("0.00")))
            .order_by("-revenue")
            .first()
        )
        top_product_share = (
            (top_product["revenue"] / total_revenue * 100)
            if top_product and total_revenue > 0
            else Decimal("0.00")
        )

        product_revenue = (
            base_qs.values("product_name")
            .annotate(
                revenue=Coalesce(Sum("total_amount"), Decimal("0.00")),
                quantity=Coalesce(Sum("quantity"), Decimal("0.00")),
                invoices_count=Count("id"),
            )
            .order_by("-revenue")
        )

        product_overview = []
        for product in product_revenue:
            share = (
                (product["revenue"] / total_revenue * 100)
                if total_revenue > 0
                else Decimal("0.00")
            )
            product_overview.append(
                {
                    "product_name": product["product_name"],
                    "revenue": float(product["revenue"]),
                    "revenue_display": self._in_lakhs(product["revenue"]),
                    "quantity": float(product["quantity"]),
                    "invoices_count": product["invoices_count"],
                    "share": float(share),
                    "share_display": f"{share:.1f}%",
                }
            )

        service_revenue = (
            base_qs.filter(service_type__isnull=False)
            .exclude(service_type="")
            .values("service_type")
            .annotate(revenue=Coalesce(Sum("total_amount"), Decimal("0.00")))
            .order_by("-revenue")
        )
        service_data = []
        for service in service_revenue:
            service_data.append(
                {
                    "service_type": service["service_type"],
                    "revenue": float(service["revenue"]),
                    "revenue_display": self._in_lakhs(service["revenue"]),
                }
            )

        # ===== Details Section =====
        product_details = (
            base_qs.values("product_name")
            .annotate(
                revenue=Coalesce(Sum("total_amount"), Decimal("0.00")),
                quantity_sold=Coalesce(Sum("quantity"), Decimal("0.00")),
                invoices_count=Count("id"),
            )
            .order_by("-revenue")
        )

        details_list = []
        for product in product_details:
            share = (
                (product["revenue"] / total_revenue * 100)
                if total_revenue > 0
                else Decimal("0.00")
            )

            if product["revenue"] >= Decimal("100000"):
                revenue_display = self._in_lakhs(product["revenue"])
            else:
                revenue_display = self._in_thousands(product["revenue"])

            details_list.append(
                {
                    "product_name": product["product_name"],
                    "revenue": float(product["revenue"]),
                    "revenue_display": revenue_display,
                    "quantity_sold": float(product["quantity_sold"]),
                    "invoices_count": product["invoices_count"],
                    "share": float(share),
                    "share_display": f"{share:.1f}%",
                }
            )

        return Response(
            {
                "overview": {
                    "kpis": {
                        "total_products": total_products,
                        "avg_revenue_per_product": float(avg_revenue_per_product),
                        "avg_revenue_per_product_display": self._in_lakhs(
                            avg_revenue_per_product
                        ),
                        "top_product_share": float(top_product_share),
                        "top_product_share_display": f"{top_product_share:.1f}%",
                    },
                    "revenue_by_product": product_overview,
                    "revenue_by_service_type": service_data,
                },
                "details": {
                    "product_revenue_details": details_list,
                },
            },
            status=status.HTTP_200_OK,
        )


class BranchView(APIView):
    """Unified Branch Analytics - Overview and Performance"""

    permission_classes = [IsAuthenticated]

    def _in_lakhs(self, amount: Decimal) -> str:
        """Convert amount to lakhs format (₹XX.XXL)"""
        if amount == 0:
            return "₹0.00L"
        lakhs = amount / Decimal("100000")
        return f"₹{lakhs.quantize(Decimal('0.01'))}L"

    def get(self, request):
        """Get combined Branch Overview and Performance data"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"}, status=status.HTTP_404_NOT_FOUND
            )

        base_qs = Invoice.objects.filter(company=company)
        base_qs_with_branch = base_qs.exclude(Q(branch__isnull=True) | Q(branch=""))

        # ========== Overview Section ==========
        # Total Branches
        total_branches = (
            base_qs.values("branch")
            .distinct()
            .exclude(Q(branch__isnull=True) | Q(branch=""))
            .count()
        )

        # Total Revenue
        total_revenue = base_qs.aggregate(
            total=Coalesce(Sum("total_amount"), Decimal("0.00"))
        )["total"] or Decimal("0.00")

        # Avg per Branch
        avg_per_branch = (
            total_revenue / Decimal(str(total_branches))
            if total_branches > 0
            else Decimal("0.00")
        )

        # Top Branch
        top_branch_data = (
            base_qs.values("branch")
            .annotate(
                revenue=Coalesce(Sum("total_amount"), Decimal("0.00")),
            )
            .exclude(Q(branch__isnull=True) | Q(branch=""))
            .order_by("-revenue")
            .first()
        )

        top_branch = (
            {
                "name": top_branch_data["branch"] if top_branch_data else None,
                "revenue": (
                    float(top_branch_data["revenue"]) if top_branch_data else 0.0
                ),
                "revenue_display": (
                    self._in_lakhs(top_branch_data["revenue"])
                    if top_branch_data
                    else "₹0.00L"
                ),
            }
            if top_branch_data
            else None
        )

        # Total Customers
        total_customers = base_qs.values("customer_name").distinct().count()

        # Sales Team Size
        sales_team_size = (
            base_qs.values("salesperson")
            .distinct()
            .exclude(Q(salesperson__isnull=True) | Q(salesperson=""))
            .count()
        )

        # Branch Performance Ranking
        branch_performance = (
            base_qs.values("branch")
            .annotate(
                revenue=Coalesce(Sum("total_amount"), Decimal("0.00")),
                invoices_count=Count("id"),
                customers_count=Count("customer_name", distinct=True),
                reps_count=Count("salesperson", distinct=True),
            )
            .exclude(Q(branch__isnull=True) | Q(branch=""))
            .order_by("-revenue")
        )

        branch_list = []
        for branch in branch_performance:
            share = (
                (branch["revenue"] / total_revenue * 100)
                if total_revenue > 0
                else Decimal("0.00")
            )
            branch_list.append(
                {
                    "branch": branch["branch"],
                    "revenue": float(branch["revenue"]),
                    "revenue_display": self._in_lakhs(branch["revenue"]),
                    "invoices_count": branch["invoices_count"],
                    "customers_count": branch["customers_count"],
                    "reps_count": branch["reps_count"],
                    "share": float(share),
                    "share_display": f"{share:.1f}%",
                }
            )

        # ========== Performance Section ==========
        # Monthly Revenue Trend by Branch
        branches = base_qs_with_branch.values("branch").distinct()
        monthly_trend = defaultdict(lambda: defaultdict(Decimal))
        current_year = timezone.now().year

        for branch_data in branches:
            branch_name = branch_data["branch"]
            branch_invoices = base_qs_with_branch.filter(branch=branch_name)

            for month in range(1, 13):
                month_revenue = branch_invoices.filter(
                    invoice_date__year=current_year, invoice_date__month=month
                ).aggregate(total=Coalesce(Sum("total_amount"), Decimal("0.00")))[
                    "total"
                ] or Decimal(
                    "0.00"
                )
                monthly_trend[branch_name][month] = month_revenue

        monthly_trend_data = []
        for month in range(1, 13):
            month_data = {
                "month": datetime(current_year, month, 1).strftime("%b %Y"),
                "month_num": month,
            }
            for branch_data in branches:
                branch_name = branch_data["branch"]
                month_data[branch_name] = float(monthly_trend[branch_name][month])
                month_data[f"{branch_name}_display"] = self._in_lakhs(
                    monthly_trend[branch_name][month]
                )
            monthly_trend_data.append(month_data)

        # Revenue by Branch (bar chart)
        branch_revenue = (
            base_qs_with_branch.values("branch")
            .annotate(
                revenue=Coalesce(Sum("total_amount"), Decimal("0.00")),
                invoices_count=Count("id"),
            )
            .order_by("-revenue")
        )

        branch_revenue_list = []
        for branch in branch_revenue:
            share = (
                (branch["revenue"] / total_revenue * 100)
                if total_revenue > 0
                else Decimal("0.00")
            )
            branch_revenue_list.append(
                {
                    "branch": branch["branch"],
                    "revenue": float(branch["revenue"]),
                    "revenue_display": self._in_lakhs(branch["revenue"]),
                    "invoices_count": branch["invoices_count"],
                    "share": float(share),
                    "share_display": f"{share:.1f}%",
                }
            )

        # Branch Details Table
        branch_details = (
            base_qs_with_branch.values("branch")
            .annotate(
                revenue=Coalesce(Sum("total_amount"), Decimal("0.00")),
                invoices_count=Count("id"),
            )
            .order_by("-revenue")
        )

        details_list = []
        for branch in branch_details:
            share = (
                (branch["revenue"] / total_revenue * 100)
                if total_revenue > 0
                else Decimal("0.00")
            )

            # Get branch GSTIN (first non-empty value for this branch)
            branch_gstin_data = (
                base_qs_with_branch.filter(branch=branch["branch"])
                .exclude(Q(branch_gstin__isnull=True) | Q(branch_gstin=""))
                .values("branch_gstin")
                .first()
            )

            branch_gstin = (
                branch_gstin_data["branch_gstin"] if branch_gstin_data else None
            )

            details_list.append(
                {
                    "branch": branch["branch"],
                    "branch_gstin": branch_gstin,
                    "revenue": float(branch["revenue"]),
                    "revenue_display": self._in_lakhs(branch["revenue"]),
                    "invoices_count": branch["invoices_count"],
                    "share": float(share),
                    "share_display": f"{share:.1f}%",
                }
            )

        return Response(
            {
                "overview": {
                    "kpis": {
                        "branches": total_branches,
                        "total_revenue": float(total_revenue),
                        "total_revenue_display": self._in_lakhs(total_revenue),
                        "top_branch": top_branch,
                        "avg_per_branch": float(avg_per_branch),
                        "avg_per_branch_display": self._in_lakhs(avg_per_branch),
                        "customers": total_customers,
                        "sales_team": sales_team_size,
                    },
                    "branch_performance": branch_list,
                    "revenue_distribution": branch_list,  # Same data for donut chart
                },
                "performance": {
                    "monthly_trend": monthly_trend_data,
                    "revenue_by_branch": branch_revenue_list,
                    "branch_details": details_list,
                },
            },
            status=status.HTTP_200_OK,
        )


class GeographicView(APIView):
    """Unified Geographic Analytics - Overview and Details"""

    permission_classes = [IsAuthenticated]

    def _in_lakhs(self, amount: Decimal) -> str:
        """Convert amount to lakhs format (₹XX.XXL)"""
        if amount == 0:
            return "₹0.00L"
        lakhs = amount / Decimal("100000")
        return f"₹{lakhs.quantize(Decimal('0.01'))}L"

    def get(self, request):
        """Get combined Geographic Overview and Details data"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"}, status=status.HTTP_404_NOT_FOUND
            )

        base_qs = Invoice.objects.filter(company=company)

        # ========== Overview Section ==========
        # Total Regions
        regions_qs = base_qs.exclude(Q(region__isnull=True) | Q(region=""))

        total_regions = regions_qs.values("region").distinct().count()

        # Total Revenue
        total_revenue = base_qs.aggregate(
            total=Coalesce(Sum("total_amount"), Decimal("0.00"))
        )["total"] or Decimal("0.00")

        # Total Customers
        total_customers = base_qs.values("customer_name").distinct().count()

        # Regional Revenue
        regional_data = (
            base_qs.values("region")
            .annotate(
                revenue=Coalesce(Sum("total_amount"), Decimal("0.00")),
                invoices_count=Count("id"),
                customers_count=Count("customer_name", distinct=True),
            )
            .exclude(Q(region__isnull=True) | Q(region=""))
            .order_by("-revenue")
        )

        region_list = []
        for region in regional_data:
            region_name = region.get("region") or "Unknown"
            share = (
                (region["revenue"] / total_revenue * 100)
                if total_revenue > 0
                else Decimal("0.00")
            )
            region_list.append(
                {
                    "region": region_name,
                    "revenue": float(region["revenue"]),
                    "revenue_display": self._in_lakhs(region["revenue"]),
                    "invoices_count": region["invoices_count"],
                    "customers_count": region["customers_count"],
                    "share": float(share),
                    "share_display": f"{share:.1f}%",
                }
            )

        # Top Region
        top_region = region_list[0] if region_list else None

        # ========== Details Section ==========
        # Regional Performance Details (same data but with different formatting)
        details_list = []
        for region in regional_data:
            region_name = region.get("region") or "Unknown"
            share = (
                (region["revenue"] / total_revenue * 100)
                if total_revenue > 0
                else Decimal("0.00")
            )
            details_list.append(
                {
                    "region": region_name,
                    "revenue": float(region["revenue"]),
                    "revenue_display": f"₹{region['revenue']:,.0f}",
                    "invoices_count": region["invoices_count"],
                    "customers_count": region["customers_count"],
                    "share": float(share),
                    "share_display": f"{share:.1f}%",
                }
            )

        return Response(
            {
                "overview": {
                    "kpis": {
                        "regions": total_regions,
                        "total_revenue": float(total_revenue),
                        "total_revenue_display": f"₹{total_revenue:,.0f}",
                        "total_customers": total_customers,
                        "top_region": top_region["region"] if top_region else None,
                    },
                    "revenue_distribution": region_list,
                    "top_regions": region_list[:5],  # Top 5 for bar chart
                },
                "details": {
                    "regional_performance_details": details_list,
                },
            },
            status=status.HTTP_200_OK,
        )


class GSTOverviewView(APIView):
    """GST Overview Analytics - Combined GST Components, B2B/B2C Breakdown, and HSN/SAC Summary"""

    permission_classes = [IsAuthenticated]

    def _in_lakhs(self, amount: Decimal) -> str:
        """Convert amount to lakhs format (₹XX.XXL)"""
        if amount == 0:
            return "₹0.00L"
        lakhs = amount / Decimal("100000")
        return f"₹{lakhs.quantize(Decimal('0.01'))}L"

    def _in_thousands(self, amount: Decimal) -> str:
        """Convert amount to thousands format (₹XX.XXK)"""
        if amount == 0:
            return "₹0.00K"
        thousands = amount / Decimal("1000")
        return f"₹{thousands.quantize(Decimal('0.01'))}K"

    def _format_amount(self, amount: Decimal) -> str:
        """Format amount as K or L based on value"""
        if amount >= Decimal("100000"):
            return self._in_lakhs(amount)
        else:
            return self._in_thousands(amount)

    def get(self, request):
        """Get GST Overview data including components, B2B/B2C breakdown, and HSN/SAC summary"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"}, status=status.HTTP_404_NOT_FOUND
            )

        base_qs = Invoice.objects.filter(company=company)

        # GST Components
        gst_summary = base_qs.aggregate(
            total_taxable_value=Coalesce(Sum("taxable_value"), Decimal("0.00")),
            total_cgst=Coalesce(Sum("cgst_amount"), Decimal("0.00")),
            total_sgst=Coalesce(Sum("sgst_amount"), Decimal("0.00")),
            total_igst=Coalesce(Sum("igst_amount"), Decimal("0.00")),
        )

        taxable_value = gst_summary["total_taxable_value"] or Decimal("0.00")
        cgst = gst_summary["total_cgst"] or Decimal("0.00")
        sgst = gst_summary["total_sgst"] or Decimal("0.00")
        igst = gst_summary["total_igst"] or Decimal("0.00")
        cess = Decimal("0.00")  # Cess field not in model, defaulting to 0

        # Total GST (Output Tax Payable) = CGST + SGST + IGST + Cess
        total_gst = cgst + sgst + igst + cess

        # B2B vs B2C Breakdown
        # B2B: Invoices with customer_gstin
        b2b_invoices = base_qs.exclude(
            Q(customer_gstin__isnull=True) | Q(customer_gstin="")
        )
        b2b_count = b2b_invoices.count()
        b2b_total = b2b_invoices.aggregate(
            total=Coalesce(Sum("total_amount"), Decimal("0.00"))
        )["total"] or Decimal("0.00")

        # B2C: Invoices without customer_gstin
        b2c_invoices = base_qs.filter(
            Q(customer_gstin__isnull=True) | Q(customer_gstin="")
        )
        b2c_count = b2c_invoices.count()
        b2c_total = b2c_invoices.aggregate(
            total=Coalesce(Sum("total_amount"), Decimal("0.00"))
        )["total"] or Decimal("0.00")

        # Total invoices
        total_invoices = b2b_count + b2c_count
        total_revenue = b2b_total + b2c_total

        # Calculate percentages
        b2b_percentage = (
            (b2b_count / total_invoices * 100)
            if total_invoices > 0
            else Decimal("0.00")
        )
        b2c_percentage = (
            (b2c_count / total_invoices * 100)
            if total_invoices > 0
            else Decimal("0.00")
        )

        # HSN/SAC Summary
        hsn_qs = base_qs.exclude(Q(hsn_sac_code__isnull=True) | Q(hsn_sac_code=""))

        hsn_summary = (
            hsn_qs.values("hsn_sac_code")
            .annotate(
                invoices_count=Count("id"),
                taxable_value=Coalesce(Sum("taxable_value"), Decimal("0.00")),
                cgst=Coalesce(Sum("cgst_amount"), Decimal("0.00")),
                sgst=Coalesce(Sum("sgst_amount"), Decimal("0.00")),
                igst=Coalesce(Sum("igst_amount"), Decimal("0.00")),
            )
            .order_by("-taxable_value")
        )

        hsn_list = []
        hsn_total_invoices = 0
        hsn_total_taxable_value = Decimal("0.00")
        hsn_total_cgst = Decimal("0.00")
        hsn_total_sgst = Decimal("0.00")
        hsn_total_igst = Decimal("0.00")

        for hsn in hsn_summary:
            total_gst = hsn["cgst"] + hsn["sgst"] + hsn["igst"]

            hsn_list.append(
                {
                    "hsn_sac_code": hsn["hsn_sac_code"],
                    "invoices_count": hsn["invoices_count"],
                    "taxable_value": float(hsn["taxable_value"]),
                    "taxable_value_display": self._format_amount(hsn["taxable_value"]),
                    "cgst": float(hsn["cgst"]),
                    "cgst_display": self._format_amount(hsn["cgst"]),
                    "sgst": float(hsn["sgst"]),
                    "sgst_display": self._format_amount(hsn["sgst"]),
                    "igst": float(hsn["igst"]),
                    "igst_display": self._format_amount(hsn["igst"]),
                    "total_gst": float(total_gst),
                    "total_gst_display": self._format_amount(total_gst),
                }
            )

            hsn_total_invoices += hsn["invoices_count"]
            hsn_total_taxable_value += hsn["taxable_value"]
            hsn_total_cgst += hsn["cgst"]
            hsn_total_sgst += hsn["sgst"]
            hsn_total_igst += hsn["igst"]

        hsn_total_gst = hsn_total_cgst + hsn_total_sgst + hsn_total_igst

        return Response(
            {
                "gst_components": {
                    "taxable_value": float(taxable_value),
                    "taxable_value_display": self._format_amount(taxable_value),
                    "cgst": float(cgst),
                    "cgst_display": self._format_amount(cgst),
                    "sgst": float(sgst),
                    "sgst_display": self._format_amount(sgst),
                    "igst": float(igst),
                    "igst_display": self._format_amount(igst),
                    "cess": float(cess),
                    "cess_display": self._format_amount(cess),
                    "total_gst": float(total_gst),
                    "total_gst_display": self._format_amount(total_gst),
                    "output_tax_payable": float(total_gst),
                    "output_tax_payable_display": self._format_amount(total_gst),
                },
                "invoice_breakdown": {
                    "b2b": {
                        "count": b2b_count,
                        "description": f"{b2b_count} invoices with GSTIN",
                        "total_value": float(b2b_total),
                        "total_value_display": self._format_amount(b2b_total),
                        "percentage": float(b2b_percentage),
                        "percentage_display": f"{b2b_percentage:.1f}%",
                    },
                    "b2c": {
                        "count": b2c_count,
                        "description": f"{b2c_count} invoices without GSTIN",
                        "total_value": float(b2c_total),
                        "total_value_display": self._format_amount(b2c_total),
                        "percentage": float(b2c_percentage),
                        "percentage_display": f"{b2c_percentage:.1f}%",
                    },
                    "total": {
                        "count": total_invoices,
                        "total_value": float(total_revenue),
                        "total_value_display": self._format_amount(total_revenue),
                    },
                },
                "hsn_sac_summary": {
                    "items": hsn_list,
                    "totals": {
                        "invoices_count": hsn_total_invoices,
                        "taxable_value": float(hsn_total_taxable_value),
                        "taxable_value_display": self._format_amount(
                            hsn_total_taxable_value
                        ),
                        "cgst": float(hsn_total_cgst),
                        "cgst_display": self._format_amount(hsn_total_cgst),
                        "sgst": float(hsn_total_sgst),
                        "sgst_display": self._format_amount(hsn_total_sgst),
                        "igst": float(hsn_total_igst),
                        "igst_display": self._format_amount(hsn_total_igst),
                        "total_gst": float(hsn_total_gst),
                        "total_gst_display": self._format_amount(hsn_total_gst),
                    },
                },
            },
            status=status.HTTP_200_OK,
        )


class RevenueDashboardView(APIView):
    """Revenue Dashboard - Unified API for all dashboard metrics"""

    permission_classes = [IsAuthenticated]

    def _in_lakhs(self, amount: Decimal) -> str:
        """Convert amount to lakhs format (₹XX.XXL)"""
        if amount == 0:
            return "₹0.00L"
        lakhs = amount / Decimal("100000")
        return f"₹{lakhs.quantize(Decimal('0.01'))}L"

    def _in_thousands(self, amount: Decimal) -> str:
        """Convert amount to thousands format (₹XX.XXK)"""
        if amount == 0:
            return "₹0.00K"
        thousands = amount / Decimal("1000")
        return f"₹{thousands.quantize(Decimal('0.01'))}K"

    def _format_amount(self, amount: Decimal) -> str:
        """Format amount as K or L based on value"""
        if amount >= Decimal("100000"):
            return self._in_lakhs(amount)
        else:
            return self._in_thousands(amount)

    def _calculate_dso(self, total_receivables, total_invoiced_last_90_days):
        """Calculate Days Sales Outstanding (DSO)"""
        if total_invoiced_last_90_days == 0:
            return 0
        # DSO = (Total Receivables / Total Sales) * Number of Days
        # Using 90 days as the period
        dso = (total_receivables / total_invoiced_last_90_days) * 90
        return int(dso)

    def get(self, request):
        """Get comprehensive Revenue Dashboard data"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"}, status=status.HTTP_404_NOT_FOUND
            )

        today = timezone.now().date()
        current_month_start = today.replace(day=1)
        previous_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
        previous_month_end = current_month_start - timedelta(days=1)
        last_90_days_start = today - timedelta(days=90)

        base_qs = Invoice.objects.filter(company=company).exclude(
            status=InvoicesStatusChoices.CANCELLED
        )

        # ========== KPIs ==========
        # Total Revenue
        total_revenue = base_qs.aggregate(
            total=Coalesce(Sum("total_amount"), Decimal("0.00"))
        )["total"] or Decimal("0.00")
        total_invoices = base_qs.count()

        # This Month Revenue
        this_month_revenue = base_qs.filter(
            invoice_date__gte=current_month_start
        ).aggregate(total=Coalesce(Sum("total_amount"), Decimal("0.00")))[
            "total"
        ] or Decimal(
            "0.00"
        )

        # Previous Month Revenue
        previous_month_revenue = base_qs.filter(
            invoice_date__gte=previous_month_start, invoice_date__lte=previous_month_end
        ).aggregate(total=Coalesce(Sum("total_amount"), Decimal("0.00")))[
            "total"
        ] or Decimal(
            "0.00"
        )

        # MoM Growth
        mom_growth = (
            (
                (this_month_revenue - previous_month_revenue)
                / previous_month_revenue
                * 100
            )
            if previous_month_revenue > 0
            else Decimal("0.00")
        )

        # Avg Invoice
        avg_invoice = (
            total_revenue / Decimal(str(total_invoices))
            if total_invoices > 0
            else Decimal("0.00")
        )

        # Deal-Linked Revenue (invoices with project_id or project_name)
        deal_linked_invoices = base_qs.exclude(
            Q(project_id__isnull=True) | Q(project_id="")
        ).exclude(Q(project_name__isnull=True) | Q(project_name=""))
        deal_linked_count = deal_linked_invoices.count()
        deal_linked_revenue = deal_linked_invoices.aggregate(
            total=Coalesce(Sum("total_amount"), Decimal("0.00"))
        )["total"] or Decimal("0.00")

        # Direct Revenue (not deal-linked)
        direct_revenue = total_revenue - deal_linked_revenue

        # Deal Conversion Rate
        deal_conversion_rate = (
            (deal_linked_count / total_invoices * 100)
            if total_invoices > 0
            else Decimal("0.00")
        )

        # Total Customers
        total_customers = base_qs.values("customer_name").distinct().count()

        # GST Collected
        total_gst = base_qs.aggregate(
            cgst=Coalesce(Sum("cgst_amount"), Decimal("0.00")),
            sgst=Coalesce(Sum("sgst_amount"), Decimal("0.00")),
            igst=Coalesce(Sum("igst_amount"), Decimal("0.00")),
        )
        gst_collected = (
            (total_gst["cgst"] or Decimal("0.00"))
            + (total_gst["sgst"] or Decimal("0.00"))
            + (total_gst["igst"] or Decimal("0.00"))
        )

        # ========== Revenue by Product/Service ==========
        product_revenue = (
            base_qs.values("product_name")
            .annotate(
                revenue=Coalesce(Sum("total_amount"), Decimal("0.00")),
            )
            .order_by("-revenue")[:10]
        )

        product_data = []
        for product in product_revenue:
            share = (
                (product["revenue"] / total_revenue * 100)
                if total_revenue > 0
                else Decimal("0.00")
            )
            product_data.append(
                {
                    "product_name": product["product_name"],
                    "revenue": float(product["revenue"]),
                    "revenue_display": self._format_amount(product["revenue"]),
                    "share": float(share),
                    "share_display": f"{share:.1f}%",
                }
            )

        # ========== Monthly Revenue Trend (Last 12 months) ==========
        monthly_trend = []
        for i in range(11, -1, -1):  # Last 12 months
            month_date = today.replace(day=1) - timedelta(days=30 * i)
            month_start = month_date.replace(day=1)

            last_day = monthrange(month_start.year, month_start.month)[1]
            month_end = month_start.replace(day=last_day)

            month_revenue = base_qs.filter(
                invoice_date__gte=month_start, invoice_date__lte=month_end
            ).aggregate(total=Coalesce(Sum("total_amount"), Decimal("0.00")))[
                "total"
            ] or Decimal(
                "0.00"
            )

            monthly_trend.append(
                {
                    "month": month_start.strftime("%b %y"),
                    "month_key": month_start.strftime("%Y-%m"),
                    "revenue": float(month_revenue),
                    "revenue_display": self._format_amount(month_revenue),
                }
            )

        # ========== AR Health ==========
        # Outstanding AR (all invoices that are not cancelled)
        # For revenue dashboard, Outstanding = Total Revenue (all receivables)
        # Since revenue Invoice model doesn't track paid_amount separately,
        # we show all non-cancelled invoices as outstanding
        outstanding_invoices = base_qs
        outstanding_ar = outstanding_invoices.aggregate(
            total=Coalesce(Sum("total_amount"), Decimal("0.00"))
        )["total"] or Decimal("0.00")

        # Overdue AR (invoices past due date and not paid)
        # Exclude PAID invoices from overdue calculation
        overdue_invoices = base_qs.exclude(status=InvoicesStatusChoices.PAID).filter(
            due_date__lt=today
        )
        overdue_ar = overdue_invoices.aggregate(
            total=Coalesce(Sum("total_amount"), Decimal("0.00"))
        )["total"] or Decimal("0.00")

        # DSO Calculation
        invoiced_last_90_days = base_qs.filter(
            invoice_date__gte=last_90_days_start
        ).aggregate(total=Coalesce(Sum("total_amount"), Decimal("0.00")))[
            "total"
        ] or Decimal(
            "0.00"
        )
        dso = self._calculate_dso(outstanding_ar, invoiced_last_90_days)

        # ========== Customer Concentration ==========
        top_customers = (
            base_qs.values("customer_name")
            .annotate(
                revenue=Coalesce(Sum("total_amount"), Decimal("0.00")),
            )
            .order_by("-revenue")[:5]
        )

        top_5_revenue = sum([c["revenue"] for c in top_customers])
        top_5_concentration = (
            (top_5_revenue / total_revenue * 100)
            if total_revenue > 0
            else Decimal("0.00")
        )

        # Risk Level Assessment
        if top_5_concentration >= 60:
            risk_level = "High"
            risk_message = "High concentration risk - diversify customer base"
        elif top_5_concentration >= 40:
            risk_level = "Medium"
            risk_message = "Monitor closely"
        else:
            risk_level = "Low"
            risk_message = "Well diversified"

        customer_concentration = []
        for customer in top_customers:
            share = (
                (customer["revenue"] / total_revenue * 100)
                if total_revenue > 0
                else Decimal("0.00")
            )
            customer_concentration.append(
                {
                    "customer_name": customer["customer_name"],
                    "revenue": float(customer["revenue"]),
                    "revenue_display": self._format_amount(customer["revenue"]),
                    "share": float(share),
                    "share_display": f"{share:.1f}%",
                }
            )

        return Response(
            {
                "kpis": {
                    "total_revenue": {
                        "value": float(total_revenue),
                        "value_display": self._format_amount(total_revenue),
                        "invoices_count": total_invoices,
                        "description": f"{total_invoices} invoices",
                    },
                    "this_month_revenue": {
                        "value": float(this_month_revenue),
                        "value_display": self._format_amount(this_month_revenue),
                        "mom_growth": float(mom_growth),
                        "mom_growth_display": f"{mom_growth:+.1f}% MoM",
                    },
                    "avg_invoice": {
                        "value": float(avg_invoice),
                        "value_display": self._format_amount(avg_invoice),
                        "description": "per invoice",
                    },
                    "deal_linked": {
                        "value": float(deal_linked_revenue),
                        "value_display": self._format_amount(deal_linked_revenue),
                        "invoices_count": deal_linked_count,
                        "description": f"{deal_linked_count} invoices",
                    },
                    "customers": {
                        "value": total_customers,
                        "description": "unique customers",
                    },
                    "gst_collected": {
                        "value": float(gst_collected),
                        "value_display": self._format_amount(gst_collected),
                        "description": "Total GST",
                    },
                },
                "revenue_by_product": product_data,
                "monthly_revenue_trend": monthly_trend,
                "ar_health": {
                    "outstanding": float(outstanding_ar),
                    "outstanding_display": self._format_amount(outstanding_ar),
                    "dso": dso,
                    "dso_display": f"{dso} days",
                    "overdue": float(overdue_ar),
                    "overdue_display": self._format_amount(overdue_ar),
                },
                "customer_concentration": {
                    "top_5_concentration": float(top_5_concentration),
                    "top_5_concentration_display": f"{top_5_concentration:.1f}%",
                    "risk_level": risk_level,
                    "risk_message": risk_message,
                    "top_customers": customer_concentration,
                },
                "sales_pipeline": {
                    "deal_linked_revenue": {
                        "value": float(deal_linked_revenue),
                        "value_display": self._format_amount(deal_linked_revenue),
                        "invoices_count": deal_linked_count,
                        "description": f"{deal_linked_count} invoices",
                    },
                    "direct_revenue": {
                        "value": float(direct_revenue),
                        "value_display": self._format_amount(direct_revenue),
                        "description": "No deal link",
                    },
                    "deal_conversion_rate": float(deal_conversion_rate),
                    "deal_conversion_rate_display": f"{deal_conversion_rate:.1f}%",
                    "conversion_description": f"{deal_linked_count} of {total_invoices} invoices linked to deals",
                },
            },
            status=status.HTTP_200_OK,
        )
