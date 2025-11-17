from collections import Counter, OrderedDict
from datetime import date

from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.enums import CaseStatusChoices, CaseTypeChoices
from litigation.models import Case


class AnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self, request):
        company_id = request.query_params.get("company_id")
        qs = Case.objects.filter(company__owner=request.user)
        if company_id:
            qs = qs.filter(company_id=company_id)
        return qs

    def get(self, request, *args, **kwargs):
        qs = self.get_queryset(request)

        # Cases by Type (include missing values as 0)
        cases_by_type = qs.values_list("type", flat=True)
        type_counter = Counter(cases_by_type)
        type_counts = {
            choice.value: type_counter.get(choice.value, 0)
            for choice in CaseTypeChoices
        }

        # Cases by Status (include missing values as 0)
        cases_by_status = qs.values_list("status", flat=True)
        status_counter = Counter(cases_by_status)
        status_counts = {
            choice.value: status_counter.get(choice.value, 0)
            for choice in CaseStatusChoices
        }

        # Cases filed over time (last 12 months, include zeros)
        monthly_qs = (
            qs.filter(issue_date__isnull=False)
            .annotate(month=TruncMonth("issue_date"))
            .values("month")
            .annotate(count=Count("id"))
        )
        monthly_counts = {
            row["month"].strftime("%Y-%m"): row["count"]
            for row in monthly_qs
            if row["month"]
        }
        today = date.today().replace(day=1)
        months = []
        year, month = today.year, today.month
        for _ in range(12):
            months.append((year, month))
            month -= 1
            if month == 0:
                month = 12
                year -= 1
        months.reverse()
        series = OrderedDict(
            (f"{y}-{m:02d}", monthly_counts.get(f"{y}-{m:02d}", 0)) for y, m in months
        )

        # Financial exposure by type (Lakhs)
        exposure_by_type = (
            qs.values("type").annotate(total=Sum("total_exposure")).order_by("type")
        )
        exposure_map = {
            row["type"]: float(row["total"]) / 100000 if row["total"] else 0.0
            for row in exposure_by_type
        }
        exposure_lakhs = [
            {
                "type": choice.value,
                "total_lakhs": round(exposure_map.get(choice.value, 0.0), 2),
            }
            for choice in CaseTypeChoices
        ]

        # Top 10 cases by exposure
        top_cases_qs = qs.order_by("-total_exposure")[:10]
        top_cases = [
            {
                "case_number": c.case_number,
                "type": c.type,
                "synopsis": c.synopsis,
                "total_exposure": float(c.total_exposure),
                "issue_date": c.issue_date,
                "due_date": c.due_date,
                "status": c.status,
                "risk": c.risk,
            }
            for c in top_cases_qs
        ]

        # Key insights (simple heuristics)
        total_cases = qs.count()
        most_common_type = (
            max(type_counts.items(), key=lambda x: x[1]) if type_counts else (None, 0)
        )
        highest_exposure = (
            max(exposure_lakhs, key=lambda x: x["total_lakhs"])
            if exposure_lakhs
            else {"type": None, "total_lakhs": 0}
        )
        resolved = status_counts.get(CaseStatusChoices.RESOLVED, 0)
        resolution_rate = round((resolved / total_cases) * 100) if total_cases else 0
        insights = {
            "most_common_type": {
                "type": most_common_type[0],
                "count": most_common_type[1],
            },
            "highest_exposure_type": {
                "type": highest_exposure["type"],
                "total_lakhs": highest_exposure["total_lakhs"],
            },
            "resolution_rate": {
                "percent": resolution_rate,
                "resolved_cases": resolved,
                "total_cases": total_cases,
            },
        }

        data = {
            "cases_by_type": type_counts,
            "cases_by_status": status_counts,
            "cases_over_time": series,
            "exposure_by_type_lakhs": exposure_lakhs,
            "top_cases_by_exposure": top_cases,
            "key_insights": insights,
        }
        return Response(data)
