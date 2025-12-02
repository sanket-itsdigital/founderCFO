from datetime import date

from django.db.models import Avg, Count, Q, Sum
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.enums import CaseStatusChoices, RiskLevelChoices
from litigation.models import Case


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get_company_id(self, request):
        return request.query_params.get("company_id")

    def get_queryset(self, request):
        company_id = self.get_company_id(request)
        qs = Case.objects.filter(company__owner=request.user)
        if company_id:
            qs = qs.filter(company_id=company_id)
        return qs

    def get(self, request, *args, **kwargs):
        qs = self.get_queryset(request)

        total_cases = qs.count()
        agg = qs.aggregate(total=Sum("total_exposure"))
        total_exposure = (agg or {}).get("total") or 0

        high_risk_cases = (
            qs.filter(risk=RiskLevelChoices.HIGH).count()
            + qs.filter(risk=RiskLevelChoices.CRITICAL).count()
        )

        today = date.today()
        due_this_month = qs.filter(
            due_date__year=today.year, due_date__month=today.month
        ).count()

        # Average age in days from issue_date to today
        # Use annotation with extraction to avoid DB-specific functions
        ages = [
            (today - c.issue_date).days for c in qs.only("issue_date") if c.issue_date
        ]
        avg_age_days = round(sum(ages) / len(ages)) if ages else 0

        # Success rate: resolved over closed-like statuses
        closed_like = qs.filter(
            status__in=[
                CaseStatusChoices.RESOLVED,
                CaseStatusChoices.CLOSED,
                CaseStatusChoices.DISMISSED,
            ]
        )
        wins = qs.filter(status=CaseStatusChoices.RESOLVED).count()
        total_closed = closed_like.count()
        success_rate = round((wins / total_closed) * 100) if total_closed else 0

        data = {
            "total_cases": total_cases,
            "total_exposure": total_exposure,
            "high_risk_cases": high_risk_cases,
            "due_this_month": due_this_month,
            "average_case_age_days": avg_age_days,
            "success_rate_percent": success_rate,
        }
        return Response(data)
