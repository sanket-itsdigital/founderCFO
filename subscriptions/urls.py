from django.urls import path

from subscriptions.views import (
    CompanySubscriptionStatusView,
    SubscriptionPlanListView,
    SubscriptionPurchaseView,
)

app_name = "subscriptions"

urlpatterns = [
    path("plans/", SubscriptionPlanListView.as_view(), name="plan-list"),
    path(
        "status/",
        CompanySubscriptionStatusView.as_view(),
        name="subscription-status",
    ),
    path(
        "purchase/",
        SubscriptionPurchaseView.as_view(),
        name="subscription-purchase",
    ),
]
