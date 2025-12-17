from django.urls import path
from expense.views.api.bills import (
    BillListCreateView,
    BillRetrieveUpdateDestroyView,
)
from expense.views.api.import_bills import BillImportView

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
]
