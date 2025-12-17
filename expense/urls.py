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
]
