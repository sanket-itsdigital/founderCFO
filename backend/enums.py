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


class SuccessLikelihoodChoices(TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"

class CompanyStatusChoices(TextChoices):
    ANNUAL = "Annual", "Annual"
    ANNUALLY = "Annually", "Annually"
    HALF_YEARLY = "Half-Yearly", "Half-Yearly"
    QUARTERLY = "Quarterly", "Quarterly"
    MONTHLY = "Monthly", "Monthly"
    WEEKLY = "Weekly", "Weekly"
    DAILY = "Daily", "Daily"
    
class ComplianceStatusChoices(TextChoices):
    OVERDUE = "Overdue", "Overdue"
    COMPLETED = "Completed", "Completed"
    PENDING = "Pending", "Pending"
    IN_PROGRESS = "In Progress", "In Progress"
    

class ActNameChoices(TextChoices):
    COMPANIES_ACT_2013 = "Companies Act, 2013", "Companies Act, 2013"
    FEMA = "FEMA", "FEMA"
    LLP_ACT_2008 = "LLP Act 2008", "LLP Act 2008"
    CGST_ACT_2017 = "CGST ACT 2017", "CGST ACT 2017"
    INCOME_TAX_ACT_1961 = "Income Tax Act, 1961", "Income Tax Act, 1961"
    ESI_ACT_1948 = "ESI Act 1948", "ESI Act 1948"
    EPF_ACT_1952 = "EPF Act 1952", "EPF Act 1952"
    SEBI_LODR = "SEBI (LODR)", "SEBI (LODR)"
    SEBI = "SEBI", "SEBI"
    MSME_ACT = "MSME Act", "MSME Act"
    
class NatureOfBusinessChoices(TextChoices):
    SAAS = "SaaS", "SaaS"
    ECOMMERCE = "Ecommerce", "Ecommerce"
    SERVICES_PROVIDER = "Services Provider", "Services Provider"
    MANUFACTURER = "Manufacturer", "Manufacturer"