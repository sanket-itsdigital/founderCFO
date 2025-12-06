from django.urls import path

from sales.views.api.revenue_analytics import RevenueAnalyticsView
from sales.views.api.forecast import SalesForecastView
from sales.views.api.forecast_deal_detail import ForecastDealDetailView
from sales.views.api.forecast_by_rep import ForecastByRepView
from sales.views.api.forecast_accuracy import ForecastAccuracyView
from sales.views.api.team_performance import TeamPerformanceView
from sales.views.api.revenue_by_product import RevenueByProductView
from sales.views.api.team_summary import TeamSummaryView
from sales.views.api.team_performance_combined import TeamPerformanceCombinedView

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
    # Team APIs
    path(
        "team/performance/",
        TeamPerformanceCombinedView.as_view(),
        name="team-performance",
    ),
    path(
        "team/performance/individual/",
        TeamPerformanceView.as_view(),
        name="team-performance-individual",
    ),
    path(
        "team/revenue-by-product/",
        RevenueByProductView.as_view(),
        name="revenue-by-product",
    ),
    path(
        "team/summary/",
        TeamSummaryView.as_view(),
        name="team-summary",
    ),
]
