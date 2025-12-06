from django.urls import path

from sales.views.api.revenue_analytics import RevenueAnalyticsView
from sales.views.api.forecast import SalesForecastView
from sales.views.api.forecast_deal_detail import ForecastDealDetailView
from sales.views.api.forecast_by_rep import ForecastByRepView
from sales.views.api.forecast_accuracy import ForecastAccuracyView

app_name = "sales"

urlpatterns = [
    # Revenue Analytics API
    path(
        "revenue-analytics/",
        RevenueAnalyticsView.as_view(),
        name="revenue-analytics",
    ),
    # Sales Forecast APIs
    path(
        "forecast/",
        SalesForecastView.as_view(),
        name="sales-forecast",
    ),
    path(
        "forecast/deal-detail/",
        ForecastDealDetailView.as_view(),
        name="forecast-deal-detail",
    ),
    path(
        "forecast/by-rep/",
        ForecastByRepView.as_view(),
        name="forecast-by-rep",
    ),
    path(
        "forecast/accuracy/",
        ForecastAccuracyView.as_view(),
        name="forecast-accuracy",
    ),
]
