from django.urls import path

from hr.views.api.headcount_overview import HeadcountOverviewView
from hr.views.api.compensation_overview import CompensationOverviewView
from hr.views.api.analytics import AnalyticsView
from hr.views.api.dashboard import HRDashboardView
from hr.views.api.headcount_breakdown import (
    HeadcountByDepartmentView,
    HeadcountByLocationView,
    HeadcountEmployeesView,
)
from hr.views.api.import_headcount import HeadcountImportView
from hr.views.api.import_recruitment import RecruitmentImportView
from hr.views.api.import_budget import BudgetImportView
from hr.views.api.turnover import TurnoverView
from hr.views.api.recruitment import RecruitmentView
from hr.views.api.budget import BudgetView

app_name = "hr"
urlpatterns = [
    path(
        "dashboard/",
        HRDashboardView.as_view(),
        name="dashboard",
    ),
    path(
        "headcount/overview/",
        HeadcountOverviewView.as_view(),
        name="headcount-overview",
    ),
    path(
        "headcount/by-department/",
        HeadcountByDepartmentView.as_view(),
        name="headcount-by-department",
    ),
    path(
        "headcount/by-location/",
        HeadcountByLocationView.as_view(),
        name="headcount-by-location",
    ),
    path(
        "headcount/employees/",
        HeadcountEmployeesView.as_view(),
        name="headcount-employees",
    ),
    path(
        "headcount/import/",
        HeadcountImportView.as_view(),
        name="headcount-import",
    ),
    # Turnover API
    path(
        "turnover/",
        TurnoverView.as_view(),
        name="turnover",
    ),
    path(
        "recruitment/",
        RecruitmentView.as_view(),
        name="recruitment",
    ),
    path(
        "recruitment/import/",
        RecruitmentImportView.as_view(),
        name="recruitment-import",
    ),
    path(
        "compensation/overview/",
        CompensationOverviewView.as_view(),
        name="compensation-overview",
    ),
    path(
        "analytics/",
        AnalyticsView.as_view(),
        name="analytics",
    ),
    path(
        "budget/",
        BudgetView.as_view(),
        name="budget",
    ),
    path(
        "budget/import/",
        BudgetImportView.as_view(),
        name="budget-import",
    ),
]
