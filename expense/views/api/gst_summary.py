from decimal import Decimal
from collections import defaultdict
from datetime import datetime, timedelta
from calendar import monthrange
from django.db.models import Q, Count, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Company
from expense.models.bills import Bill
from expense.views.api.bills import get_company_from_request
from financial.enums import BillsStatusChoices


class GSTSummaryView(APIView):
    """
    Combined API endpoint for GST Summary data.

    GET /api/expense/gst-summary/
    - Returns:
      * GST KPIs: Taxable Value, Total GST Input, ITC Available, ITC Pending
      * GST Distribution: CGST, SGST, IGST, Cess breakdown
      * ITC Status: ITC Utilization percentage
      * Supply Type Breakdown: B2B Local, B2B Interstate, B2C/Unregistered
      * Monthly GST Input Trend: Monthly breakdown of CGST, SGST, IGST
      * HSN/SAC Code-wise Summary
      * Vendor-wise Summary
      * Monthly Filing Summary
    - Query parameters:
      * months (optional): Number of months to include in trends (default: 12)
    """

    permission_classes = [IsAuthenticated]

    @staticmethod
    def _format_amount(amount: Decimal) -> str:
        """Format amount in lakhs/crores with Indian numbering"""
        if amount == 0:
            return "₹0"
        if amount < 1000:
            return f"₹{amount:,.2f}"
        elif amount < 100000:
            return f"₹{amount / 1000:.2f}K"
        elif amount < 10000000:  # Less than 1 crore
            lakhs = amount / Decimal("100000")
            return f"₹{lakhs.quantize(Decimal('0.01'))}L"
        else:  # 1 crore or more
            crores = amount / Decimal("10000000")
            return f"₹{crores.quantize(Decimal('0.01'))}Cr"

    @staticmethod
    def _format_amount_indian(amount: Decimal) -> str:
        """Format amount with Indian numbering system (lakhs/crores)"""
        if amount == 0:
            return "₹0"
        # Convert to string with Indian numbering
        amount_str = f"{amount:,.2f}"
        # For amounts >= 1 crore, show in crores
        if amount >= 10000000:
            crores = amount / Decimal("10000000")
            return f"₹{crores.quantize(Decimal('0.01'))}Cr"
        # For amounts >= 1 lakh, show in lakhs
        elif amount >= 100000:
            lakhs = amount / Decimal("100000")
            return f"₹{lakhs.quantize(Decimal('0.01'))}L"
        else:
            return f"₹{amount:,.2f}"

    def _is_eligible_for_itc(self, bill):
        """
        Determine if bill is eligible for ITC.
        Logic: ITC is eligible when:
        - Vendor has GSTIN (or vendor_gstin is provided)
        - GST is paid (CGST + SGST + IGST > 0)
        - Not marked as ineligible in eligibility field
        """
        has_gstin = (
            (bill.vendor and bill.vendor.gstin)
            or bill.vendor_gstin
            or (bill.vendor and hasattr(bill.vendor, "gstin") and bill.vendor.gstin)
        )
        has_gst = bill.cgst_amount > 0 or bill.sgst_amount > 0 or bill.igst_amount > 0
        # Check eligibility field - if it contains "not eligible" or similar, exclude
        is_marked_ineligible = (
            bill.eligibility and "not eligible" in bill.eligibility.lower()
        )

        return has_gstin and has_gst and not is_marked_ineligible

    def get(self, request, *args, **kwargs):
        """Get all GST summary data in one response"""
        company = get_company_from_request(request)
        if not company:
            return Response(
                {
                    "gst_kpis": {
                        "taxable_value": {
                            "amount": 0,
                            "amount_display": "₹0",
                        },
                        "total_gst_input": {
                            "amount": 0,
                            "amount_display": "₹0",
                            "breakdown": {
                                "cgst": 0,
                                "sgst": 0,
                                "igst": 0,
                                "cess": 0,
                            },
                        },
                        "itc_available": {
                            "amount": 0,
                            "amount_display": "₹0",
                        },
                        "itc_pending": {
                            "amount": 0,
                            "amount_display": "₹0",
                        },
                    },
                    "gst_distribution": {
                        "cgst": 0,
                        "sgst": 0,
                        "igst": 0,
                        "cess": 0,
                    },
                    "itc_status": {
                        "itc_available": 0,
                        "itc_claimed": 0,
                        "itc_pending": 0,
                        "utilization_percentage": 0.0,
                    },
                    "supply_type_breakdown": {
                        "b2b_local": {
                            "amount": 0,
                            "amount_display": "₹0",
                            "invoice_count": 0,
                        },
                        "b2b_interstate": {
                            "amount": 0,
                            "amount_display": "₹0",
                            "invoice_count": 0,
                        },
                        "b2c_unregistered": {
                            "amount": 0,
                            "amount_display": "₹0",
                            "invoice_count": 0,
                        },
                    },
                    "monthly_gst_input_trend": [],
                    "hsn_sac_summary": [],
                    "vendor_wise_summary": [],
                    "monthly_filing_summary": [],
                },
                status=status.HTTP_200_OK,
            )

        # Get query parameters
        months = int(request.query_params.get("months", 12))

        # Get all bills (excluding cancelled)
        bills = (
            Bill.objects.filter(company=company)
            .exclude(status=BillsStatusChoices.CANCELLED)
            .select_related("vendor")
        )

        # Calculate GST KPIs
        total_taxable_value = sum(bill.subtotal for bill in bills)
        total_cgst = sum(bill.cgst_amount for bill in bills)
        total_sgst = sum(bill.sgst_amount for bill in bills)
        total_igst = sum(bill.igst_amount for bill in bills)
        total_cess = Decimal("0")  # Cess not in model, set to 0
        total_gst_input = total_cgst + total_sgst + total_igst + total_cess

        # Calculate ITC Available (GST where eligible for ITC)
        itc_available = Decimal("0")
        for bill in bills:
            if self._is_eligible_for_itc(bill):
                itc_available += bill.cgst_amount + bill.sgst_amount + bill.igst_amount

        # ITC Claimed - not tracked in model, assume 0 for now
        # In future, this could be tracked in a separate model
        itc_claimed = Decimal("0")
        itc_pending = itc_available - itc_claimed

        # ITC Utilization percentage
        itc_utilization = (
            float((itc_claimed / itc_available) * 100) if itc_available > 0 else 0.0
        )

        gst_kpis = {
            "taxable_value": {
                "amount": float(total_taxable_value),
                "amount_display": self._format_amount_indian(total_taxable_value),
            },
            "total_gst_input": {
                "amount": float(total_gst_input),
                "amount_display": self._format_amount_indian(total_gst_input),
                "breakdown": {
                    "cgst": float(total_cgst),
                    "sgst": float(total_sgst),
                    "igst": float(total_igst),
                    "cess": float(total_cess),
                },
            },
            "itc_available": {
                "amount": float(itc_available),
                "amount_display": self._format_amount_indian(itc_available),
            },
            "itc_pending": {
                "amount": float(itc_pending),
                "amount_display": self._format_amount_indian(itc_pending),
            },
        }

        # GST Distribution
        gst_distribution = {
            "cgst": float(total_cgst),
            "sgst": float(total_sgst),
            "igst": float(total_igst),
            "cess": float(total_cess),
        }

        # ITC Status
        itc_status = {
            "itc_available": float(itc_available),
            "itc_claimed": float(itc_claimed),
            "itc_pending": float(itc_pending),
            "utilization_percentage": round(itc_utilization, 1),
        }

        # Supply Type Breakdown
        b2b_local_bills = bills.filter(
            Q(cgst_amount__gt=0) | Q(sgst_amount__gt=0)
        ).exclude(igst_amount__gt=0)
        b2b_interstate_bills = bills.filter(igst_amount__gt=0)
        b2c_unregistered_bills = bills.filter(
            Q(cgst_amount=0, sgst_amount=0, igst_amount=0)
            | Q(vendor_gstin="")
            | Q(vendor__isnull=True, vendor_gstin="")
        )

        b2b_local_amount = sum(bill.subtotal for bill in b2b_local_bills)
        b2b_interstate_amount = sum(bill.subtotal for bill in b2b_interstate_bills)
        b2c_unregistered_amount = sum(bill.subtotal for bill in b2c_unregistered_bills)

        supply_type_breakdown = {
            "b2b_local": {
                "amount": float(b2b_local_amount),
                "amount_display": self._format_amount_indian(b2b_local_amount),
                "invoice_count": b2b_local_bills.count(),
            },
            "b2b_interstate": {
                "amount": float(b2b_interstate_amount),
                "amount_display": self._format_amount_indian(b2b_interstate_amount),
                "invoice_count": b2b_interstate_bills.count(),
            },
            "b2c_unregistered": {
                "amount": float(b2c_unregistered_amount),
                "amount_display": self._format_amount_indian(b2c_unregistered_amount),
                "invoice_count": b2c_unregistered_bills.count(),
            },
        }

        # Monthly GST Input Trend
        today = timezone.now().date()
        current_month_start = today.replace(day=1)

        monthly_gst_input_trend = []
        for i in range(months - 1, -1, -1):
            month_date = (current_month_start - timedelta(days=30 * i)).replace(day=1)
            last_day = monthrange(month_date.year, month_date.month)[1]
            month_end = month_date.replace(day=last_day)

            month_bills = bills.filter(
                bill_date__year=month_date.year, bill_date__month=month_date.month
            )

            month_cgst = sum(bill.cgst_amount for bill in month_bills)
            month_sgst = sum(bill.sgst_amount for bill in month_bills)
            month_igst = sum(bill.igst_amount for bill in month_bills)
            month_cess = Decimal("0")

            monthly_gst_input_trend.append(
                {
                    "month": month_date.strftime("%Y-%m"),
                    "month_display": month_date.strftime("%b %Y"),
                    "cgst": float(month_cgst),
                    "cgst_display": self._format_amount(month_cgst),
                    "sgst": float(month_sgst),
                    "sgst_display": self._format_amount(month_sgst),
                    "igst": float(month_igst),
                    "igst_display": self._format_amount(month_igst),
                    "cess": float(month_cess),
                    "cess_display": self._format_amount(month_cess),
                    "total": float(month_cgst + month_sgst + month_igst + month_cess),
                    "total_display": self._format_amount(
                        month_cgst + month_sgst + month_igst + month_cess
                    ),
                }
            )

        # HSN/SAC Code-wise Summary
        hsn_sac_data = defaultdict(
            lambda: {
                "count": 0,
                "taxable_value": Decimal("0"),
                "gst_amount": Decimal("0"),
            }
        )

        for bill in bills:
            hsn_sac = bill.hsn_sac or "Not Specified"
            hsn_sac_data[hsn_sac]["count"] += 1
            hsn_sac_data[hsn_sac]["taxable_value"] += bill.subtotal
            hsn_sac_data[hsn_sac]["gst_amount"] += (
                bill.cgst_amount + bill.sgst_amount + bill.igst_amount
            )

        hsn_sac_summary = []
        for hsn_sac, data in sorted(
            hsn_sac_data.items(), key=lambda x: x[1]["taxable_value"], reverse=True
        ):
            hsn_sac_summary.append(
                {
                    "hsn_sac_code": hsn_sac,
                    "count": data["count"],
                    "taxable_value": float(data["taxable_value"]),
                    "taxable_value_display": self._format_amount_indian(
                        data["taxable_value"]
                    ),
                    "gst_amount": float(data["gst_amount"]),
                    "gst_amount_display": self._format_amount_indian(
                        data["gst_amount"]
                    ),
                }
            )

        # Add total row
        total_count = sum(data["count"] for data in hsn_sac_data.values())
        total_taxable = sum(data["taxable_value"] for data in hsn_sac_data.values())
        total_gst = sum(data["gst_amount"] for data in hsn_sac_data.values())

        hsn_sac_summary.append(
            {
                "hsn_sac_code": "TOTAL",
                "count": total_count,
                "taxable_value": float(total_taxable),
                "taxable_value_display": self._format_amount_indian(total_taxable),
                "gst_amount": float(total_gst),
                "gst_amount_display": self._format_amount_indian(total_gst),
            }
        )

        # Vendor-wise Summary
        vendor_data = defaultdict(
            lambda: {
                "count": 0,
                "taxable_value": Decimal("0"),
                "gst_amount": Decimal("0"),
                "vendor_name": None,
                "vendor_gstin": None,
            }
        )

        for bill in bills:
            vendor_key = bill.vendor_id or bill.vendor_name or "Unknown"
            vendor_data[vendor_key]["count"] += 1
            vendor_data[vendor_key]["taxable_value"] += bill.subtotal
            vendor_data[vendor_key]["gst_amount"] += (
                bill.cgst_amount + bill.sgst_amount + bill.igst_amount
            )
            if not vendor_data[vendor_key]["vendor_name"]:
                vendor_data[vendor_key]["vendor_name"] = (
                    bill.vendor.name if bill.vendor else (bill.vendor_name or "Unknown")
                )
            if not vendor_data[vendor_key]["vendor_gstin"]:
                vendor_data[vendor_key]["vendor_gstin"] = (
                    bill.vendor.gstin
                    if bill.vendor and bill.vendor.gstin
                    else (bill.vendor_gstin or "-")
                )

        vendor_wise_summary = []
        for vendor_key, data in sorted(
            vendor_data.items(),
            key=lambda x: x[1]["taxable_value"],
            reverse=True,
        ):
            vendor_wise_summary.append(
                {
                    "vendor_name": data["vendor_name"],
                    "vendor_gstin": data["vendor_gstin"],
                    "invoice_count": data["count"],
                    "taxable_value": float(data["taxable_value"]),
                    "taxable_value_display": self._format_amount_indian(
                        data["taxable_value"]
                    ),
                    "gst_amount": float(data["gst_amount"]),
                    "gst_amount_display": self._format_amount_indian(
                        data["gst_amount"]
                    ),
                }
            )

        # Monthly Filing Summary (for GSTR-3B)
        monthly_filing_summary = []
        for i in range(months - 1, -1, -1):
            month_date = (current_month_start - timedelta(days=30 * i)).replace(day=1)
            last_day = monthrange(month_date.year, month_date.month)[1]
            month_end = month_date.replace(day=last_day)

            month_bills = bills.filter(
                bill_date__year=month_date.year, bill_date__month=month_date.month
            )

            month_taxable = sum(bill.subtotal for bill in month_bills)
            month_cgst = sum(bill.cgst_amount for bill in month_bills)
            month_sgst = sum(bill.sgst_amount for bill in month_bills)
            month_igst = sum(bill.igst_amount for bill in month_bills)
            month_total_gst = month_cgst + month_sgst + month_igst

            monthly_filing_summary.append(
                {
                    "month": month_date.strftime("%Y-%m"),
                    "month_display": month_date.strftime("%b %Y"),
                    "taxable_value": float(month_taxable),
                    "taxable_value_display": self._format_amount_indian(month_taxable),
                    "cgst": float(month_cgst),
                    "cgst_display": self._format_amount(month_cgst),
                    "sgst": float(month_sgst),
                    "sgst_display": self._format_amount(month_sgst),
                    "igst": float(month_igst),
                    "igst_display": self._format_amount(month_igst),
                    "total_gst": float(month_total_gst),
                    "total_gst_display": self._format_amount_indian(month_total_gst),
                }
            )

        # Add total row for monthly filing summary
        total_monthly_taxable = sum(
            item["taxable_value"] for item in monthly_filing_summary
        )
        total_monthly_cgst = sum(item["cgst"] for item in monthly_filing_summary)
        total_monthly_sgst = sum(item["sgst"] for item in monthly_filing_summary)
        total_monthly_igst = sum(item["igst"] for item in monthly_filing_summary)
        total_monthly_gst = sum(item["total_gst"] for item in monthly_filing_summary)

        monthly_filing_summary.append(
            {
                "month": "TOTAL",
                "month_display": "TOTAL",
                "taxable_value": float(total_monthly_taxable),
                "taxable_value_display": self._format_amount_indian(
                    total_monthly_taxable
                ),
                "cgst": float(total_monthly_cgst),
                "cgst_display": self._format_amount(total_monthly_cgst),
                "sgst": float(total_monthly_sgst),
                "sgst_display": self._format_amount(total_monthly_sgst),
                "igst": float(total_monthly_igst),
                "igst_display": self._format_amount(total_monthly_igst),
                "total_gst": float(total_monthly_gst),
                "total_gst_display": self._format_amount_indian(total_monthly_gst),
            }
        )

        return Response(
            {
                "gst_kpis": gst_kpis,
                "gst_distribution": gst_distribution,
                "itc_status": itc_status,
                "supply_type_breakdown": supply_type_breakdown,
                "monthly_gst_input_trend": monthly_gst_input_trend,
                "hsn_sac_summary": hsn_sac_summary,
                "vendor_wise_summary": vendor_wise_summary,
                "monthly_filing_summary": monthly_filing_summary,
            },
            status=status.HTTP_200_OK,
        )
