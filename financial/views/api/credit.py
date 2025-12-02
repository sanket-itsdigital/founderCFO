from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import Company
from financial.models.credit import Credit
from financial.serializers.credit import CreditListSerializer, CreditDetailSerializer


def get_company_from_request(request):
    """Helper function to get company from request"""
    company_id = request.query_params.get("company_id")
    if company_id:
        try:
            return Company.objects.get(id=company_id, owner=request.user)
        except Company.DoesNotExist:
            return None
    # Try to get the first company owned by the user
    return Company.objects.filter(owner=request.user).first()


class CreditListView(generics.ListAPIView):
    """
    List all customer credits for a company.
    Returns credit limits with calculated fields like current balance, utilization, etc.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = CreditListSerializer

    def get_queryset(self):
        """Filter credits by company"""
        company = get_company_from_request(self.request)
        if not company:
            return Credit.objects.none()
        
        queryset = Credit.objects.filter(company=company)
        
        # Optional: Filter by customer name
        customer_name = self.request.query_params.get("customer_name")
        if customer_name:
            queryset = queryset.filter(customer_name__icontains=customer_name)
        
        return queryset.order_by("customer_name")


class CreditRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    """
    Retrieve a single credit record or update credit_limit.
    Only the credit_limit field can be updated.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = CreditDetailSerializer
    lookup_field = "id"

    def get_queryset(self):
        """Filter credits by company"""
        company = get_company_from_request(self.request)
        if not company:
            return Credit.objects.none()
        
        return Credit.objects.filter(company=company)

    def update(self, request, *args, **kwargs):
        """Update only credit_limit field"""
        instance = self.get_object()
        
        # Only allow updating credit_limit
        if "credit_limit" not in request.data:
            return Response(
                {"error": "Only credit_limit field can be updated"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if any other fields are being updated
        allowed_fields = {"credit_limit"}
        provided_fields = set(request.data.keys())
        if provided_fields - allowed_fields:
            return Response(
                {"error": f"Only credit_limit can be updated. Other fields are read-only."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update credit_limit
        credit_limit = request.data.get("credit_limit")
        if credit_limit is None:
            return Response(
                {"error": "credit_limit is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            credit_limit = float(credit_limit)
            if credit_limit < 0:
                return Response(
                    {"error": "credit_limit must be a positive number"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {"error": "credit_limit must be a valid number"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        instance.credit_limit = credit_limit
        instance.save()
        
        # Return updated instance with all calculated fields
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

