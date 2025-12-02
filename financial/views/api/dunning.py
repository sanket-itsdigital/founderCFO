from decimal import Decimal
from collections import defaultdict

from django.db.models import Count, F
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Company
from financial.models.dunning import DunningQueue, EmailTemplate
from financial.models.account_receivable import Invoice
from financial.enums import DunningStageChoices, InvoicesStatusChoices
from financial.serializers.dunning import DunningQueueSerializer, EmailTemplateSerializer
from financial.views.api.ar_aging import get_company_from_request


class DunningSummaryView(APIView):
    """Get dunning summary by stage"""
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        company = get_company_from_request(request)
        if not company:
            return Response({
                "friendly_count": 0,
                "firm_count": 0,
                "urgent_count": 0,
                "final_count": 0,
                "total_overdue": 0,
            })

        # Get all overdue invoices
        today = timezone.now().date()
        overdue_invoices = Invoice.objects.filter(
            company=company,
            due_date__lt=today
        ).exclude(
            status__in=[InvoicesStatusChoices.PAID, InvoicesStatusChoices.CANCELLED]
        ).filter(
            total_amount__gt=F('paid_amount')
        )

        stage_counts = defaultdict(int)
        
        for invoice in overdue_invoices:
            days_overdue = (today - invoice.due_date).days
            stage = DunningQueue.calculate_stage(days_overdue)
            stage_counts[stage] += 1

        return Response({
            "friendly_count": stage_counts[DunningStageChoices.FRIENDLY],
            "firm_count": stage_counts[DunningStageChoices.FIRM],
            "urgent_count": stage_counts[DunningStageChoices.URGENT],
            "final_count": stage_counts[DunningStageChoices.FINAL],
            "total_overdue": overdue_invoices.count(),
        })


class DunningQueueListView(generics.ListAPIView):
    """List dunning queue"""
    permission_classes = [IsAuthenticated]
    serializer_class = DunningQueueSerializer

    def get_queryset(self):
        company = get_company_from_request(self.request)
        if not company:
            return DunningQueue.objects.none()
        
        # Optional filter by stage
        stage = self.request.query_params.get("stage")
        queryset = DunningQueue.objects.filter(company=company).select_related('invoice')
        
        if stage:
            queryset = queryset.filter(stage=stage)
        
        return queryset.order_by('-days_overdue')


class GenerateDunningQueueView(APIView):
    """Generate/update dunning queue from overdue invoices"""
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        today = timezone.now().date()
        overdue_invoices = Invoice.objects.filter(
            company=company,
            due_date__lt=today
        ).exclude(
            status__in=[InvoicesStatusChoices.PAID, InvoicesStatusChoices.CANCELLED]
        ).filter(
            total_amount__gt=F('paid_amount')
        )

        created_count = 0
        updated_count = 0

        for invoice in overdue_invoices:
            days_overdue = (today - invoice.due_date).days
            stage = DunningQueue.calculate_stage(days_overdue)
            
            queue_item, created = DunningQueue.objects.update_or_create(
                company=company,
                invoice=invoice,
                stage=stage,
                defaults={
                    'days_overdue': days_overdue,
                }
            )
            
            if created:
                created_count += 1
            else:
                updated_count += 1

        return Response({
            "message": f"Generated/updated {created_count + updated_count} dunning queue items",
            "created": created_count,
            "updated": updated_count,
        })


class EmailTemplateListCreateView(generics.ListCreateAPIView):
    """List and create email templates"""
    permission_classes = [IsAuthenticated]
    serializer_class = EmailTemplateSerializer

    def get_queryset(self):
        company = get_company_from_request(self.request)
        # Get company-specific and global templates
        queryset = EmailTemplate.objects.filter(
            Q(company=company) | Q(company__isnull=True)
        )
        return queryset.order_by('name')

    def perform_create(self, serializer):
        company = get_company_from_request(self.request)
        serializer.save(company=company)


class EmailTemplateRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete email template"""
    permission_classes = [IsAuthenticated]
    serializer_class = EmailTemplateSerializer
    lookup_field = "id"

    def get_queryset(self):
        company = get_company_from_request(self.request)
        return EmailTemplate.objects.filter(
            Q(company=company) | Q(company__isnull=True)
        )

