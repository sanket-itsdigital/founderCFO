from django.db.models import TextChoices


class InvoicesPaymentTerms(TextChoices):
    COD = "COD", "COD"
    NET_7 = "Net 7", "Net 7"
    NET_15 = "Net 15", "Net 15"
    NET_30 = "Net 30", "Net 30"
    NET_45 = "Net 45", "Net 45"
    NET_60 = "Net 60", "Net 60"
    NET_90 = "Net 90", "Net 90"


class InvoicesCategoryChoices(TextChoices):
    PRODUCTS_SALES = "Products Sales", "Products Sales"
    SERVICES = "Services", "Services"
    SUBSCRIPTIONS = "Subscriptions", "Subscriptions"
    CONSULTING = "Consulting", "Consulting"
    MAINTENANCE = "Maintenance", "Maintenance"
    OTHER = "Other", "Other"


class InvoicesStatusChoices(TextChoices):
    DRAFT = "Draft", "Draft"
    PENDING = "Pending", "Pending"
    PARTIAL = "Partial", "Partial"
    PAID = "Paid", "Paid"
    OVERDUE = "Overdue", "Overdue"
    CANCELLED = "Cancelled", "Cancelled"
    BAD_DEBT = "Bad Debt", "Bad Debt"


class PaymentStatusChoices(TextChoices):
    PENDING = "Pending", "Pending"
    PARTIAL = "Partial", "Partial"
    PAID = "Paid", "Paid"
    OVERDUE = "Overdue", "Overdue"
    CANCELLED = "Cancelled", "Cancelled"


class RiskLevelChoices(TextChoices):
    LOW = "Low", "Low"
    MEDIUM = "Medium", "Medium"
    HIGH = "High", "High"


# Reminders Enums
class ReminderStatusChoices(TextChoices):
    PENDING = "Pending", "Pending"
    SENT = "Sent", "Sent"
    CANCELLED = "Cancelled", "Cancelled"


class ReminderTriggerTypeChoices(TextChoices):
    BEFORE_DUE_DATE = "Before Due Date", "Before Due Date"
    AFTER_DUE_DATE = "After Due Date", "After Due Date"
    ON_DUE_DATE = "On Due Date", "On Due Date"


# Dunning Enums
class DunningStageChoices(TextChoices):
    FRIENDLY = "Friendly", "Friendly"  # 1-14 days
    FIRM = "Firm", "Firm"  # 15-29 days
    URGENT = "Urgent", "Urgent"  # 30-59 days
    FINAL = "Final", "Final"  # 60+ days


# Disputes Enums
class DisputeReasonChoices(TextChoices):
    PRICING_DISCREPANCY = "Pricing discrepancy", "Pricing discrepancy"
    QUANTITY_MISMATCH = "Quantity mismatch", "Quantity mismatch"
    DAMAGED_GOODS = "Damaged goods", "Damaged goods"
    SERVICE_NOT_DELIVERED = "Service not delivered", "Service not delivered"
    DUPLICATE_INVOICE = "Duplicate invoice", "Duplicate invoice"
    INCORRECT_BILLING_ADDRESS = "Incorrect billing address", "Incorrect billing address"
    TAX_CALCULATION_ERROR = "Tax calculation error", "Tax calculation error"
    UNAUTHORIZED_CHARGES = "Unauthorized charges", "Unauthorized charges"
    OTHER = "Other", "Other"


class DisputeStatusChoices(TextChoices):
    OPEN = "Open", "Open"
    IN_REVIEW = "In Review", "In Review"
    RESOLVED = "Resolved", "Resolved"
    CLOSED = "Closed", "Closed"


class DisputePriorityChoices(TextChoices):
    LOW = "Low", "Low"
    MEDIUM = "Medium", "Medium"
    HIGH = "High", "High"
    URGENT = "Urgent", "Urgent"


# Payment Plans Enums
class PaymentPlanStatusChoices(TextChoices):
    ACTIVE = "Active", "Active"
    COMPLETED = "Completed", "Completed"
    CANCELLED = "Cancelled", "Cancelled"
    DEFAULTED = "Defaulted", "Defaulted"


class PaymentFrequencyChoices(TextChoices):
    WEEKLY = "Weekly", "Weekly"
    BI_WEEKLY = "Bi-weekly", "Bi-weekly"
    MONTHLY = "Monthly", "Monthly"
    QUARTERLY = "Quarterly", "Quarterly"
    ANNUALLY = "Annually", "Annually"


class InstallmentStatusChoices(TextChoices):
    PENDING = "Pending", "Pending"
    PAID = "Paid", "Paid"
    OVERDUE = "Overdue", "Overdue"
    SKIPPED = "Skipped", "Skipped"

class BillsStatusChoices(TextChoices):
    PENDING = "Pending", "Pending"
    PARTIAL = "Partial", "Partial"
    PAID = "Paid", "Paid"
    OVERDUE = "Overdue", "Overdue"
    CANCELLED = "Cancelled", "Cancelled"