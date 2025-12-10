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
from revenue.views.api.analytics import (
    TrendsYearOverYearView,
    TrendsServiceKPIsView,
    CustomersOverviewView,
    CustomersCohortAnalysisView,
    SalespersonOverviewView,
    SalespersonPerformanceView,
    ProductsOverviewView,
    ProductsDetailsView,
    BranchOverviewView,
    BranchPerformanceView,
    GeographicOverviewView,
    GeographicDetailsView,
    GSTOverviewView,
)

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
    # Analytics Section - Trends
    path(
        "analytics/trends/year-over-year/",
        TrendsYearOverYearView.as_view(),
        name="trends-year-over-year",
    ),
    path(
        "analytics/trends/service-kpis/",
        TrendsServiceKPIsView.as_view(),
        name="trends-service-kpis",
    ),
    # Analytics Section - Customers
    path(
        "analytics/customers/overview/",
        CustomersOverviewView.as_view(),
        name="customers-overview",
    ),
    path(
        "analytics/customers/cohort-analysis/",
        CustomersCohortAnalysisView.as_view(),
        name="customers-cohort-analysis",
    ),
    # Analytics Section - Salesperson
    path(
        "analytics/salesperson/overview/",
        SalespersonOverviewView.as_view(),
        name="salesperson-overview",
    ),
    path(
        "analytics/salesperson/performance/",
        SalespersonPerformanceView.as_view(),
        name="salesperson-performance",
    ),
    # Analytics Section - Products
    path(
        "analytics/products/overview/",
        ProductsOverviewView.as_view(),
        name="products-overview",
    ),
    path(
        "analytics/products/details/",
        ProductsDetailsView.as_view(),
        name="products-details",
    ),
    # Analytics Section - Branch
    path(
        "analytics/branch/overview/",
        BranchOverviewView.as_view(),
        name="branch-overview",
    ),
    path(
        "analytics/branch/performance/",
        BranchPerformanceView.as_view(),
        name="branch-performance",
    ),
    # Analytics Section - Geographic
    path(
        "analytics/geographic/overview/",
        GeographicOverviewView.as_view(),
        name="geographic-overview",
    ),
    path(
        "analytics/geographic/details/",
        GeographicDetailsView.as_view(),
        name="geographic-details",
    ),
    # Analytics Section - GST
    path(
        "analytics/gst/overview/",
        GSTOverviewView.as_view(),
        name="gst-overview",
    ),
]
