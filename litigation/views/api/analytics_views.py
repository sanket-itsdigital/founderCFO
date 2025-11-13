from collections import Counter
from datetime import date

from django.db.models import Sum
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.enums import CaseStatusChoices
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

        # Cases by Type
        cases_by_type = qs.values_list("type", flat=True)
        type_counter = Counter(cases_by_type)

        # Cases by Status
        cases_by_status = qs.values_list("status", flat=True)
        status_counter = Counter(cases_by_status)

        # Cases filed over time (by month for last 12 months)
        today = date.today()
        series = {}
        for c in qs.only("issue_date"):
            if not c.issue_date:
                continue
            key = c.issue_date.strftime("%Y-%m")
            series[key] = series.get(key, 0) + 1

        # Financial exposure by type (Lakhs)
        exposure_by_type = (
            qs.values("type").annotate(total=Sum("total_exposure")).order_by("type")
        )
        exposure_lakhs = [
            {
                "type": row["type"],
                "total_lakhs": float(row["total"]) / 100000 if row["total"] else 0.0,
            }
            for row in exposure_by_type
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
        insights = []
        if exposure_lakhs:
            max_type = max(exposure_lakhs, key=lambda x: x["total_lakhs"])  # type: ignore[arg-type]
            insights.append(
                f"Highest financial exposure in {max_type['type']} (~{max_type['total_lakhs']:.2f} Lakh)."
            )
        if status_counter:
            open_count = status_counter.get(
                CaseStatusChoices.OPEN, 0
            ) + status_counter.get("open", 0)
            in_progress = status_counter.get(
                CaseStatusChoices.IN_PROGRESS, 0
            ) + status_counter.get("in progress", 0)
            insights.append(f"{open_count} open and {in_progress} in-progress cases.")
        if series:
            recent_key = max(series.keys())
            insights.append(f"Recent filings: {series[recent_key]} in {recent_key}.")

        data = {
            "cases_by_type": type_counter,
            "cases_by_status": status_counter,
            "cases_over_time": series,
            "exposure_by_type_lakhs": exposure_lakhs,
            "top_cases_by_exposure": top_cases,
            "key_insights": insights,
        }
        return Response(data)
