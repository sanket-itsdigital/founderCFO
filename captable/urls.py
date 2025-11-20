from django.urls import path

from captable.views.api import (
    CapTableEventDetailView,
    CapTableEventDocumentView,
    CapTableEventListCreateView,
    CapTableEventTransactionCreateView,
    CapTableEventTransactionDetailView,
    CapTableSummaryView,
    CapitalizationTableDetailView,
    CapitalizationTableListCreateView,
    ShareHolderListView,
    ShareholderDetailView,
    ShareholderListCreateView,
)

app_name = "captable"

urlpatterns = [
    path("events/", CapTableEventListCreateView.as_view(), name="captable-events-list"),
    path(
        "events/<uuid:pk>/",
        CapTableEventDetailView.as_view(),
        name="captable-events-detail",
    ),
    path(
        "events/<uuid:pk>/documents/",
        CapTableEventDocumentView.as_view(),
        name="captable-events-documents",
    ),
    path(
        "events/transactions/",
        CapTableEventTransactionCreateView.as_view(),
        name="captable-events-transactions",
    ),
    path(
        "events/transactions/<uuid:pk>/",
        CapTableEventTransactionDetailView.as_view(),
        name="captable-events-transactions-detail",
    ),
    path(
        "shareholders/",
        ShareholderListCreateView.as_view(),
        name="captable-shareholders-list",
    ),
    path(
        "shareholders/<uuid:pk>/",
        ShareholderDetailView.as_view(),
        name="captable-shareholders-detail",
    ),
    path(
        "transactions/",
        CapitalizationTableListCreateView.as_view(),
        name="captable-transactions-list",
    ),
    path(
        "transactions/<uuid:pk>/",
        CapitalizationTableDetailView.as_view(),
        name="captable-transactions-detail",
    ),
    path("summary/", CapTableSummaryView.as_view(), name="summary"),
    path("shareholders-list/", ShareHolderListView.as_view(), name="shareholder-list"),
]
