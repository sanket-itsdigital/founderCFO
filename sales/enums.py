from django.db.models import TextChoices


class SalesStageStatusChoices(TextChoices):
    DISCOVERY = "Discovery", "Discovery"
    QUALIFICATION = "Qualification", "Qualification"
    PROPOSAL = "Proposal", "Proposal"
    NEGOTIATION = "Negotiation", "Negotiation"
    CLOSED_WON = "Closed Won", "Closed Won"
    CLOSED_LOST = "Closed Lost", "Closed Lost"
    UNQUALIFIED = "Unqualified", "Unqualified"


class SalesSourceChoices(TextChoices):
    OUTBOUND = "Outbound", "Outbound"
    INBOUND = "Inbound", "Inbound"
    REFERRAL = "Referral", "Referral"
    EVENT = "Event", "Event"
    PARTNER = "Partner", "Partner"
    SOCIAL_MEDIA = "Social Media", "Social Media"
    OTHER = "Other", "Other"


class SalesNextStepChoices(TextChoices):
    COMPLETED = "Completed", "Completed"
    LOST = "Lost", "Lost"
    CONTRACT_REVIEW = "Contract Review", "Contract Review"
    LEGAL_REVIEW = "Legal Review", "Legal Review"
    PRICING_DISCUSSION = "Pricing Discussion", "Pricing Discussion"
    FINAL_APPROVAL = "Final Approval", "Final Approval"
    PROPOSAL_PRESENTATION = "Proposal Presentation", "Proposal Presentation"
    TECHNICAL_VALIDATION = "Technical Validation", "Technical Validation"
    ROI_PRESENTATION = "ROI Presentation", "ROI Presentation"
    DEMO_FOLLOW_UP = "Demo Follow-up", "Demo Follow-up"
    DISCOVERY_CALL = "Discovery Call", "Discovery Call"
    TECHNICAL_SCOPING = "Technical Scoping", "Technical Scoping"
    STAKEHOLDER_MAPPING = "Stakeholder Mapping", "Stakeholder Mapping"
    INITIAL_ASSESSMENT = "Initial Assessment", "Initial Assessment"
    INTRO_MEETING_SCHEDULED = "Intro Meeting Scheduled", "Intro Meeting Scheduled"
    DEMO_SCHEDULED = "Demo Scheduled", "Demo Scheduled"
    INITIAL_CONTACT = "Initial Contact", "Initial Contact"
    QUALIFICATION_CALL = "Qualification Call", "Qualification Call"

class SalesProductChoices(TextChoices):
    ENTERPRISE = "Enterprise", "Enterprise"
    PRO = "Pro", "Pro"
    STARTER = "Starter", "Starter"