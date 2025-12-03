from django.urls import path
from financial.views.api import (
    ARAgeingSummaryView,
    ARDashboardView,
    InvoiceListCreateView,
    InvoiceRetrieveUpdateDestroyView,
    CustomerBalanceSummaryView,
    CustomerSegmentsView,
    CollectionPriorityView,
    
    CashFlowProjectionView,
    
    
    AnalyticsView,
    WriteOffsSummaryView,
    WriteOffCandidatesListView,
    WriteOffListCreateView,
    WriteOffSelectedView,
    AuditTrailSummaryView,
    AuditTrailListView,
)

app_name = "financial"

urlpatterns = [
    # Invoices
    path(
        "invoices/",
        InvoiceListCreateView.as_view(),
        name="invoice-list-create",
    ),
    path(
        "invoices/<uuid:id>/",
        InvoiceRetrieveUpdateDestroyView.as_view(),
        name="invoice-detail",
    ),
    # Customer Balance Summary
    path(
        "customers/balance-summary/",
        CustomerBalanceSummaryView.as_view(),
        name="customer-balance-summary",
    ),
    # Customer Segments
    path(
        "customers/segments/",
        CustomerSegmentsView.as_view(),
        name="customer-segments",
    ),
    # AR Ageing
    path(
        "ar-ageing-summary/",
        ARAgeingSummaryView.as_view(),
        name="ar-ageing-summary",
    ),
    # AR Dashboard
    path(
        "ar-dashboard/",
        ARDashboardView.as_view(),
        name="ar-dashboard",
    ),
    # Collection Priority
    path(
        "collection-priority/",
        CollectionPriorityView.as_view(),
        name="collection-priority",
    ),
     
    # Cash Flow
    path(
        "cash-flow/projection/",
        CashFlowProjectionView.as_view(),
        name="cash-flow-projection",
    ),
     
]
