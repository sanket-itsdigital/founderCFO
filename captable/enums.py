from django.db.models import TextChoices

class CapTableEventStatus(TextChoices):
    INCORPORATION = "Incorporation", "Incorporation"
    FOUNDERS_EQUITY = "Founders' Equity", "Founders' Equity"
    SEED_ROUND = "Seed Round", "Seed Round"
    SERIES_A = "Series A", "Series A"
    SERIES_B = "Series B", "Series B"
    SERIES_C = "Series C", "Series C"
    SERIES_D = "Series D", "Series D"
    ESOP_GRANT = "ESOP Grant", "ESOP Grant"
    SECONDARY_SALE = "Secondary Sale", "Secondary Sale"
    OTHER = "Other", "Other"
    
class ShareClassType(TextChoices):
    COMMON = "Common", "Common"
    PREFERENCE = "Preference", "Preference"
    DEBENTURE = "Debenture", "Debenture"
    ADVISORY = "Advisory", "Advisory"
    ESOP = "ESOP", "ESOP"
    
class InvestorType(TextChoices):
    FOUNDER = "Founder", "Founder"
    ANGEL_INVESTOR = "Angel Investor", "Angel Investor"
    VENTURE_CAPITAL = "Venture Capital", "Venture Capital"
    STRATEGIC_INVESTMENT = "Strategic Investment", "Strategic Investment"
    ADVISOR = "Advisor", "Advisor"
    EMPLOYEE = "Employee", "Employee"
    OTHER = "Other", "Other"