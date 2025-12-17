from django.urls import path
from expense.views.api.bills import (
    BillListCreateView,
    BillRetrieveUpdateDestroyView,
)
from expense.views.api.import_bills import BillImportView
from expense.views.api.vendors import (
    VendorsView,
    VendorBillsView,
)
from expense.views.api.categories import (
    CategoriesView,
    CategoryBillsView,
)
from expense.views.api.departments import (
    DepartmentsView,
    DepartmentBillsView,
)
from expense.views.api.branches import (
    BranchesView,
    BranchBillsView,
)
from expense.views.api.analytics import (
    AnalyticsOverviewView,
    AnalyticsTrendsView,
    AnalyticsByBranchView,
)
from expense.views.api.gst_summary import GSTSummaryView
from expense.views.api.recurring import (
    RecurringExpenseListCreateView,
    RecurringExpenseRetrieveUpdateDestroyView,
    RecurringExpenseChoicesView,
)

app_name = "expense"

urlpatterns = [
    # Bills - List, Create, Update, Delete
    path(
        "bills/",
        BillListCreateView.as_view(),
        name="bill-list-create",
    ),
    path(
        "bills/<uuid:id>/",
        BillRetrieveUpdateDestroyView.as_view(),
        name="bill-detail",
    ),
    # Bills - Import from Excel
    path(
        "bills/import/",
        BillImportView.as_view(),
        name="bill-import",
    ),
    # Vendors - Combined API (Summary, Top Vendors, All Vendors)
    path(
        "vendors/",
        VendorsView.as_view(),
        name="vendors",
    ),
    path(
        "vendors/<uuid:vendor_id>/bills/",
        VendorBillsView.as_view(),
        name="vendor-bills",
    ),
    # Categories - Combined API (Summary, Distribution, Top Sub-Categories, All Categories)
    path(
        "categories/",
        CategoriesView.as_view(),
        name="categories",
    ),
    path(
        "categories/<str:category_name>/bills/",
        CategoryBillsView.as_view(),
        name="category-bills",
    ),
    # Departments - Combined API (Summary, Spend by Department, Distribution, All Departments)
    path(
        "departments/",
        DepartmentsView.as_view(),
        name="departments",
    ),
    path(
        "departments/<str:department_name>/bills/",
        DepartmentBillsView.as_view(),
        name="department-bills",
    ),
    # Branches - Combined API (Summary, All Branches)
    path(
        "branches/",
        BranchesView.as_view(),
        name="branches",
    ),
    path(
        "branches/<str:branch_name>/bills/",
        BranchBillsView.as_view(),
        name="branch-bills",
    ),
    # Analytics - Overview
    path(
        "analytics/overview/",
        AnalyticsOverviewView.as_view(),
        name="analytics-overview",
    ),
    # Analytics - Trends
    path(
        "analytics/trends/",
        AnalyticsTrendsView.as_view(),
        name="analytics-trends",
    ),
    # Analytics - By Branch
    path(
        "analytics/by-branch/",
        AnalyticsByBranchView.as_view(),
        name="analytics-by-branch",
    ),
    # GST Summary
    path(
        "gst-summary/",
        GSTSummaryView.as_view(),
        name="gst-summary",
    ),
    # Recurring Expenses - Combined API (Summary + List, Create)
    path(
        "recurring/",
        RecurringExpenseListCreateView.as_view(),
        name="recurring-list-create",
    ),
    # Recurring Expenses - Choices (for dropdowns)
    path(
        "recurring/choices/",
        RecurringExpenseChoicesView.as_view(),
        name="recurring-choices",
    ),
    # Recurring Expenses - Retrieve, Update, Delete
    path(
        "recurring/<uuid:id>/",
        RecurringExpenseRetrieveUpdateDestroyView.as_view(),
        name="recurring-detail",
    ),
]
