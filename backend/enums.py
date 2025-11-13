from django.db.models import TextChoices


class VerificationStatusChoices(TextChoices):
    PENDING = "Pending", "Pending"
    ACCEPTED = "Accepted", "Accepted"
    REJECTED = "Rejected", "Rejected"


class UserRoleChoices(TextChoices):
    ACCOUNTANT = "Accountant", "Accountant"
    INVESTOR = "Investor", "Investor"
    FOUNDER = "Founder", "Founder"
    CFO = "CFO", "CFO"


class CaseTypeChoices(TextChoices):
    GST = "GST", "GST"
    INCOME_TAX = "Income Tax", "Income Tax"
    PROFESSIONAL_TAX = "Professional Tax", "Professional Tax"
    ESI = "ESI", "ESI"
    PF = "PF", "PF"
    LABOUR = "Labour", "Labour"
    COMMERCIAL = "Commercial", "Commercial"
    OTHER = "Other", "Other"


class CaseStatusChoices(TextChoices):
    OPEN = "open", "open"
    IN_PROGRESS = "in progress", "in progress"
    APPEALED = "appealed", "appealed"
    STAYED = "stayed", "stayed"
    RESOLVED = "resolved", "resolved"
    CLOSED = "closed", "closed"
    DISMISSED = "dismissed", "dismissed"


class RiskLevelChoices(TextChoices):
    LOW = "low", "low"
    MEDIUM = "medium", "medium"
    HIGH = "high", "high"
    CRITICAL = "critical", "critical"
