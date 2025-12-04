from django.db.models import Q, Count
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Company
from financial.models.account_receivable.audit_trail import AuditTrail
from financial.serializers.account_receivable.audit_trail import AuditTrailSerializer
from financial.views.api.account_receivable.ar_aging import get_company_from_request


class AuditTrailSummaryView(APIView):
    """Get audit trail summary statistics"""
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        company = get_company_from_request(request)
        if not company:
            return Response({
                "today_activity": 0,
                "payments_logged": 0,
                "communications": 0,
                "total_records": 0,
            })

        today = timezone.now().date()
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # Today's activity
        today_activity = AuditTrail.objects.filter(
            company=company,
            created_at__gte=today_start
        ).count()

        # Payments logged
        payments_logged = AuditTrail.objects.filter(
            company=company,
            action="payment"
        ).count()

        # Communications (emails and calls)
        communications = AuditTrail.objects.filter(
            company=company,
            action__in=["email", "call"]
        ).count()

        # Total records
        total_records = AuditTrail.objects.filter(company=company).count()

        return Response({
            "today_activity": today_activity,
            "payments_logged": payments_logged,
            "communications": communications,
            "total_records": total_records,
        })


class AuditTrailListView(generics.ListAPIView):
    """List audit trail entries with filtering"""
    permission_classes = [IsAuthenticated]
    serializer_class = AuditTrailSerializer

    def get_queryset(self):
        company = get_company_from_request(self.request)
        if not company:
            return AuditTrail.objects.none()
        
        queryset = AuditTrail.objects.filter(company=company).select_related('user')
        
        # Filter by action
        action = self.request.query_params.get("action")
        if action:
            queryset = queryset.filter(action=action)
        
        # Filter by entity type
        entity_type = self.request.query_params.get("entity_type")
        if entity_type:
            queryset = queryset.filter(entity_type=entity_type)
        
        # Search by reference or details
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(reference__icontains=search) |
                Q(details__icontains=search)
            )
        
        return queryset.order_by('-created_at')

