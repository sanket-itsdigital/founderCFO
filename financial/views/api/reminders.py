from decimal import Decimal
from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Company
from financial.models.reminders import Reminder, ReminderRule
from financial.models.account_receivable import Invoice
from financial.enums import ReminderStatusChoices, ReminderTriggerTypeChoices, InvoicesStatusChoices
from financial.serializers.reminders import (
    ReminderRuleSerializer,
    ReminderScheduleSerializer,
    ReminderHistorySerializer,
)
from financial.views.api.ar_aging import get_company_from_request


class RemindersSummaryView(APIView):
    """Get reminders summary statistics"""
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        company = get_company_from_request(request)
        if not company:
            return Response({
                "due_today": 0,
                "scheduled": 0,
                "sent_this_month": 0,
                "active_rules": 0,
            })

        today = timezone.now().date()
        month_start = today.replace(day=1)

        due_today = Reminder.objects.filter(
            company=company,
            scheduled_date=today,
            status=ReminderStatusChoices.PENDING
        ).count()

        scheduled = Reminder.objects.filter(
            company=company,
            scheduled_date__gt=today,
            status=ReminderStatusChoices.PENDING
        ).count()

        sent_this_month = Reminder.objects.filter(
            company=company,
            status=ReminderStatusChoices.SENT,
            sent_at__gte=month_start
        ).count()

        active_rules = ReminderRule.objects.filter(
            company=company,
            is_active=True
        ).count()

        return Response({
            "due_today": due_today,
            "scheduled": scheduled,
            "sent_this_month": sent_this_month,
            "active_rules": active_rules,
        })


class ReminderScheduleListView(generics.ListAPIView):
    """List upcoming reminders schedule"""
    permission_classes = [IsAuthenticated]
    serializer_class = ReminderScheduleSerializer

    def get_queryset(self):
        company = get_company_from_request(self.request)
        if not company:
            return Reminder.objects.none()
        
        return Reminder.objects.filter(
            company=company,
            status=ReminderStatusChoices.PENDING
        ).select_related('invoice', 'reminder_rule').order_by('scheduled_date')


class ReminderRuleListCreateView(generics.ListCreateAPIView):
    """List and create reminder rules"""
    permission_classes = [IsAuthenticated]
    serializer_class = ReminderRuleSerializer

    def get_queryset(self):
        company = get_company_from_request(self.request)
        if not company:
            return ReminderRule.objects.none()
        
        return ReminderRule.objects.filter(company=company).order_by('trigger_days')

    def perform_create(self, serializer):
        company = get_company_from_request(self.request)
        serializer.save(company=company)


class ReminderRuleRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete reminder rule"""
    permission_classes = [IsAuthenticated]
    serializer_class = ReminderRuleSerializer
    lookup_field = "id"

    def get_queryset(self):
        company = get_company_from_request(self.request)
        if not company:
            return ReminderRule.objects.none()
        
        return ReminderRule.objects.filter(company=company)


class ReminderHistoryListView(generics.ListAPIView):
    """List sent reminders history"""
    permission_classes = [IsAuthenticated]
    serializer_class = ReminderHistorySerializer

    def get_queryset(self):
        company = get_company_from_request(self.request)
        if not company:
            return Reminder.objects.none()
        
        return Reminder.objects.filter(
            company=company,
            status=ReminderStatusChoices.SENT
        ).select_related('invoice', 'reminder_rule').order_by('-sent_at')


class SendReminderView(APIView):
    """Send a reminder manually"""
    permission_classes = [IsAuthenticated]

    def post(self, request, reminder_id, *args, **kwargs):
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            reminder = Reminder.objects.get(id=reminder_id, company=company)
            reminder.mark_as_sent()
            return Response({
                "message": "Reminder sent successfully",
                "reminder_id": str(reminder.id)
            })
        except Reminder.DoesNotExist:
            return Response(
                {"error": "Reminder not found"},
                status=status.HTTP_404_NOT_FOUND
            )


class GenerateRemindersView(APIView):
    """Generate reminders based on active rules"""
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get active rules
        rules = ReminderRule.objects.filter(company=company, is_active=True)
        
        # Get all pending invoices
        invoices = Invoice.objects.filter(
            company=company
        ).exclude(
            status__in=[InvoicesStatusChoices.PAID, InvoicesStatusChoices.CANCELLED]
        )

        created_count = 0
        
        for rule in rules:
            for invoice in invoices:
                # Calculate scheduled date
                scheduled_date = rule.calculate_scheduled_date(invoice.due_date)
                
                # Only create if scheduled date is today or in the future
                if scheduled_date >= timezone.now().date():
                    # Check if reminder already exists
                    if not Reminder.objects.filter(
                        company=company,
                        invoice=invoice,
                        reminder_rule=rule,
                        scheduled_date=scheduled_date
                    ).exists():
                        Reminder.objects.create(
                            company=company,
                            invoice=invoice,
                            reminder_rule=rule,
                            scheduled_date=scheduled_date,
                            email_template_name=rule.email_template_name,
                            status=ReminderStatusChoices.PENDING
                        )
                        created_count += 1

        return Response({
            "message": f"Generated {created_count} reminders",
            "created_count": created_count
        })

