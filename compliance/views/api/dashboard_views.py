from django.db.models import Count, Q, Sum, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.utils import get_user_company
from compliance.models import ComplianceTaskMaster, CompliancePayments
from backend.enums import ComplianceStatusChoices


class ComplianceDashboardView(APIView):
    """
    Compliance Dashboard showing:
    Total Tasks, Completed Tasks, Pending Tasks, In Progress, Overdue Tasks,
    Critical Tasks, High Severity, Due This Month, Completion Rate %,
    Compliance Health Score, Total Exposure (₹), Litigation Exposure (₹),
    Total Provisions (₹), Payments This Month (₹)
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # Task statistics
        all_tasks = ComplianceTaskMaster.objects.all()

        # For non-superusers, filter by company's selected tasks
        # Use get_user_company to get company from logged-in user only (ignore query params)
        if not request.user.is_superuser:
            company = get_user_company(request.user)
            if company:
                all_tasks = all_tasks.filter(companies=company)
            else:
                all_tasks = all_tasks.none()

        total_tasks = all_tasks.count()
        completed_tasks = all_tasks.filter(
            status=ComplianceStatusChoices.COMPLETED
        ).count()
        pending_tasks = all_tasks.filter(status=ComplianceStatusChoices.PENDING).count()
        in_progress = all_tasks.filter(
            status=ComplianceStatusChoices.IN_PROGRESS
        ).count()
        overdue_tasks = all_tasks.filter(is_overdue=True).count()

        # Critical tasks
        critical_tasks = all_tasks.filter(
            Q(severity__icontains="critical") | Q(severity__icontains="high")
        ).count()

        # High severity
        high_severity = all_tasks.filter(severity__icontains="high").count()

        # Due this month
        today = timezone.now().date()
        first_day_month = today.replace(day=1)
        last_day_month = (first_day_month + timedelta(days=32)).replace(
            day=1
        ) - timedelta(days=1)

        due_this_month = all_tasks.filter(
            due_date__gte=first_day_month, due_date__lte=last_day_month
        ).count()

        # Completion rate
        completion_rate = (
            (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        )

        # Compliance Health Score (0-100 scale)
        # Based on completion rate, overdue ratio, and critical tasks ratio
        # If there are no tasks, health score should be 0 (not applicable)
        if total_tasks == 0:
            health_score = 0.0
        else:
            overdue_ratio = (overdue_tasks / total_tasks) if total_tasks > 0 else 0
            critical_ratio = (critical_tasks / total_tasks) if total_tasks > 0 else 0

            health_score = max(
                0,
                min(
                    100,
                    completion_rate * 0.5  # 50% weight on completion
                    + (1 - overdue_ratio * 2) * 30  # 30% weight on overdue (penalized)
                    + (1 - critical_ratio) * 20,  # 20% weight on critical tasks
                ),
            )

        # Financial exposure
        all_payments = CompliancePayments.objects.all()

        # For non-superusers, filter payments by company's selected tasks
        # Use get_user_company to get company from logged-in user only (ignore query params)
        if not request.user.is_superuser:
            company = get_user_company(request.user)
            if company:
                # Get task IDs for company's selected tasks
                company_task_ids = company.selected_compliance_tasks.values_list(
                    "id", flat=True
                )
                all_payments = all_payments.filter(
                    compliance_task_id__in=company_task_ids
                )
            else:
                all_payments = all_payments.none()

        penalty_sum = all_payments.aggregate(
            total=Coalesce(
                Sum("estimated_penalty"), Decimal("0"), output_field=DecimalField()
            )
        )["total"] or Decimal("0")

        interest_sum = all_payments.aggregate(
            total=Coalesce(
                Sum("estimated_interest"), Decimal("0"), output_field=DecimalField()
            )
        )["total"] or Decimal("0")

        late_fee_sum = all_payments.aggregate(
            total=Coalesce(
                Sum("estimated_late_fee"), Decimal("0"), output_field=DecimalField()
            )
        )["total"] or Decimal("0")

        total_exposure = float(penalty_sum) + float(interest_sum) + float(late_fee_sum)

        # Litigation exposure (can be extended based on business logic)
        litigation_exposure = 0  # Placeholder - can be calculated from related models

        # Total provisions (can be extended based on business logic)
        total_provisions = 0  # Placeholder - can be calculated from related models

        # Payments this month
        month_payments = all_payments.filter(
            payment_date__gte=first_day_month, payment_date__lte=last_day_month
        )

        month_penalty = month_payments.aggregate(
            total=Coalesce(
                Sum("estimated_penalty"), Decimal("0"), output_field=DecimalField()
            )
        )["total"] or Decimal("0")

        month_interest = month_payments.aggregate(
            total=Coalesce(
                Sum("estimated_interest"), Decimal("0"), output_field=DecimalField()
            )
        )["total"] or Decimal("0")

        month_late_fee = month_payments.aggregate(
            total=Coalesce(
                Sum("estimated_late_fee"), Decimal("0"), output_field=DecimalField()
            )
        )["total"] or Decimal("0")

        payments_this_month = (
            float(month_penalty) + float(month_interest) + float(month_late_fee)
        )

        # For doughnut chart reference
        completed_portion = completed_tasks
        remaining = total_tasks - completed_tasks

        dashboard_data = {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "pending_tasks": pending_tasks,
            "in_progress": in_progress,
            "overdue_tasks": overdue_tasks,
            "critical_tasks": critical_tasks,
            "high_severity": high_severity,
            "due_this_month": due_this_month,
            "completion_rate": round(completion_rate, 2),
            "compliance_health_score": round(health_score, 2),
            "total_exposure": float(total_exposure),
            "litigation_exposure": float(litigation_exposure),
            "total_provisions": float(total_provisions),
            "payments_this_month": float(payments_this_month),
            "doughnut_chart": {
                "completed_portion": completed_portion,
                "remaining": remaining,
            },
        }

        return Response(dashboard_data)
