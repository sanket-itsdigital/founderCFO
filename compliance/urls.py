from django.urls import path
from compliance.views.api import (
    ComplianceTaskListCreateView,
    ComplianceTaskRetrieveUpdateDestroyView,
    ComplianceTaskSelectionView,
    ComplianceTaskDropdownView,
    ComplianceTaskSelectedView,
    CompliancePaymentListCreateView,
    CompliancePaymentRetrieveUpdateDestroyView,
    ActWiseSummaryView,
    ExposureAnalysisView,
    ComplianceDashboardView,
)

app_name = "compliance"

urlpatterns = [
    # Task APIs
    path(
        "tasks/",
        ComplianceTaskListCreateView.as_view(),
        name="task-list-create",
    ),
    path(
        "tasks/<uuid:pk>/",
        ComplianceTaskRetrieveUpdateDestroyView.as_view(),
        name="task-detail",
    ),
    path(
        "tasks/select/",
        ComplianceTaskSelectionView.as_view(),
        name="task-selection",
    ),
    path(
        "tasks/dropdown/",
        ComplianceTaskDropdownView.as_view(),
        name="task-dropdown",
    ),
    path(
        "tasks/selected/",
        ComplianceTaskSelectedView.as_view(),
        name="task-selected",
    ),
    # Payment APIs
    path(
        "payments/",
        CompliancePaymentListCreateView.as_view(),
        name="payment-list-create",
    ),
    path(
        "payments/<uuid:pk>/",
        CompliancePaymentRetrieveUpdateDestroyView.as_view(),
        name="payment-detail",
    ),
    # Summary and Analysis APIs
    path(
        "act-wise-summary/",
        ActWiseSummaryView.as_view(),
        name="act-wise-summary",
    ),
    path(
        "exposure-analysis/",
        ExposureAnalysisView.as_view(),
        name="exposure-analysis",
    ),
    path(
        "dashboard/",
        ComplianceDashboardView.as_view(),
        name="dashboard",
    ),
]
