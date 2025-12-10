from sales.views.api.revenue_analytics import RevenueAnalyticsView
from sales.views.api.forecast import SalesForecastView
from sales.views.api.forecast_deal_detail import ForecastDealDetailView
from sales.views.api.forecast_by_rep import ForecastByRepView
from sales.views.api.forecast_accuracy import ForecastAccuracyView
from sales.views.api.team_performance import TeamPerformanceView
from sales.views.api.revenue_by_product import RevenueByProductView
from sales.views.api.team_summary import TeamSummaryView
from sales.views.api.team_performance_combined import TeamPerformanceCombinedView
from sales.views.api.sales_overview import SalesOverviewView
from sales.views.api.pipeline_overview import PipelineOverviewView
from sales.views.api.create_deal import CreateDealView
from sales.views.api.import_sales import SalesImportView

__all__ = [
    "SalesOverviewView",
    "PipelineOverviewView",
    "CreateDealView",
    "SalesImportView",
    "RevenueAnalyticsView",
    "SalesForecastView",
    "ForecastDealDetailView",
    "ForecastByRepView",
    "ForecastAccuracyView",
    "TeamPerformanceView",
    "RevenueByProductView",
    "TeamSummaryView",
    "TeamPerformanceCombinedView",
]
