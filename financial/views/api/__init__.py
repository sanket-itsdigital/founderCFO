from financial.views.api.ar_aging import ARAgeingSummaryView
from financial.views.api.collection_priority import CollectionPriorityView
from financial.views.api.cash_flow import CashFlowProjectionView
from financial.views.api.analytics import AnalyticsView
from financial.views.api.write_offs import (
    WriteOffsSummaryView,
    WriteOffCandidatesListView,
    WriteOffListCreateView,
    WriteOffSelectedView,
)
from financial.views.api.audit_trail import (
    AuditTrailSummaryView,
    AuditTrailListView,
)
from financial.views.api.invoice import (
    InvoiceListCreateView,
    InvoiceRetrieveUpdateDestroyView,
)
from financial.views.api.customer_balance import (
    CustomerBalanceSummaryView,
    CustomerBalanceDetailView,
)
from financial.views.api.customer_segments import CustomerSegmentsView
from financial.views.api.ar_dashboard import ARDashboardView

__all__ = [
    "ARAgeingSummaryView",
    "CreditListView",
    "CreditRetrieveUpdateView",
    "CollectionPriorityView",
    "CashFlowProjectionView",
    "AnalyticsView",
    "WriteOffsSummaryView",
    "WriteOffCandidatesListView",
    "WriteOffListCreateView",
    "WriteOffSelectedView",
    "AuditTrailSummaryView",
    "AuditTrailListView",
    "InvoiceListCreateView",
    "InvoiceRetrieveUpdateDestroyView",
    "CustomerBalanceSummaryView",
    "CustomerBalanceDetailView",
    "CustomerSegmentsView",
    "ARDashboardView",
]
