from django.urls import path, include
from rest_framework.routers import DefaultRouter

from captable.views.api import (
    CapTableEventViewSet,
    CapTableSummaryView,
    CapitalizationTableViewSet,
    ShareholderViewSet,
)

app_name = "captable"

router = DefaultRouter()
router.register("events", CapTableEventViewSet, basename="captable-events")
router.register("shareholders", ShareholderViewSet, basename="captable-shareholders")
router.register(
    "transactions", CapitalizationTableViewSet, basename="captable-transactions"
)

urlpatterns = [
    path("", include(router.urls)),
    path("summary/", CapTableSummaryView.as_view(), name="summary"),
]
