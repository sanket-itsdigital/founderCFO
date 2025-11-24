from django.db.models import Count, Q, Sum, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone
from decimal import Decimal
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from compliance.models import ComplianceTaskMaster, CompliancePayments
from backend.enums import ComplianceStatusChoices


class ActWiseSummaryView(APIView):
    """
    Act-wise summary showing:
    Total tasks, Completed, Pending, In progress, Overdue, Critical Task, 
    High severity, Completion rate%, Health status
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        act = request.query_params.get("act", None)
        
        # Base queryset
        tasks = ComplianceTaskMaster.objects.all()
        if act:
            tasks = tasks.filter(act=act)
        
        # Group by act
        acts = tasks.values("act").distinct()
        
        summary_data = []
        
        for act_data in acts:
            act_name = act_data["act"]
            act_tasks = tasks.filter(act=act_name)
            
            total_tasks = act_tasks.count()
            completed = act_tasks.filter(status=ComplianceStatusChoices.COMPLETED).count()
            pending = act_tasks.filter(status=ComplianceStatusChoices.PENDING).count()
            in_progress = act_tasks.filter(status=ComplianceStatusChoices.IN_PROGRESS).count()
            overdue = act_tasks.filter(is_overdue=True).count()
            
            # Critical tasks (assuming severity='critical' or 'high')
            critical_tasks = act_tasks.filter(
                Q(severity__icontains="critical") | Q(severity__icontains="high")
            ).count()
            
            # High severity tasks
            high_severity = act_tasks.filter(severity__icontains="high").count()
            
            # Completion rate
            completion_rate = (
                (completed / total_tasks * 100) if total_tasks > 0 else 0
            )
            
            # Health status based on completion rate and overdue tasks
            if completion_rate >= 80 and overdue == 0:
                health_status = "Excellent"
            elif completion_rate >= 60 and overdue <= total_tasks * 0.1:
                health_status = "Good"
            elif completion_rate >= 40 and overdue <= total_tasks * 0.2:
                health_status = "Fair"
            else:
                health_status = "Poor"
            
            summary_data.append({
                "act_name": act_name,
                "total_tasks": total_tasks,
                "completed": completed,
                "pending": pending,
                "in_progress": in_progress,
                "overdue": overdue,
                "critical_tasks": critical_tasks,
                "high_severity": high_severity,
                "completion_rate": round(completion_rate, 2),
                "health_status": health_status,
            })
        
        return Response(summary_data)


class ExposureAnalysisView(APIView):
    """
    Exposure analysis showing:
    Total acts, Estimated Penalties (₹), Estimated Interest (₹), 
    Estimated Late Fees (₹), Total Exposure (₹), Overdue Tasks, Critical Overdue
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        act = request.query_params.get("act", None)
        
        # Get all unique acts from both tasks and payments
        tasks = ComplianceTaskMaster.objects.all()
        payments = CompliancePayments.objects.all()
        
        if act:
            tasks = tasks.filter(act=act)
            payments = payments.filter(related_act=act)
        
        # Get unique acts from tasks
        task_acts = tasks.values_list("act", flat=True).distinct()
        payment_acts = payments.values_list("related_act", flat=True).distinct()
        all_acts = set(list(task_acts) + [a for a in payment_acts if a])
        
        exposure_data = []
        
        for act_name in all_acts:
            if not act_name:
                continue
            
            act_payments = payments.filter(related_act=act_name)
            act_tasks = tasks.filter(act=act_name)
            
            # Aggregate financial data from payments
            payment_penalty = act_payments.aggregate(
                total=Coalesce(Sum("estimated_penalty"), Decimal("0"), output_field=DecimalField())
            )["total"] or Decimal("0")
            
            payment_interest = act_payments.aggregate(
                total=Coalesce(Sum("estimated_interest"), Decimal("0"), output_field=DecimalField())
            )["total"] or Decimal("0")
            
            payment_late_fee = act_payments.aggregate(
                total=Coalesce(Sum("estimated_late_fee"), Decimal("0"), output_field=DecimalField())
            )["total"] or Decimal("0")
            
            # Aggregate financial data from tasks (convert string to float)
            task_penalty_sum = 0
            task_interest_sum = 0
            task_late_fee_sum = 0
            
            for task in act_tasks:
                try:
                    if task.penalty:
                        task_penalty_sum += float(task.penalty)
                except (ValueError, TypeError):
                    pass
                try:
                    if task.interest_amount:
                        task_interest_sum += float(task.interest_amount)
                except (ValueError, TypeError):
                    pass
                try:
                    if task.late_fee:
                        task_late_fee_sum += float(task.late_fee)
                except (ValueError, TypeError):
                    pass
            
            estimated_penalty = float(payment_penalty) + task_penalty_sum
            estimated_interest = float(payment_interest) + task_interest_sum
            estimated_late_fee = float(payment_late_fee) + task_late_fee_sum
            
            total_exposure = estimated_penalty + estimated_interest + estimated_late_fee
            
            # Get overdue tasks for this act
            overdue_tasks = act_tasks.filter(is_overdue=True).count()
            
            # Critical overdue tasks
            critical_overdue = act_tasks.filter(
                is_overdue=True,
            ).filter(
                Q(severity__icontains="critical") | Q(severity__icontains="high")
            ).count()
            
            exposure_data.append({
                "act_name": act_name,
                "estimated_penalty": round(estimated_penalty, 2),
                "estimated_interest": round(estimated_interest, 2),
                "estimated_late_fee": round(estimated_late_fee, 2),
                "total_exposure": round(total_exposure, 2),
                "overdue_tasks": overdue_tasks,
                "critical_overdue": critical_overdue,
            })
        
        return Response(exposure_data)

