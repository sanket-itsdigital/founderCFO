from revenue.views.api.register import (
    AllInvoicesView,
    CustomerRevenueView,
    CustomerInvoicesView,
    ProductRevenueView,
    ProductInvoicesView,
    SalespersonRevenueView,
    SalespersonInvoicesView,
    ServiceRevenueView,
    ServiceInvoicesView,
)
from revenue.views.api.import_invoices import RevenueInvoiceImportView
from revenue.views.api.analytics import (
    TrendsView,
    CustomersView,
    SalespersonView,
    ProductsView,
    BranchView,
    GeographicView,
    GSTOverviewView,
    RevenueDashboardView,
)

__all__ = [
    "AllInvoicesView",
    "CustomerRevenueView",
    "CustomerInvoicesView",
    "ProductRevenueView",
    "ProductInvoicesView",
    "SalespersonRevenueView",
    "SalespersonInvoicesView",
    "ServiceRevenueView",
    "ServiceInvoicesView",
    "RevenueInvoiceImportView",
    "TrendsView",
    "CustomersView",
    "SalespersonView",
    "ProductsView",
    "BranchView",
    "GeographicView",
    "GSTOverviewView",
    "RevenueDashboardView",
]
