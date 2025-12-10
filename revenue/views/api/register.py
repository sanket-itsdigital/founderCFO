from decimal import Decimal
from django.db.models import Count, Sum, Avg, Q
from django.db.models.functions import Coalesce
from rest_framework import status, generics
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from revenue.models.invoice import Invoice
from revenue.serializers.invoice import (
    InvoiceSerializer,
    InvoiceCreateSerializer,
    InvoiceUpdateSerializer,
)
from revenue.serializers.register import (
    CustomerRevenueSerializer,
    ProductRevenueSerializer,
    SalespersonRevenueSerializer,
    ServiceRevenueSerializer,
)
from sales.views.api.utils import get_company_from_request


class AllInvoicesView(generics.ListCreateAPIView):
    """API for All Invoices - List and Create"""

    permission_classes = [IsAuthenticated]
    serializer_class = InvoiceSerializer

    def get_queryset(self):
        """Filter invoices by company"""
        company = get_company_from_request(self.request)
        if not company:
            return Invoice.objects.none()
        return Invoice.objects.filter(company=company).order_by("-invoice_date")

    def get_serializer_class(self):
        """Use create serializer for POST"""
        if self.request.method == "POST":
            return InvoiceCreateSerializer
        return InvoiceSerializer

    def perform_create(self, serializer):
        """Set company when creating invoice"""
        company = get_company_from_request(self.request)
        if not company:
            raise ValidationError({"error": "Company not found"})
        serializer.save(company=company)


class InvoiceDetailView(generics.RetrieveUpdateDestroyAPIView):
    """API for Invoice Detail - Get, Update, Delete"""

    permission_classes = [IsAuthenticated]
    serializer_class = InvoiceSerializer
    lookup_field = "id"

    def get_queryset(self):
        """Filter invoices by company"""
        company = get_company_from_request(self.request)
        if not company:
            return Invoice.objects.none()
        return Invoice.objects.filter(company=company)

    def get_serializer_class(self):
        """Use update serializer for PATCH/PUT"""
        if self.request.method in ["PATCH", "PUT"]:
            return InvoiceUpdateSerializer
        return InvoiceSerializer


class CustomerRevenueView(APIView):
    """API for Revenue by Customer"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get revenue aggregated by customer"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Aggregate revenue by customer
        customer_data = (
            Invoice.objects.filter(company=company)
            .values("customer_name")
            .annotate(
                invoices_count=Count("id"),
                revenue=Coalesce(Sum("total_amount"), Decimal("0.00")),
                avg_value=Coalesce(Avg("total_amount"), Decimal("0.00")),
            )
            .order_by("-revenue")
        )

        customers = []
        for item in customer_data:
            customers.append(
                {
                    "customer_name": item["customer_name"],
                    "invoices_count": item["invoices_count"],
                    "revenue": item["revenue"] or Decimal("0.00"),
                    "avg_value": item["avg_value"] or Decimal("0.00"),
                }
            )

        serializer = CustomerRevenueSerializer(customers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CustomerInvoicesView(APIView):
    """API for Customer-related Invoices (drill-down)"""

    permission_classes = [IsAuthenticated]

    def get(self, request, customer_name):
        """Get all invoices for a specific customer"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Decode customer name from URL
        from urllib.parse import unquote

        customer_name = unquote(customer_name)

        invoices = Invoice.objects.filter(
            company=company, customer_name=customer_name
        ).order_by("-invoice_date")

        # Calculate summary
        summary = invoices.aggregate(
            total_invoices=Count("id"),
            total_revenue=Coalesce(Sum("total_amount"), Decimal("0.00")),
            total_with_gst=Coalesce(
                Sum("total_amount"), Decimal("0.00")
            ),  # Assuming total includes GST
        )

        serializer = InvoiceSerializer(invoices, many=True)
        return Response(
            {
                "customer_name": customer_name,
                "summary": {
                    "invoices": summary["total_invoices"],
                    "revenue": summary["total_revenue"] or Decimal("0.00"),
                    "total_incl_gst": summary["total_with_gst"] or Decimal("0.00"),
                },
                "invoices": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class ProductRevenueView(APIView):
    """API for Revenue by Product"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get revenue aggregated by product"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Aggregate revenue by product
        product_data = (
            Invoice.objects.filter(company=company)
            .values("product_name")
            .annotate(
                invoices_count=Count("id"),
                quantity=Coalesce(Sum("quantity"), Decimal("0.00")),
                revenue=Coalesce(Sum("total_amount"), Decimal("0.00")),
            )
            .order_by("-revenue")
        )

        products = []
        for item in product_data:
            products.append(
                {
                    "product_name": item["product_name"],
                    "invoices_count": item["invoices_count"],
                    "quantity": item["quantity"] or Decimal("0.00"),
                    "revenue": item["revenue"] or Decimal("0.00"),
                }
            )

        serializer = ProductRevenueSerializer(products, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ProductInvoicesView(APIView):
    """API for Product-related Invoices (drill-down)"""

    permission_classes = [IsAuthenticated]

    def get(self, request, product_name):
        """Get all invoices for a specific product"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Decode product name from URL
        from urllib.parse import unquote

        product_name = unquote(product_name)

        invoices = Invoice.objects.filter(
            company=company, product_name=product_name
        ).order_by("-invoice_date")

        serializer = InvoiceSerializer(invoices, many=True)
        return Response(
            {
                "product_name": product_name,
                "invoices": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class SalespersonRevenueView(APIView):
    """API for Revenue by Salesperson"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get revenue aggregated by salesperson"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Aggregate revenue by salesperson
        salesperson_data = (
            Invoice.objects.filter(company=company, salesperson__isnull=False)
            .exclude(salesperson="")
            .values("salesperson")
            .annotate(
                invoices_count=Count("id"),
                customers_count=Count("customer_name", distinct=True),
                revenue=Coalesce(Sum("total_amount"), Decimal("0.00")),
                avg_deal=Coalesce(Avg("total_amount"), Decimal("0.00")),
            )
            .order_by("-revenue")
        )

        # Calculate total revenue for share calculation
        total_revenue = Invoice.objects.filter(company=company).aggregate(
            total=Coalesce(Sum("total_amount"), Decimal("0.00"))
        )["total"] or Decimal("0.00")

        salespersons = []
        for item in salesperson_data:
            revenue = item["revenue"] or Decimal("0.00")
            share = (
                (revenue / total_revenue * Decimal("100"))
                if total_revenue > 0
                else Decimal("0.00")
            )

            salespersons.append(
                {
                    "salesperson": item["salesperson"],
                    "invoices_count": item["invoices_count"],
                    "customers_count": item["customers_count"],
                    "revenue": revenue,
                    "avg_deal": item["avg_deal"] or Decimal("0.00"),
                    "share": share,
                }
            )

        # Calculate KPIs
        total_salespersons = len(salespersons)
        top_performer = salespersons[0] if salespersons else None
        avg_deal_size = (
            sum([s["avg_deal"] for s in salespersons]) / total_salespersons
            if total_salespersons > 0
            else Decimal("0.00")
        )
        avg_per_rep = (
            total_revenue / Decimal(str(total_salespersons))
            if total_salespersons > 0
            else Decimal("0.00")
        )

        serializer = SalespersonRevenueSerializer(salespersons, many=True)
        return Response(
            {
                "kpis": {
                    "total_salespersons": total_salespersons,
                    "top_performer": {
                        "name": top_performer["salesperson"] if top_performer else None,
                        "revenue": (
                            top_performer["revenue"]
                            if top_performer
                            else Decimal("0.00")
                        ),
                    },
                    "avg_deal_size": avg_deal_size,
                    "avg_per_rep": avg_per_rep,
                },
                "salespersons": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class SalespersonInvoicesView(APIView):
    """API for Salesperson-related Invoices (drill-down)"""

    permission_classes = [IsAuthenticated]

    def get(self, request, salesperson):
        """Get all invoices for a specific salesperson"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Decode salesperson name from URL
        from urllib.parse import unquote

        salesperson = unquote(salesperson)

        invoices = Invoice.objects.filter(
            company=company, salesperson=salesperson
        ).order_by("-invoice_date")

        serializer = InvoiceSerializer(invoices, many=True)
        return Response(
            {
                "salesperson": salesperson,
                "invoices": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class ServiceRevenueView(APIView):
    """API for Revenue by Service/Category"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get revenue aggregated by service type"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Aggregate revenue by service type
        service_data = (
            Invoice.objects.filter(company=company, service_type__isnull=False)
            .exclude(service_type="")
            .values("service_type")
            .annotate(
                invoices_count=Count("id"),
                customers_count=Count("customer_name", distinct=True),
                revenue=Coalesce(Sum("total_amount"), Decimal("0.00")),
            )
            .order_by("-revenue")
        )

        # Calculate total revenue for share calculation
        total_revenue = Invoice.objects.filter(company=company).aggregate(
            total=Coalesce(Sum("total_amount"), Decimal("0.00"))
        )["total"] or Decimal("0.00")

        services = []
        for item in service_data:
            revenue = item["revenue"] or Decimal("0.00")
            share = (
                (revenue / total_revenue * Decimal("100"))
                if total_revenue > 0
                else Decimal("0.00")
            )

            services.append(
                {
                    "service_type": item["service_type"],
                    "invoices_count": item["invoices_count"],
                    "customers_count": item["customers_count"],
                    "revenue": revenue,
                    "share": share,
                }
            )

        # Calculate KPIs
        total_categories = len(services)
        top_category = services[0] if services else None
        avg_revenue_per_category = (
            total_revenue / Decimal(str(total_categories))
            if total_categories > 0
            else Decimal("0.00")
        )

        serializer = ServiceRevenueSerializer(services, many=True)
        return Response(
            {
                "kpis": {
                    "total_categories": total_categories,
                    "top_category": {
                        "name": top_category["service_type"] if top_category else None,
                        "share": (
                            top_category["share"] if top_category else Decimal("0.00")
                        ),
                    },
                    "avg_revenue_per_category": avg_revenue_per_category,
                },
                "services": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class ServiceInvoicesView(APIView):
    """API for Service/Category-related Invoices (drill-down)"""

    permission_classes = [IsAuthenticated]

    def get(self, request, service_type):
        """Get all invoices for a specific service type"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"error": "Company not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Decode service type from URL
        from urllib.parse import unquote

        service_type = unquote(service_type)

        invoices = Invoice.objects.filter(
            company=company, service_type=service_type
        ).order_by("-invoice_date")

        serializer = InvoiceSerializer(invoices, many=True)
        return Response(
            {
                "service_type": service_type,
                "invoices": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
