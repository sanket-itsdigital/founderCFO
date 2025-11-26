from django.db.models import TextChoices


class Frequency(TextChoices):
    MONTHLY = "Monthly", "Monthly"
    QUARTERLY = "Quarterly", "Quarterly"
    HALF_YEARLY = "Half-yearly", "Half-yearly"
    ANNUALLY = "Annually", "Annually"


class ConsequencesType(TextChoices):
    SEC_403_COMPANIES_ACT = (
        "Penalty under Sec 403 of Companies Act.",
        "Penalty under Sec 403 of Companies Act.",
    )
    LLP_100_PER_DAY = (
        "Delay attracts ₹100/day penalty under LLP Act.",
        "Delay attracts ₹100/day penalty under LLP Act.",
    )
    LATE_FILING_INTEREST_18 = (
        "Late filing attracts 18% interest and ₹50/day fee.",
        "Late filing attracts 18% interest and ₹50/day fee.",
    )
    CONSEQUENCES_APPLICABLE_LAW = (
        "Consequences as per applicable law.",
        "Consequences as per applicable law.",
    )
    TCS_100_PER_DAY = (
        "₹100 per day penalty; disallowance of buyer’s TCS credit.",
        "₹100 per day penalty; disallowance of buyer’s TCS credit.",
    )
    PENALTY_1_5_LAKH_OR_0_5_PERCENT = (
        "Penalty ₹1.5 lakh or 0.5% of turnover (whichever lower).",
        "Penalty ₹1.5 lakh or 0.5% of turnover (whichever lower).",
    )
    INCOME_TAX_5000_10000_AND_INTEREST = (
        "₹5,000–₹10,000 penalty; interest u/s 234A/B/C.",
        "₹5,000–₹10,000 penalty; interest u/s 234A/B/C.",
    )
    LATE_PAYMENT_5000_10000 = (
        "₹5,000–₹10,000 penalty; interest on late payment.",
        "₹5,000–₹10,000 penalty; interest on late payment.",
    )
    FORM_3CEB_1_LAKH = (
        "₹1 lakh penalty u/s 271BA for non-filing Form 3CEB.",
        "₹1 lakh penalty u/s 271BA for non-filing Form 3CEB.",
    )
    NOT_APPLICABLE = ("Not Applicable", "Not Applicable")


class InterestType(TextChoices):
    NA = "NA", "NA"
    RATE_18 = "18%", "18%"
    RATE_1 = "1%", "1%"
    RATE_12 = "12%", "12%"
    BANK_RATE_3X = "*3 bank rate", "*3 bank rate"


class ParticularsType(TextChoices):
    AOC4 = (
        "AOC-4-Annual Accounts filing (AOC-4) – late fee ₹1 L/day; interest on delayed accounts",
        "AOC-4-Annual Accounts filing (AOC-4) – late fee ₹1 L/day; interest on delayed accounts",
    )
    AOC4_VARIANTS = (
        "AOC-4-Filing of annual financial statements (AOC-4 / XBRL / CFS)",
        "AOC-4-Filing of annual financial statements (AOC-4 / XBRL / CFS)",
    )
    AOC4_XBRL = (
        "AOC-4 XBRL-AOC-4 XBRL filing – late fee ₹1 L/day; interest on delayed accounts",
        "AOC-4 XBRL-AOC-4 XBRL filing – late fee ₹1 L/day; interest on delayed accounts",
    )

    BEN2_RETURN = (
        "BEN-2-Return of significant beneficial ownership",
        "BEN-2-Return of significant beneficial ownership",
    )

    CHALLAN_280_45 = (
        "Challan 280-2nd instalment of Advance Tax (45%)",
        "Challan 280-2nd instalment of Advance Tax (45%)",
    )
    CHALLAN_280_75 = (
        "Challan 280-3rd instalment of Advance Tax (75%)",
        "Challan 280-3rd instalment of Advance Tax (75%)",
    )
    CHALLAN_280_100 = (
        "Challan 280-4th instalment of Advance Tax (100%)",
        "Challan 280-4th instalment of Advance Tax (100%)",
    )
    CHALLAN_281_MARCH = (
        "Challan 281-Deposit of TDS deducted in March 2025",
        "Challan 281-Deposit of TDS deducted in March 2025",
    )
    CHALLAN_281_DEC = (
        "Challan 281-Deposit of TDS/TCS for December 2025",
        "Challan 281-Deposit of TDS/TCS for December 2025",
    )
    CHALLAN_281_MONTHLY = (
        "Challan 281-Monthly TDS/TCS deposit (non-March months)",
        "Challan 281-Monthly TDS/TCS deposit (non-March months)",
    )
    CRA2 = (
        "CRA-2-Secretarial Audit / CRA-2 filing – late fee ₹5,000/day",
        "CRA-2-Secretarial Audit / CRA-2 filing – late fee ₹5,000/day",
    )

    DIR12 = (
        "DIR-12-Director Appointment / Resignation filing – late fee ₹5,000/day",
        "DIR-12-Director Appointment / Resignation filing – late fee ₹5,000/day",
    )
    DIR3_KYC = (
        "DIR-3 KYC-Director KYC for DIN holders as on 31.03.2025",
        "DIR-3 KYC-Director KYC for DIN holders as on 31.03.2025",
    )

    DPT3 = (
        "DPT-3-Return of deposits / exempted loans",
        "DPT-3-Return of deposits / exempted loans",
    )

    ECB2 = (
        "Form ECB 2-ECB transaction reporting",
        "Form ECB 2-ECB transaction reporting",
    )

    EPF_AUG = (
        "ECR / Challan-Deposit EPF contribution for Aug 2025",
        "ECR / Challan-Deposit EPF contribution for Aug 2025",
    )
    EPF_DEC = (
        "ECR / Challan-Deposit EPF contribution for Dec 2025",
        "ECR / Challan-Deposit EPF contribution for Dec 2025",
    )
    EPF_FEB = (
        "ECR / Challan-Deposit EPF contribution for Feb 2026",
        "ECR / Challan-Deposit EPF contribution for Feb 2026",
    )
    EPF_JAN = (
        "ECR / Challan-Deposit EPF contribution for Jan 2026",
        "ECR / Challan-Deposit EPF contribution for Jan 2026",
    )
    EPF_JUL = (
        "ECR / Challan-Deposit EPF contribution for Jul 2025",
        "ECR / Challan-Deposit EPF contribution for Jul 2025",
    )
    EPF_JUN = (
        "ECR / Challan-Deposit EPF contribution for Jun 2025",
        "ECR / Challan-Deposit EPF contribution for Jun 2025",
    )
    EPF_NOV = (
        "ECR / Challan-Deposit EPF contribution for Nov 2025",
        "ECR / Challan-Deposit EPF contribution for Nov 2025",
    )
    EPF_OCT = (
        "ECR / Challan-Deposit EPF contribution for Oct 2025",
        "ECR / Challan-Deposit EPF contribution for Oct 2025",
    )
    EPF_SEP = (
        "ECR / Challan-Deposit EPF contribution for Sep 2025",
        "ECR / Challan-Deposit EPF contribution for Sep 2025",
    )

    ESI_APR = (
        "Challan / Portal-Deposit ESI contribution for Apr 2025",
        "Challan / Portal-Deposit ESI contribution for Apr 2025",
    )
    ESI_AUG = (
        "Challan / Portal-Deposit ESI contribution for Aug 2025",
        "Challan / Portal-Deposit ESI contribution for Aug 2025",
    )
    ESI_DEC = (
        "Challan / Portal-Deposit ESI contribution for Dec 2025",
        "Challan / Portal-Deposit ESI contribution for Dec 2025",
    )
    ESI_FEB = (
        "Challan / Portal-Deposit ESI contribution for Feb 2026",
        "Challan / Portal-Deposit ESI contribution for Feb 2026",
    )
    ESI_JAN = (
        "Challan / Portal-Deposit ESI contribution for Jan 2026",
        "Challan / Portal-Deposit ESI contribution for Jan 2026",
    )
    ESI_JUL = (
        "Challan / Portal-Deposit ESI contribution for Jul 2025",
        "Challan / Portal-Deposit ESI contribution for Jul 2025",
    )
    ESI_MAR = (
        "ESI Challan / Online Portal (Reg 31-A)-Deposit ESI contribution for Mar 2025",
        "ESI Challan / Online Portal (Reg 31-A)-Deposit ESI contribution for Mar 2025",
    )
    ESI_NOV = (
        "Challan / Portal-Deposit ESI contribution for Nov 2025",
        "Challan / Portal-Deposit ESI contribution for Nov 2025",
    )
    ESI_OCT = (
        "Challan / Portal-Deposit ESI contribution for Oct 2025",
        "Challan / Portal-Deposit ESI contribution for Oct 2025",
    )
    ESI_SEP = (
        "Challan / Portal-Deposit ESI contribution for Sep 2025",
        "Challan / Portal-Deposit ESI contribution for Sep 2025",
    )

    FC4 = (
        "FC-4-Annual return of foreign company",
        "FC-4-Annual return of foreign company",
    )

    FLA_ANNUAL_RETURN = (
        "FLA-Annual return of foreign liabilities & assets",
        "FLA-Annual return of foreign liabilities & assets",
    )

    FORM_16A_Q2 = (
        "Form 16A-Issue of TDS certificates (Q2)",
        "Form 16A-Issue of TDS certificates (Q2)",
    )
    FORM_16A_Q3 = (
        "Form 16A-Quarterly TDS certificate (Q3)",
        "Form 16A-Quarterly TDS certificate (Q3)",
    )
    FORM_16A_Q4 = (
        "Form 16A / 16-Issue of TDS Certificates for Q4 (2024–25)",
        "Form 16A / 16-Issue of TDS Certificates for Q4 (2024–25)",
    )

    FORM_24Q_SET = (
        "Form 24Q/26Q/27Q/27EQ-Quarterly TDS return for Q4 (FY 24–25)",
        "Form 24Q/26Q/27Q/27EQ-Quarterly TDS return for Q4 (FY 24–25)",
    )

    FORM_3CD = (
        "Form 3CD / Various-Tax Audit Report, SEBI filings, TCS Certificate",
        "Form 3CD / Various-Tax Audit Report, SEBI filings, TCS Certificate",
    )

    GSTR1_QRMP = (
        "GSTR-1 (QRMP)-Quarterly outward supply statement (under QRMP scheme) – interest & late fee if delay",
        "GSTR-1 (QRMP)-Quarterly outward supply statement (under QRMP scheme) – interest & late fee if delay",
    )
    GSTR3B = (
        "GSTR-3B-Summary return & tax payment – interest & late fee if delay",
        "GSTR-3B-Summary return & tax payment – interest & late fee if delay",
    )
    GSTR3B_QRMP = (
        "GSTR-3B (QRMP)-Quarterly return summary – interest & late fee",
        "GSTR-3B (QRMP)-Quarterly return summary – interest & late fee",
    )
    GSTR4 = (
        "GSTR-4-Annual return for composition dealers",
        "GSTR-4-Annual return for composition dealers",
    )
    GSTR6 = (
        "GSTR-6-Return for Input Service Distributor (ISD) – late fee if delay",
        "GSTR-6-Return for Input Service Distributor (ISD) – late fee if delay",
    )
    GSTR7 = (
        "GSTR-7-TDS return under GST – interest & late fee for delay",
        "GSTR-7-TDS return under GST – interest & late fee for delay",
    )
    GSTR9 = (
        "GSTR-9-Annual return – summary of all transactions",
        "GSTR-9-Annual return – summary of all transactions",
    )
    GSTR9C = (
        "GSTR-9C-Reconciliation statement & audit certification",
        "GSTR-9C-Reconciliation statement & audit certification",
    )
    GSTR11 = (
        "GSTR-11-Return by UIN holders (e.g. embassies, UN bodies)",
        "GSTR-11-Return by UIN holders (e.g. embassies, UN bodies)",
    )

    ITR5 = (
        "ITR-5-Filing of return of income for entities required to get accounts audited",
        "ITR-5-Filing of return of income for entities required to get accounts audited",
    )
    ITR6 = (
        "ITR-6-Filing of return of income for companies not claiming exemption u/s 11",
        "ITR-6-Filing of return of income for companies not claiming exemption u/s 11",
    )
    ITR6_3_5_7 = (
        "ITR-6 or ITR-3/5/7 (as applicable)-Filing of return of income where assessee has international / specified domestic transactions",
        "ITR-6 or ITR-3/5/7 (as applicable)-Filing of return of income where assessee has international / specified domestic transactions",
    )
    ITR7 = (
        "ITR-7-Filing of return of income by trusts, NGOs, political parties, institutions claiming exemption",
        "ITR-7-Filing of return of income by trusts, NGOs, political parties, institutions claiming exemption",
    )

    ITC04 = (
        "ITC-04-Job-work details – interest & late fee if delay",
        "ITC-04-Job-work details – interest & late fee if delay",
    )

    MBP1 = (
        "MBP-1-Disclosure of interest by Directors (First Board Meeting each FY)",
        "MBP-1-Disclosure of interest by Directors (First Board Meeting each FY)",
    )

    MR1 = (
        "MR-1-AGM Resolutions / MR-1 filing – late fee ₹5,000/day",
        "MR-1-AGM Resolutions / MR-1 filing – late fee ₹5,000/day",
    )

    MSC1 = (
        "MSC-1-Annual Secretarial Compliance filing (MSC-1) – late fee ₹5,000/day",
        "MSC-1-Annual Secretarial Compliance filing (MSC-1) – late fee ₹5,000/day",
    )
    MSME1_H1 = (
        "MSME-1-Half-yearly return of outstanding payments to MSME (Oct 2024 – Mar 2025)",
        "MSME-1-Half-yearly return of outstanding payments to MSME (Oct 2024 – Mar 2025)",
    )
    MSME1_H2 = "MSME-1-MSME-1 (Apr – Sep 2025)", "MSME-1-MSME-1 (Apr – Sep 2025)"

    NDH3 = (
        "NDH-3-Half-yearly return for Nidhi companies",
        "NDH-3-Half-yearly return for Nidhi companies",
    )

    PH1 = (
        "PH1-Statement of outward supplies (sales) – delay may attract interest & late fee",
        "PH1-Statement of outward supplies (sales) – delay may attract interest & late fee",
    )

    SH7_CHG1 = (
        "SH-7 / CHG-1-Change in Authorized Capital / Resolutions – late fee ₹5,000/day",
        "SH-7 / CHG-1-Change in Authorized Capital / Resolutions – late fee ₹5,000/day",
    )

    VARIOUS_27D = (
        "Various / Form 27D-SEBI filings, TCS Certificate",
        "Various / Form 27D-SEBI filings, TCS Certificate",
    )


class CompanyType(TextChoices):
    PRIVATE_LIMITED = "Private Limited", "Private Limited"
    PUBLIC_LIMITED = "Public Limited", "Public Limited"
    LLP = "LLP", "LLP"


class PenaltyAmount(TextChoices):
    LATE_FEE_100_PER_DAY_PENALTY_10K_5L = (
        "Int - NA - Late Fees - ₹100 per day - Penalty - ₹10,000 – ₹5 lakh",
        "Int - NA - Late Fees - ₹100 per day - Penalty - ₹10,000 – ₹5 lakh",
    )
    LATE_FEE_5000_PER_DIN = (
        "Int - NA - Late Fees - NA - Penalty - ₹5,000 per DIN",
        "Int - NA - Late Fees - NA - Penalty - ₹5,000 per DIN",
    )
    LATE_FEE_25K_5L = (
        "Int - NA - Late Fees - ₹100 per day - Penalty - ₹25,000 – ₹5 lakh",
        "Int - NA - Late Fees - ₹100 per day - Penalty - ₹25,000 – ₹5 lakh",
    )
    NO_UPPER_LIMIT_PENALTY = (
        "Int - NA - Late Fees - ₹100 per day - Penalty - No upper limit",
        "Int - NA - Late Fees - ₹100 per day - Penalty - No upper limit",
    )
    PENALTY_1L_5L = (
        "Int - NA - Late Fees - NA - Penalty - ₹1 lakh – ₹5 lakh",
        "Int - NA - Late Fees - NA - Penalty - ₹1 lakh – ₹5 lakh",
    )
    INT_18_PERCENT_TAX_PAYABLE_LATE_FEE_50_DAY = (
        "Int - 18 % p.a. on tax payable u/s 50 - Late Fees - ₹50 / day (₹25 CGST + ₹25 SGST); ₹20 / day for NIL - Penalty - Up to ₹5,000 u/s 47",
        "Int - 18 % p.a. on tax payable u/s 50 - Late Fees - ₹50 / day (₹25 CGST + ₹25 SGST); ₹20 / day for NIL - Penalty - Up to ₹5,000 u/s 47",
    )
    INT_18_PERCENT_PENALTY_5000 = (
        "Int - 18 % p.a. - Late Fees - ₹50 / day (₹20 NIL) - Penalty - Up to ₹5,000",
        "Int - 18 % p.a. - Late Fees - ₹50 / day (₹20 NIL) - Penalty - Up to ₹5,000",
    )
    INT_18_PERCENT_ON_TDS = (
        "Int - 18 % p.a. on TDS amount - Late Fees - ₹50 / day (₹20 NIL) - Penalty - 10 % of TDS not paid or ₹10k (min)",
        "Int - 18 % p.a. on TDS amount - Late Fees - ₹50 / day (₹20 NIL) - Penalty - 10 % of TDS not paid or ₹10k (min)",
    )
    LATE_FEE_100_DAY_272A = (
        "Int - NA - Late Fees - ₹100/day delay (u/s 272A(2)(g)) - Penalty - ₹10k–₹1 lakh",
        "Int - NA - Late Fees - ₹100/day delay (u/s 272A(2)(g)) - Penalty - ₹10k–₹1 lakh",
    )
    INT_12_PERCENT_PENALTY_PROSECUTION_85 = (
        "Int - 12% p.a. (Sec 39 (5)(a)) - Late Fees - 5%–25% p.a. (Reg 31-C) - Penalty - Prosecution u/s 85; damages up to 25% of arrears",
        "Int - 12% p.a. (Sec 39 (5)(a)) - Late Fees - 5%–25% p.a. (Reg 31-C) - Penalty - Prosecution u/s 85; damages up to 25% of arrears",
    )
    PENALTY_FEMA_COMPOUNDING = (
        "Int - NA - Late Fees - Up to ₹2 lakh or thrice the amount involved (FEMA) - Penalty - Compounding penalty up to ₹10,000 per contravention, and if continuing, ₹2,000 per day after the first day (Sec 13, FEMA 1999).",
        "Int - NA - Late Fees - Up to ₹2 lakh or thrice the amount involved (FEMA) - Penalty - Compounding penalty up to ₹10,000 per contravention, and if continuing, ₹2,000 per day after the first day (Sec 13, FEMA 1999).",
    )
    SEBI_NATCS_1_PERCENT = (
        "Int - SEBI – NATCS – 1% per month (u/s 206C) - Late Fees - SEBI – ₹1,000 per dayTCS – ₹200 per day (u/s 234E) - Penalty - SEBI: ₹1 lakh per day or up to ₹1 crore. Income Tax: ₹100 per day under Sec 272A(2)(k).",
        "Int - SEBI – NATCS – 1% per month (u/s 206C) - Late Fees - SEBI – ₹1,000 per dayTCS – ₹200 per day (u/s 234E) - Penalty - SEBI: ₹1 lakh per day or up to ₹1 crore. Income Tax: ₹100 per day under Sec 272A(2)(k).",
    )
    TAX_AUDIT_TCS_1_PERCENT = (
        "Int - Tax Audit – 1% per month (u/s 234A/B/C)TCS – 1% per month (u/s 206C) - Late Fees - Tax Audit – ₹1.5 lakh or 0.5% of turnover (u/s 271B)SEBI – ₹1,000 per dayTCS – ₹200 per day (u/s 234E) - Penalty - Tax Audit (Sec 271B): 0.5% of turnover (max ₹1,50,000). SEBI: ₹1 lakh per day or up to ₹1 crore.",
        "Int - Tax Audit – 1% per month (u/s 234A/B/C)TCS – 1% per month (u/s 206C) - Late Fees - Tax Audit – ₹1.5 lakh or 0.5% of turnover (u/s 271B)SEBI – ₹1,000 per dayTCS – ₹200 per day (u/s 234E) - Penalty - Tax Audit (Sec 271B): 0.5% of turnover (max ₹1,50,000). SEBI: ₹1 lakh per day or up to ₹1 crore.",
    )
