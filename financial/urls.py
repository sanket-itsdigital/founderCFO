from django.urls import path
from financial.views.api import (
    ARAgeingSummaryView,
    ARDashboardView,
    InvoiceListCreateView,
    InvoiceRetrieveUpdateDestroyView,
    CustomerBalanceSummaryView,
    CustomerBalanceDetailView,
    CustomerSegmentsView,
    CollectionPriorityView,
    BillListCreateView,
    BillRetrieveUpdateDestroyView,
    APAgeingSummaryView,
    VendorBalanceSummaryView,
    PaymentPriorityQueueView,
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
    path(
        "customers/balance-summary/<str:customer_name>/",
        CustomerBalanceDetailView.as_view(),
        name="customer-balance-detail",
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
    # Accounts Payable
    path(
        "payable/bills/",
        BillListCreateView.as_view(),
        name="bill-list-create",
    ),
    path(
        "payable/bills/<uuid:id>/",
        BillRetrieveUpdateDestroyView.as_view(),
        name="bill-detail",
    ),
    path(
        "payable/ap-ageing-summary/",
        APAgeingSummaryView.as_view(),
        name="ap-ageing-summary",
    ),
    path(
        "payable/vendors/balance-summary/",
        VendorBalanceSummaryView.as_view(),
        name="vendor-balance-summary",
    ),
    path(
        "payable/payment-priority/",
        PaymentPriorityQueueView.as_view(),
        name="payment-priority-queue",
    ),
]
