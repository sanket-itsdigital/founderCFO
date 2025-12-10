from django.urls import path
from revenue.views.api.register import (
    AllInvoicesView,
    InvoiceDetailView,
    CustomerRevenueView,
    CustomerInvoicesView,
    ProductRevenueView,
    ProductInvoicesView,
    SalespersonRevenueView,
    SalespersonInvoicesView,
    ServiceRevenueView,
    ServiceInvoicesView,
)
from revenue.views.api.import_invoices import RevenueInvoiceImportView

app_name = "revenue"

urlpatterns = [
    # Register Section - All Invoices
    path(
        "register/invoices/",
        AllInvoicesView.as_view(),
        name="all-invoices",
    ),
    path(
        "register/invoices/<uuid:id>/",
        InvoiceDetailView.as_view(),
        name="invoice-detail",
    ),
    path(
        "register/invoices/import/",
        RevenueInvoiceImportView.as_view(),
        name="import-invoices",
    ),
    # Register Section - By Customer
    path(
        "register/customers/",
        CustomerRevenueView.as_view(),
        name="customer-revenue",
    ),
    path(
        "register/customers/<str:customer_name>/invoices/",
        CustomerInvoicesView.as_view(),
        name="customer-invoices",
    ),
    # Register Section - By Product
    path(
        "register/products/",
        ProductRevenueView.as_view(),
        name="product-revenue",
    ),
    path(
        "register/products/<str:product_name>/invoices/",
        ProductInvoicesView.as_view(),
        name="product-invoices",
    ),
    # Register Section - By Salesperson
    path(
        "register/salespersons/",
        SalespersonRevenueView.as_view(),
        name="salesperson-revenue",
    ),
    path(
        "register/salespersons/<str:salesperson>/invoices/",
        SalespersonInvoicesView.as_view(),
        name="salesperson-invoices",
    ),
    # Register Section - By Service
    path(
        "register/services/",
        ServiceRevenueView.as_view(),
        name="service-revenue",
    ),
    path(
        "register/services/<str:service_type>/invoices/",
        ServiceInvoicesView.as_view(),
        name="service-invoices",
    ),
]
