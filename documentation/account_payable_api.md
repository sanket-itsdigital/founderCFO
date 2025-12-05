# Accounts Payable API Documentation

This document provides comprehensive documentation for all Accounts Payable (AP) APIs, including endpoints, request/response formats, and examples.

## Table of Contents

1. [Bills APIs](#bills-apis)
2. [AP Ageing Summary](#ap-ageing-summary)
3. [Vendor Balance Summary](#vendor-balance-summary)
4. [Payment Priority Queue](#payment-priority-queue)
5. [Payment Scheduler](#payment-scheduler)
6. [Record Payment](#record-payment)
7. [Cash Flow Projection](#cash-flow-projection)
8. [AP Analytics](#ap-analytics)
9. [AP Dashboard](#ap-dashboard)

---

## Bills APIs

### 1. List Bills

**Endpoint:** `GET /api/financial/payable/bills/`

**Description:** Retrieve a list of all bills for the company.

**Query Parameters:**
- `company_id` (optional): Company UUID
- `status` (optional): Filter by status (PENDING, PARTIAL, PAID, OVERDUE, CANCELLED)
- `vendor_name` (optional): Filter by vendor name (partial match)
- `bill_number` (optional): Filter by bill number (partial match)
- `search` (optional): Search across bill_number, vendor_name, category

**Sample Request:**
```
GET /api/financial/payable/bills/?company_id=<uuid>&status=PENDING
```

**Sample Response:**
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "bill_number": "BILL-2024-001",
      "vendor_id": "660e8400-e29b-41d4-a716-446655440001",
      "vendor_name": "Tech Mahindra",
      "bill_date": "2025-10-14",
      "due_date": "2025-11-14",
      "amount": 31170.00,
      "amount_display": "₹31.17K",
      "paid_amount": 0.00,
      "paid_amount_display": "₹0.00K",
      "balance_amount": 31170.00,
      "balance_display": "₹31.17K",
      "status": "PENDING",
      "status_display": "Pending",
      "category": "IT Services",
      "notes": "",
      "is_overdue": true,
      "created_at": "2025-10-14T10:00:00Z",
      "updated_at": "2025-10-14T10:00:00Z"
    }
  ]
}
```

---

### 2. Create Bill

**Endpoint:** `POST /api/financial/payable/bills/`

**Description:** Create a new bill.

**Request Body:**
```json
{
  "bill_number": "BILL-2024-001",
  "vendor": "660e8400-e29b-41d4-a716-446655440001",
  "vendor_name": "Tech Mahindra",
  "bill_date": "2025-10-14",
  "due_date": "2025-11-14",
  "amount": 31170.00,
  "paid_amount": 0.00,
  "status": "PENDING",
  "category": "IT Services",
  "notes": "Monthly service bill"
}
```

**Sample Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "bill_number": "BILL-2024-001",
  "vendor_id": "660e8400-e29b-41d4-a716-446655440001",
  "vendor_name": "Tech Mahindra",
  "bill_date": "2025-10-14",
  "due_date": "2025-11-14",
  "amount": 31170.00,
  "amount_display": "₹31.17K",
  "paid_amount": 0.00,
  "paid_amount_display": "₹0.00K",
  "balance_amount": 31170.00,
  "balance_display": "₹31.17K",
  "status": "PENDING",
  "status_display": "Pending",
  "category": "IT Services",
  "notes": "Monthly service bill",
  "is_overdue": false,
  "created_at": "2025-10-14T10:00:00Z",
  "updated_at": "2025-10-14T10:00:00Z"
}
```

---

### 3. Get Bill Details

**Endpoint:** `GET /api/financial/payable/bills/<uuid:id>/`

**Description:** Retrieve details of a specific bill.

**Sample Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "bill_number": "BILL-2024-001",
  "vendor_id": "660e8400-e29b-41d4-a716-446655440001",
  "vendor_name": "Tech Mahindra",
  "bill_date": "2025-10-14",
  "due_date": "2025-11-14",
  "amount": 31170.00,
  "amount_display": "₹31.17K",
  "paid_amount": 0.00,
  "paid_amount_display": "₹0.00K",
  "balance_amount": 31170.00,
  "balance_display": "₹31.17K",
  "status": "PENDING",
  "status_display": "Pending",
  "category": "IT Services",
  "notes": "",
  "is_overdue": false,
  "created_at": "2025-10-14T10:00:00Z",
  "updated_at": "2025-10-14T10:00:00Z"
}
```

---

### 4. Update Bill

**Endpoint:** `PUT /api/financial/payable/bills/<uuid:id>/` or `PATCH /api/financial/payable/bills/<uuid:id>/`

**Description:** Update an existing bill (PUT for full update, PATCH for partial update).

**Request Body (PATCH):**
```json
{
  "paid_amount": 15000.00,
  "status": "PARTIAL"
}
```

**Sample Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "bill_number": "BILL-2024-001",
  "vendor_id": "660e8400-e29b-41d4-a716-446655440001",
  "vendor_name": "Tech Mahindra",
  "bill_date": "2025-10-14",
  "due_date": "2025-11-14",
  "amount": 31170.00,
  "amount_display": "₹31.17K",
  "paid_amount": 15000.00,
  "paid_amount_display": "₹15.00K",
  "balance_amount": 16170.00,
  "balance_display": "₹16.17K",
  "status": "PARTIAL",
  "status_display": "Partial",
  "category": "IT Services",
  "notes": "",
  "is_overdue": false,
  "created_at": "2025-10-14T10:00:00Z",
  "updated_at": "2025-10-14T15:30:00Z"
}
```

---

### 5. Delete Bill

**Endpoint:** `DELETE /api/financial/payable/bills/<uuid:id>/`

**Description:** Delete a bill.

**Sample Response:**
```
204 No Content
```

---

## AP Ageing Summary

**Endpoint:** `GET /api/financial/payable/ap-ageing-summary/`

**Description:** Get Accounts Payable ageing analysis with breakdown by time buckets.

**Query Parameters:**
- `company_id` (optional): Company UUID

**Sample Request:**
```
GET /api/financial/payable/ap-ageing-summary/?company_id=<uuid>
```

**Sample Response:**
```json
{
  "total_ap": 9699000.0,
  "total_ap_display": "₹96.99L",
  "overdue_percentage": 50.2,
  "portfolio_health": "At Risk - Prioritize payments",
  "ageing_buckets": [
    {
      "label": "Current",
      "amount": 4830000.0,
      "amount_display": "₹48.30L",
      "percentage": 49.8
    },
    {
      "label": "1-30 Days",
      "amount": 2368000.0,
      "amount_display": "₹23.68L",
      "percentage": 24.4
    },
    {
      "label": "31-60 Days",
      "amount": 2502000.0,
      "amount_display": "₹25.02L",
      "percentage": 25.8
    },
    {
      "label": "61-90 Days",
      "amount": 0.0,
      "amount_display": "₹0.00L",
      "percentage": 0.0
    },
    {
      "label": "90+ Days",
      "amount": 0.0,
      "amount_display": "₹0.00L",
      "percentage": 0.0
    }
  ]
}
```

**Field Descriptions:**
- `total_ap`: Total outstanding accounts payable amount
- `overdue_percentage`: Percentage of AP that is overdue
- `portfolio_health`: Health indicator (Healthy, Low Risk, Moderate Risk, At Risk)
- `ageing_buckets`: Breakdown by time periods (Current, 1-30 Days, 31-60 Days, 61-90 Days, 90+ Days)

---

## Vendor Balance Summary

**Endpoint:** `GET /api/financial/payable/vendors/balance-summary/`

**Description:** Get summary of outstanding balances by vendor.

**Query Parameters:**
- `company_id` (optional): Company UUID

**Sample Request:**
```
GET /api/financial/payable/vendors/balance-summary/?company_id=<uuid>
```

**Sample Response:**
```json
{
  "total_outstanding": 9699000.0,
  "total_outstanding_display": "₹96.99L",
  "vendors": [
    {
      "vendor_id": "660e8400-e29b-41d4-a716-446655440001",
      "vendor_name": "Mahindra & Mahindra",
      "outstanding": 1875000.0,
      "outstanding_display": "₹18.75L",
      "bill_count": 4,
      "oldest_bill_date": "2025-10-13",
      "oldest_bill_display": "13 Oct 2025",
      "percentage_of_total": 19.3
    },
    {
      "vendor_id": "660e8400-e29b-41d4-a716-446655440002",
      "vendor_name": "ITC Limited",
      "outstanding": 1388000.0,
      "outstanding_display": "₹13.88L",
      "bill_count": 2,
      "oldest_bill_date": "2025-09-03",
      "oldest_bill_display": "03 Sep 2025",
      "percentage_of_total": 14.3
    }
  ]
}
```

**Field Descriptions:**
- `total_outstanding`: Total outstanding amount across all vendors
- `vendors`: List of vendors with outstanding balances, sorted by amount (descending)
- `bill_count`: Number of outstanding bills for the vendor
- `oldest_bill_date`: Date of the oldest outstanding bill
- `percentage_of_total`: Vendor's outstanding as percentage of total

---

## Payment Priority Queue

**Endpoint:** `GET /api/financial/payable/payment-priority/`

**Description:** Get bills prioritized by overdue status and early payment discounts.

**Query Parameters:**
- `company_id` (optional): Company UUID

**Sample Request:**
```
GET /api/financial/payable/payment-priority/?company_id=<uuid>
```

**Sample Response:**
```json
{
  "bills": [
    {
      "bill_id": "550e8400-e29b-41d4-a716-446655440000",
      "bill_number": "BILL-2024-013",
      "vendor_id": "660e8400-e29b-41d4-a716-446655440001",
      "vendor_name": "Tech Mahindra",
      "due_date": "2025-10-14",
      "due_date_display": "14 Oct 2025",
      "days_overdue": 51,
      "days_display": "51 overdue",
      "amount_due": 31170.0,
      "amount_due_display": "₹31.17K",
      "discount_percentage": null,
      "discount_display": "-",
      "priority": "Critical",
      "priority_color": "#EF4444"
    },
    {
      "bill_id": "550e8400-e29b-41d4-a716-446655440001",
      "bill_number": "BILL-2024-030",
      "vendor_id": "660e8400-e29b-41d4-a716-446655440002",
      "vendor_name": "Infosys Limited",
      "due_date": "2025-10-18",
      "due_date_display": "18 Oct 2025",
      "days_overdue": 47,
      "days_display": "47 overdue",
      "amount_due": 316000.0,
      "amount_due_display": "₹3.16L",
      "discount_percentage": null,
      "discount_display": "-",
      "priority": "Critical",
      "priority_color": "#EF4444"
    }
  ],
  "summary": {
    "total_bills": 10,
    "total_amount": 9699000.0,
    "total_amount_display": "₹96.99L",
    "critical_count": 5,
    "overdue_count": 3
  }
}
```

**Field Descriptions:**
- `bills`: List of bills sorted by priority (Critical first, then Overdue)
- `priority`: Priority level (Critical: 45+ days overdue, Overdue: <45 days overdue)
- `discount_percentage`: Early payment discount percentage if available
- `summary`: Summary statistics

---

## Payment Scheduler

**Endpoint:** `GET /api/financial/payable/payment-scheduler/`

**Description:** Get bills grouped by payment schedule (Overdue, Due This Week, Due Next Week, Upcoming).

**Query Parameters:**
- `company_id` (optional): Company UUID

**Sample Request:**
```
GET /api/financial/payable/payment-scheduler/?company_id=<uuid>
```

**Sample Response:**
```json
{
  "summary_cards": [
    {
      "title": "Overdue",
      "amount": 4870000.0,
      "amount_display": "₹48.70L",
      "bill_count": 13,
      "icon": "overdue"
    },
    {
      "title": "Due This Week",
      "amount": 785000.0,
      "amount_display": "₹7.85L",
      "bill_count": 2,
      "icon": "due_this_week"
    },
    {
      "title": "Due Next Week",
      "amount": 1998000.0,
      "amount_display": "₹19.98L",
      "bill_count": 3,
      "icon": "due_next_week"
    }
  ],
  "overdue": {
    "group_name": "Overdue",
    "bill_count": 13,
    "total_amount": 4870000.0,
    "total_amount_display": "₹48.70L",
    "potential_discount": null,
    "potential_discount_display": null,
    "bills": [
      {
        "bill_id": "550e8400-e29b-41d4-a716-446655440000",
        "bill_number": "BILL-2024-013",
        "vendor_id": "660e8400-e29b-41d4-a716-446655440001",
        "vendor_name": "Tech Mahindra",
        "due_date": "2025-10-14",
        "due_date_display": "14 Oct 2025",
        "days_overdue": 51,
        "days_until_due": 0,
        "days_display": "51 overdue",
        "amount": 31170.0,
        "amount_display": "₹31.17K",
        "discount_percentage": null,
        "discount_amount": null,
        "discount_display": "-",
        "status": "Overdue",
        "is_selected": false
      }
    ]
  },
  "due_this_week": {
    "group_name": "Due This Week",
    "bill_count": 2,
    "total_amount": 785000.0,
    "total_amount_display": "₹7.85L",
    "potential_discount": 3040.0,
    "potential_discount_display": "₹3.04K",
    "bills": [
      {
        "bill_id": "550e8400-e29b-41d4-a716-446655440002",
        "bill_number": "BILL-2024-022",
        "vendor_id": "660e8400-e29b-41d4-a716-446655440003",
        "vendor_name": "Hindustan Petroleum",
        "due_date": "2025-12-11",
        "due_date_display": "11 Dec 2025",
        "days_overdue": 0,
        "days_until_due": 7,
        "days_display": "7 days",
        "amount": 152000.0,
        "amount_display": "₹1.52L",
        "discount_percentage": 2.0,
        "discount_amount": 3040.0,
        "discount_display": "Save ₹3.04K",
        "status": "Due Soon",
        "is_selected": false
      }
    ]
  },
  "due_next_week": {
    "group_name": "Due Next Week",
    "bill_count": 3,
    "total_amount": 1998000.0,
    "total_amount_display": "₹19.98L",
    "potential_discount": null,
    "potential_discount_display": null,
    "bills": []
  },
  "upcoming": {
    "group_name": "Upcoming",
    "bill_count": 5,
    "total_amount": 2047000.0,
    "total_amount_display": "₹20.47L",
    "potential_discount": 7470.0,
    "potential_discount_display": "₹7.47K",
    "bills": []
  },
  "selected_for_payment": {
    "group_name": "Selected for Payment",
    "bill_count": 0,
    "total_amount": 0.0,
    "total_amount_display": "₹0.00L",
    "potential_discount": null,
    "potential_discount_display": null,
    "bills": []
  }
}
```

**Field Descriptions:**
- `summary_cards`: Quick overview cards for Overdue, Due This Week, Due Next Week
- `overdue`: Bills past their due date
- `due_this_week`: Bills due within the next 7 days
- `due_next_week`: Bills due in 8-14 days
- `upcoming`: Bills due after 14 days
- `selected_for_payment`: Bills selected for payment (managed by frontend)
- `potential_discount`: Total potential discount if paid early

---

## Record Payment

**Endpoint:** `POST /api/financial/payable/record-payment/`

**Description:** Record a payment for a bill.

**Request Body:**
```json
{
  "bill_id": "550e8400-e29b-41d4-a716-446655440000",
  "payment_date": "2025-12-04",
  "amount": 260139.00,
  "payment_method": "Bank Transfer",
  "reference_number": "TXN123456",
  "bank_name": "HDFC Bank",
  "tds_deducted": 0.00,
  "discount_taken": 0.00,
  "notes": "Payment processed via NEFT"
}
```

**Payment Methods:**
- `Bank Transfer`
- `NEFT`
- `RTGS`
- `IMPS`
- `Cheque`
- `UPI`
- `Cash`
- `Credit Card`

**Sample Response:**
```json
{
  "payment_id": "770e8400-e29b-41d4-a716-446655440000",
  "bill_id": "550e8400-e29b-41d4-a716-446655440000",
  "bill_number": "BILL-2024-018",
  "payment_date": "2025-12-04",
  "amount": 260139.0,
  "amount_display": "₹2.60L",
  "payment_method": "Bank Transfer",
  "bill_status": "PAID",
  "bill_balance": 0.0,
  "bill_balance_display": "₹0.00L",
  "message": "Payment of ₹2.60L recorded successfully. Bill status: Paid"
}
```

**Field Descriptions:**
- `bill_id`: UUID of the bill being paid
- `payment_date`: Date of payment
- `amount`: Payment amount (excluding TDS and discount)
- `payment_method`: Method of payment
- `reference_number`: Transaction reference number
- `bank_name`: Bank name (for bank transfers)
- `tds_deducted`: TDS deducted from payment
- `discount_taken`: Discount taken on payment
- `notes`: Payment notes

**Note:** The bill's `paid_amount` and `status` are automatically updated after payment is recorded.

---

## Cash Flow Projection

**Endpoint:** `GET /api/financial/payable/cash-flow-projection/`

**Description:** Get cash outflow projection based on bill due dates.

**Query Parameters:**
- `company_id` (optional): Company UUID

**Sample Request:**
```
GET /api/financial/payable/cash-flow-projection/?company_id=<uuid>
```

**Sample Response:**
```json
{
  "summary": {
    "next_7_days": 5503000.0,
    "next_7_days_display": "₹55.03L",
    "next_30_days": 8613000.0,
    "next_30_days_display": "₹86.13L",
    "next_90_days": 9699000.0,
    "next_90_days_display": "₹96.99L"
  },
  "projections": [
    {
      "date": "2025-12-04",
      "date_display": "Dec 04",
      "due_amount": 500000.0,
      "due_amount_display": "₹5.00L",
      "cumulative_amount": 500000.0,
      "cumulative_amount_display": "₹5.00L"
    },
    {
      "date": "2025-12-05",
      "date_display": "Dec 05",
      "due_amount": 0.0,
      "due_amount_display": "₹0.00L",
      "cumulative_amount": 500000.0,
      "cumulative_amount_display": "₹5.00L"
    },
    {
      "date": "2025-12-29",
      "date_display": "Dec 29",
      "due_amount": 961000.0,
      "due_amount_display": "₹9.61L",
      "cumulative_amount": 8613000.0,
      "cumulative_amount_display": "₹86.13L"
    }
  ]
}
```

**Field Descriptions:**
- `summary`: Projected outflows for next 7, 30, and 90 days
- `projections`: Daily projection data for next 90 days
- `due_amount`: Amount due on that specific date
- `cumulative_amount`: Cumulative total up to that date

---

## AP Analytics

**Endpoint:** `GET /api/financial/payable/analytics/`

**Description:** Get comprehensive analytics data for AP reports.

**Query Parameters:**
- `company_id` (optional): Company UUID

**Sample Request:**
```
GET /api/financial/payable/analytics/?company_id=<uuid>
```

**Sample Response:**
```json
{
  "spending_by_category": [
    {
      "category": "Office Supplies",
      "amount": 1800000.0,
      "amount_display": "₹18.00L",
      "percentage": 18.0,
      "color": "#3B82F6"
    },
    {
      "category": "Vehicle Fleet",
      "amount": 1600000.0,
      "amount_display": "₹16.00L",
      "percentage": 16.0,
      "color": "#10B981"
    },
    {
      "category": "Maintenance",
      "amount": 1400000.0,
      "amount_display": "₹14.00L",
      "percentage": 14.0,
      "color": "#F59E0B"
    }
  ],
  "monthly_trend": [
    {
      "month": "2025-07",
      "month_display": "Jul 2025",
      "billed": 0.0,
      "billed_display": "₹0.00L",
      "paid": 0.0,
      "paid_display": "₹0.00L"
    },
    {
      "month": "2025-08",
      "month_display": "Aug 2025",
      "billed": 1200000.0,
      "billed_display": "₹12.00L",
      "paid": 500000.0,
      "paid_display": "₹5.00L"
    },
    {
      "month": "2025-11",
      "month_display": "Nov 2025",
      "billed": 8000000.0,
      "billed_display": "₹80.00L",
      "paid": 2000000.0,
      "paid_display": "₹20.00L"
    }
  ],
  "top_vendors": [
    {
      "vendor_name": "ITC Limited",
      "amount": 2800000.0,
      "amount_display": "₹28.00L"
    },
    {
      "vendor_name": "Mahindra & Mahindra",
      "amount": 2500000.0,
      "amount_display": "₹25.00L"
    },
    {
      "vendor_name": "Asian Paints",
      "amount": 2000000.0,
      "amount_display": "₹20.00L"
    },
    {
      "vendor_name": "Godrej & Boyce",
      "amount": 1400000.0,
      "amount_display": "₹14.00L"
    },
    {
      "vendor_name": "Infosys Limited",
      "amount": 1000000.0,
      "amount_display": "₹10.00L"
    }
  ],
  "payment_methods": [
    {
      "payment_method": "Cheque",
      "amount": 4500000.0,
      "amount_display": "₹45.00L",
      "percentage": 45.0,
      "color": "#3B82F6"
    },
    {
      "payment_method": "RTGS",
      "amount": 3500000.0,
      "amount_display": "₹35.00L",
      "percentage": 35.0,
      "color": "#10B981"
    },
    {
      "payment_method": "NEFT",
      "amount": 800000.0,
      "amount_display": "₹8.00L",
      "percentage": 8.0,
      "color": "#F59E0B"
    },
    {
      "payment_method": "UPI",
      "amount": 200000.0,
      "amount_display": "₹2.00L",
      "percentage": 2.0,
      "color": "#EC4899"
    }
  ]
}
```

**Field Descriptions:**
- `spending_by_category`: Pie chart data showing spending distribution by category
- `monthly_trend`: Line chart data showing billed vs paid amounts over last 6 months
- `top_vendors`: Top 5 vendors by total spending
- `payment_methods`: Pie chart data showing payment method distribution

---

## AP Dashboard

**Endpoint:** `GET /api/financial/payable/dashboard/`

**Description:** Get comprehensive AP dashboard with KPIs, health status, and insights.

**Query Parameters:**
- `company_id` (optional): Company UUID

**Sample Request:**
```
GET /api/financial/payable/dashboard/?company_id=<uuid>
```

**Sample Response:**
```json
{
  "kpis": {
    "total_payables": 9699000.0,
    "total_payables_display": "₹96.99L",
    "outstanding_balance_percentage": 50.2,
    "dpo": 224,
    "avg_payment_time_percentage": 0.0,
    "payment_efficiency": 100.0,
    "on_time_payment_rate": 100.0,
    "overdue_amount": 4870000.0,
    "overdue_amount_display": "₹48.70L",
    "overdue_bills_count": 13,
    "overdue_percentage": 50.2,
    "discounts_captured": 13840.0,
    "discounts_captured_display": "₹13.84K",
    "early_payment_savings_percentage": 0.0,
    "total_bills": 30,
    "all_vendor_bills_percentage": 0.0
  },
  "ap_health_status": {
    "status": "Needs Attention",
    "on_time_payment_rate": 100.0,
    "status_message": "100% on-time payments"
  },
  "ageing_distribution": {
    "current": 4830000.0,
    "current_display": "₹48.30L",
    "overdue": 4870000.0,
    "overdue_display": "₹48.70L"
  },
  "key_insights": [
    {
      "text": "13 overdue bills",
      "type": "danger",
      "color": "#EF4444"
    },
    {
      "text": "High DPO (224 days)",
      "type": "warning",
      "color": "#6B7280"
    },
    {
      "text": "₹13.84K saved",
      "type": "success",
      "color": "#3B82F6"
    },
    {
      "text": "Excellent payment record",
      "type": "success",
      "color": "#10B981"
    }
  ],
  "ageing_breakdown": {
    "current": 4830000.0,
    "current_display": "₹48.30L",
    "days_1_30": 2368000.0,
    "days_1_30_display": "₹23.68L",
    "days_31_60": 2502000.0,
    "days_31_60_display": "₹25.02L",
    "days_61_90": 0.0,
    "days_61_90_display": "₹0.00L",
    "days_90_plus": 0.0,
    "days_90_plus_display": "₹0.00L"
  }
}
```

**Field Descriptions:**
- `kpis`: Key performance indicators including total payables, DPO, payment efficiency, overdue amounts, discounts, and bill counts
- `ap_health_status`: Overall AP health status (Healthy, Needs Attention, Critical)
- `ageing_distribution`: Current vs Overdue amounts
- `key_insights`: Dynamic insights based on metrics
- `ageing_breakdown`: Detailed breakdown by time periods

**KPI Metrics:**
- `total_payables`: Total outstanding accounts payable
- `dpo`: Days Payable Outstanding (average days to pay bills)
- `payment_efficiency`: Percentage of payments made on time
- `overdue_amount`: Total amount of overdue bills
- `discounts_captured`: Total discounts captured from early payments

---

## Error Responses

All APIs may return the following error responses:

### 400 Bad Request
```json
{
  "error": "Validation error",
  "details": {
    "field_name": ["Error message"]
  }
}
```

### 401 Unauthorized
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 404 Not Found
```json
{
  "error": "Resource not found"
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal server error"
}
```

---

## Authentication

All APIs require authentication. Include the authentication token in the request headers:

```
Authorization: Bearer <token>
```

---

## Notes

1. All amounts are in Indian Rupees (₹)
2. Amounts are formatted as "L" (Lakhs) for values >= ₹1,00,000 and "K" (Thousands) for smaller values
3. Dates are in ISO 8601 format (YYYY-MM-DD)
4. UUIDs are used for all ID fields
5. The `company_id` query parameter is optional if the user owns only one company
6. Bill statuses: PENDING, PARTIAL, PAID, OVERDUE, CANCELLED
7. Payment methods: Bank Transfer, NEFT, RTGS, IMPS, Cheque, UPI, Cash, Credit Card


