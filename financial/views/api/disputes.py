from decimal import Decimal
from datetime import timedelta

from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Company
from financial.models.disputes import Dispute
from financial.enums import DisputeStatusChoices
from financial.serializers.disputes import DisputeSerializer, DisputeCreateSerializer
from financial.views.api.ar_aging import get_company_from_request


class DisputesSummaryView(APIView):
    """Get disputes summary statistics"""
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        company = get_company_from_request(request)
        if not company:
            return Response({
                "open_disputes": 0,
                "disputed_amount": 0,
                "resolved_this_month": 0,
                "total_disputes": 0,
            })

        today = timezone.now().date()
        month_start = today.replace(day=1)

        open_disputes = Dispute.objects.filter(
            company=company,
            status=DisputeStatusChoices.OPEN
        ).count()

        disputed_amount = Dispute.objects.filter(
            company=company,
            status=DisputeStatusChoices.OPEN
        ).aggregate(
            total=Sum('disputed_amount')
        )['total'] or Decimal("0.00")

        resolved_this_month = Dispute.objects.filter(
            company=company,
            status=DisputeStatusChoices.RESOLVED,
            resolved_at__gte=month_start
        ).count()

        total_disputes = Dispute.objects.filter(company=company).count()

        return Response({
            "open_disputes": open_disputes,
            "disputed_amount": float(disputed_amount),
            "disputed_amount_display": self._format_amount(disputed_amount),
            "resolved_this_month": resolved_this_month,
            "total_disputes": total_disputes,
        })

    @staticmethod
    def _format_amount(amount):
        """Format amount for display"""
        if amount >= 1000:
            return f"₹{amount / 1000:.2f}K"
        return f"₹{amount:.2f}"


class DisputeListCreateView(generics.ListCreateAPIView):
    """List and create disputes"""
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return DisputeCreateSerializer
        return DisputeSerializer

    def get_queryset(self):
        company = get_company_from_request(self.request)
        if not company:
            return Dispute.objects.none()
        
        queryset = Dispute.objects.filter(company=company).select_related('invoice')
        
        # Optional filters
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        company = get_company_from_request(self.request)
        serializer.save(company=company)


class DisputeRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    """Retrieve or update dispute"""
    permission_classes = [IsAuthenticated]
    serializer_class = DisputeSerializer
    lookup_field = "id"

    def get_queryset(self):
        company = get_company_from_request(self.request)
        if not company:
            return Dispute.objects.none()
        
        return Dispute.objects.filter(company=company).select_related('invoice')


class ResolveDisputeView(APIView):
    """Resolve a dispute"""
    permission_classes = [IsAuthenticated]

    def post(self, request, dispute_id, *args, **kwargs):
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            dispute = Dispute.objects.get(id=dispute_id, company=company)
            resolution_notes = request.data.get("resolution_notes", "")
            dispute.mark_as_resolved(resolution_notes)
            
            serializer = DisputeSerializer(dispute)
            return Response(serializer.data)
        except Dispute.DoesNotExist:
            return Response(
                {"error": "Dispute not found"},
                status=status.HTTP_404_NOT_FOUND
            )

