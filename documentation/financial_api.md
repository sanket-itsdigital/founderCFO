# Financial API Documentation

This document provides comprehensive API documentation for the Financial module, including Invoices, AR Ageing, Customer Balance, and Customer Segments.

## Base URL
```
/api/financial/
```

## Authentication
All endpoints require authentication. Include the authentication token in the request headers:
```
Authorization: Token <your_token>
```

## Query Parameters
Most endpoints accept an optional `company_id` query parameter:
```
?company_id=<uuid>
```
If not provided, the API will use the first company owned by the authenticated user.

---

## 1. Invoices API

### 1.1 List Invoices
Get a list of all invoices for a company.

**Endpoint:** `GET /api/financial/invoices/`

**Query Parameters:**
- `company_id` (optional): UUID of the company
- `status` (optional): Filter by invoice status (Draft, Pending, Partial, Paid, Overdue, Cancelled, Bad Debt)
- `customer_name` (optional): Filter by customer name (partial match)
- `invoice_number` (optional): Filter by invoice number (partial match)

**Request Example:**
```http
GET /api/financial/invoices/?company_id=123e4567-e89b-12d3-a456-426614174000&status=Pending
```

**Response Example:**
```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174001",
    "company": "123e4567-e89b-12d3-a456-426614174000",
    "invoice_number": "INV-2024-001",
    "customer_name": "CloudFirst Pvt Ltd",
    "invoice_date": "2024-01-15",
    "payment_terms": "Net 30",
    "payment_terms_display": "Net 30",
    "due_date": "2024-02-14",
    "subtotal_amount": "2500000.00",
    "tax_amount": "450000.00",
    "discount_amount": "0.00",
    "total_amount": "2950000.00",
    "total_amount_display": "₹29.50L",
    "paid_amount": "0.00",
    "paid_amount_display": "₹0.00L",
    "balance_amount": "2950000.00",
    "balance_amount_display": "₹29.50L",
    "category": "Services",
    "category_display": "Services",
    "status": "Pending",
    "status_display": "Pending",
    "sales_order_reference": "SO-2024-001",
    "notes": "Monthly service invoice",
    "is_overdue": false,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
]
```

### 1.2 Create Invoice
Create a new invoice.

**Endpoint:** `POST /api/financial/invoices/`

**Request Payload:**
```json
{
  "invoice_number": "INV-2024-002",
  "customer_name": "Digital Dynamics",
  "invoice_date": "2024-01-20",
  "payment_terms": "Net 30",
  "due_date": "2024-02-19",
  "subtotal_amount": "5000000.00",
  "tax_amount": "900000.00",
  "discount_amount": "0.00",
  "total_amount": "5900000.00",
  "paid_amount": "0.00",
  "category": "Products Sales",
  "status": "Draft",
  "sales_order_reference": "SO-2024-002",
  "notes": "Product delivery invoice"
}
```

**Field Descriptions:**
- `invoice_number` (required): Unique invoice number (must be unique per company)
- `customer_name` (required): Name of the customer
- `invoice_date` (required): Date of the invoice (YYYY-MM-DD)
- `payment_terms` (optional): Payment terms (COD, Net 7, Net 15, Net 30, Net 45, Net 60, Net 90)
- `due_date` (required): Due date for payment (YYYY-MM-DD)
- `subtotal_amount` (required): Subtotal amount before tax and discount
- `tax_amount` (optional): Tax amount (default: 0.00)
- `discount_amount` (optional): Discount amount (default: 0.00)
- `total_amount` (optional): Total amount (auto-calculated if not provided: subtotal + tax - discount)
- `paid_amount` (optional): Amount paid (default: 0.00)
- `category` (optional): Invoice category (Products Sales, Services, Subscriptions, Consulting, Maintenance, Other)
- `status` (optional): Invoice status (default: Draft)
- `sales_order_reference` (optional): Reference to sales order
- `notes` (optional): Additional notes

**Response Example:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174002",
  "company": "123e4567-e89b-12d3-a456-426614174000",
  "invoice_number": "INV-2024-002",
  "customer_name": "Digital Dynamics",
  "invoice_date": "2024-01-20",
  "payment_terms": "Net 30",
  "payment_terms_display": "Net 30",
  "due_date": "2024-02-19",
  "subtotal_amount": "5000000.00",
  "tax_amount": "900000.00",
  "discount_amount": "0.00",
  "total_amount": "5900000.00",
  "total_amount_display": "₹59.00L",
  "paid_amount": "0.00",
  "paid_amount_display": "₹0.00L",
  "balance_amount": "5900000.00",
  "balance_amount_display": "₹59.00L",
  "category": "Products Sales",
  "category_display": "Products Sales",
  "status": "Draft",
  "status_display": "Draft",
  "sales_order_reference": "SO-2024-002",
  "notes": "Product delivery invoice",
  "is_overdue": false,
  "created_at": "2024-01-20T10:30:00Z",
  "updated_at": "2024-01-20T10:30:00Z"
}
```

### 1.3 Get Invoice Details
Retrieve details of a specific invoice.

**Endpoint:** `GET /api/financial/invoices/<id>/`

**Response Example:** Same as Create Invoice response

### 1.4 Update Invoice
Update an existing invoice.

**Endpoint:** `PUT /api/financial/invoices/<id>/` or `PATCH /api/financial/invoices/<id>/`

**Request Payload:** Same fields as Create Invoice (all fields required for PUT, only changed fields for PATCH)

**Response Example:** Same as Create Invoice response

### 1.5 Delete Invoice
Delete an invoice.

**Endpoint:** `DELETE /api/financial/invoices/<id>/`

**Response:** `204 No Content`

---

## 2. AR Dashboard API

Get comprehensive Accounts Receivable dashboard with all KPIs, health status, and analytics.

**Endpoint:** `GET /api/financial/ar-dashboard/`

**Query Parameters:**
- `company_id` (optional): UUID of the company

**Request Example:**
```http
GET /api/financial/ar-dashboard/?company_id=123e4567-e89b-12d3-a456-426614174000
```

**Response Example:**
```json
{
  "kpis": {
    "total_receivables": 21200000.00,
    "total_receivables_display": "₹2.12Cr",
    "total_receivables_trend": null,
    "dso": 105,
    "collection_efficiency": 36.0,
    "overdue_ar": 16400000.00,
    "overdue_ar_percentage": 77.4,
    "overdue_ar_display": "₹1.64Cr",
    "avg_days_delinquent": 53,
    "this_month_collections": 866000.00,
    "this_month_collections_display": "₹8.66L",
    "this_month_collections_trend": null,
    "invoice_status": {
      "total": 30,
      "paid": 8,
      "pending": 4,
      "overdue": 18
    }
  },
  "ar_health_status": {
    "status": "Needs Attention",
    "total_receivables": 21200000.00,
    "total_receivables_display": "₹2.12Cr",
    "metrics": {
      "dso": 105,
      "dso_target": 30,
      "dso_status": "High",
      "collection_efficiency": 36.0,
      "collection_efficiency_status": "Low",
      "overdue_amount": 16400000.00,
      "overdue_amount_display": "₹1.64Cr",
      "overdue_percentage": 77.4,
      "top_customer_concentration": 18.5,
      "top_customer_name": "Digital Dynamics",
      "top_customer_status": "Diversified"
    }
  },
  "ageing_distribution": [
    {
      "label": "Current",
      "amount": 4830000.00,
      "amount_display": "₹48.30L",
      "percentage": 22.8,
      "color": "green"
    },
    {
      "label": "1-30 Days",
      "amount": 0.00,
      "amount_display": "₹0.00L",
      "percentage": 0.0,
      "color": "blue"
    },
    {
      "label": "31-60 Days",
      "amount": 0.00,
      "amount_display": "₹0.00L",
      "percentage": 0.0,
      "color": "orange"
    },
    {
      "label": "61-90 Days",
      "amount": 0.00,
      "amount_display": "₹0.00L",
      "percentage": 0.0,
      "color": "red"
    },
    {
      "label": "90+ Days",
      "amount": 0.00,
      "amount_display": "₹0.00L",
      "percentage": 0.0,
      "color": "dark_red"
    }
  ],
  "priority_actions": {
    "critical_count": 3,
    "due_this_week_count": 0,
    "collected_this_month": 866000.00,
    "collected_this_month_display": "₹8.66L"
  },
  "top_customers": [
    {
      "customer_name": "Digital Dynamics",
      "invoice_count": 4,
      "outstanding": 6100954.00,
      "outstanding_display": "₹61.01L",
      "percentage": 28.8
    },
    {
      "customer_name": "Innovate Systems",
      "invoice_count": 4,
      "outstanding": 4369066.00,
      "outstanding_display": "₹43.69L",
      "percentage": 20.6
    },
    {
      "customer_name": "CloudFirst Pvt Ltd",
      "invoice_count": 2,
      "outstanding": 2659202.00,
      "outstanding_display": "₹26.59L",
      "percentage": 12.5
    },
    {
      "customer_name": "Acme Technologies Pvt Ltd",
      "invoice_count": 3,
      "outstanding": 3365994.00,
      "outstanding_display": "₹33.66L",
      "percentage": 15.9
    },
    {
      "customer_name": "Quantum Computing Ltd",
      "invoice_count": 1,
      "outstanding": 1020516.00,
      "outstanding_display": "₹10.21L",
      "percentage": 4.8
    }
  ],
  "collection_trend": [
    {
      "month": "Jun",
      "collected": 1500000.00,
      "collected_display": "₹15.00L",
      "invoiced": 5000000.00,
      "invoiced_display": "₹50.00L"
    },
    {
      "month": "Jul",
      "collected": 2000000.00,
      "collected_display": "₹20.00L",
      "invoiced": 6000000.00,
      "invoiced_display": "₹60.00L"
    },
    {
      "month": "Aug",
      "collected": 1800000.00,
      "collected_display": "₹18.00L",
      "invoiced": 5500000.00,
      "invoiced_display": "₹55.00L"
    },
    {
      "month": "Sep",
      "collected": 1580000.00,
      "collected_display": "₹15.80L",
      "invoiced": 4670000.00,
      "invoiced_display": "₹46.70L"
    },
    {
      "month": "Oct",
      "collected": 1200000.00,
      "collected_display": "₹12.00L",
      "invoiced": 4500000.00,
      "invoiced_display": "₹45.00L"
    },
    {
      "month": "Nov",
      "collected": 866000.00,
      "collected_display": "₹8.66L",
      "invoiced": 4000000.00,
      "invoiced_display": "₹40.00L"
    }
  ]
}
```

**Response Fields:**

### KPIs Section
- `total_receivables`: Total outstanding receivables (float)
- `total_receivables_display`: Formatted in crores (₹XX.XXCr)
- `total_receivables_trend`: Trend indicator (null for now, can be "up", "down", or percentage)
- `dso`: Days Sales Outstanding (integer)
- `collection_efficiency`: Collection efficiency percentage (float)
- `overdue_ar`: Overdue AR amount (float)
- `overdue_ar_percentage`: Percentage of total receivables that are overdue (float)
- `overdue_ar_display`: Formatted overdue AR in crores (₹XX.XXCr)
- `avg_days_delinquent`: Average days delinquent for overdue invoices (integer)
- `this_month_collections`: Collections this month (float)
- `this_month_collections_display`: Formatted collections in lakhs (₹XX.XXL)
- `this_month_collections_trend`: Trend indicator (null for now)
- `invoice_status`: Object with counts:
  - `total`: Total invoices (integer)
  - `paid`: Paid invoices count (integer)
  - `pending`: Pending invoices count (integer)
  - `overdue`: Overdue invoices count (integer)

### AR Health Status Section
- `status`: Overall health status ("Healthy", "Needs Attention", "Critical")
- `total_receivables`: Total receivables (float)
- `total_receivables_display`: Formatted total (₹XX.XXCr)
- `metrics`: Detailed metrics object:
  - `dso`: Days Sales Outstanding (integer)
  - `dso_target`: Target DSO (default: 30 days)
  - `dso_status`: Status label ("High", "Normal", "Low")
  - `collection_efficiency`: Collection efficiency percentage (float)
  - `collection_efficiency_status`: Status label ("High", "Normal", "Low")
  - `overdue_amount`: Overdue amount (float)
  - `overdue_amount_display`: Formatted overdue amount (₹XX.XXCr)
  - `overdue_percentage`: Overdue percentage (float)
  - `top_customer_concentration`: Top customer's percentage of total receivables (float)
  - `top_customer_name`: Name of top customer (string)
  - `top_customer_status`: Concentration status ("Diversified", "Concentrated", "High Risk")

### Ageing Distribution Section
- Array of ageing buckets with:
  - `label`: Bucket label (Current, 1-30 Days, 31-60 Days, 61-90 Days, 90+ Days)
  - `amount`: Amount in this bucket (float)
  - `amount_display`: Formatted amount (₹XX.XXL)
  - `percentage`: Percentage of total receivables (float)
  - `color`: Color code for visualization (green, blue, orange, red, dark_red)

### Priority Actions Section
- `critical_count`: Number of invoices 90+ days overdue (integer)
- `due_this_week_count`: Number of invoices due this week (integer)
- `collected_this_month`: Collections this month (float)
- `collected_this_month_display`: Formatted collections (₹XX.XXL)

### Top Customers Section
- Array of top 5 customers by outstanding amount:
  - `customer_name`: Customer name (string)
  - `invoice_count`: Number of invoices (integer)
  - `outstanding`: Outstanding amount (float)
  - `outstanding_display`: Formatted amount (₹XX.XXL)
  - `percentage`: Percentage of total receivables (float)

### Collection Trend Section
- Array of monthly data (last 6 months):
  - `month`: Month abbreviation (string)
  - `collected`: Amount collected (float)
  - `collected_display`: Formatted collected amount (₹XX.XXL)
  - `invoiced`: Amount invoiced (float)
  - `invoiced_display`: Formatted invoiced amount (₹XX.XXL)

---

## 3. AR Ageing Summary API

Get Accounts Receivable ageing summary with breakdown by ageing buckets.

**Endpoint:** `GET /api/financial/ar-ageing-summary/`

**Query Parameters:**
- `company_id` (optional): UUID of the company

**Request Example:**
```http
GET /api/financial/ar-ageing-summary/?company_id=123e4567-e89b-12d3-a456-426614174000
```

**Response Example:**
```json
{
  "total_ar": 15000000.00,
  "total_ar_display": "₹150.00L",
  "overdue_percentage": 45.5,
  "portfolio_health": "Moderate Risk - Monitor closely",
  "ageing_buckets": [
    {
      "label": "Current",
      "amount": 5500000.00,
      "amount_display": "₹55.00L",
      "percentage": 36.67
    },
    {
      "label": "1-30 Days",
      "amount": 3000000.00,
      "amount_display": "₹30.00L",
      "percentage": 20.00
    },
    {
      "label": "31-60 Days",
      "amount": 2500000.00,
      "amount_display": "₹25.00L",
      "percentage": 16.67
    },
    {
      "label": "61-90 Days",
      "amount": 2000000.00,
      "amount_display": "₹20.00L",
      "percentage": 13.33
    },
    {
      "label": "90+ Days",
      "amount": 2000000.00,
      "amount_display": "₹20.00L",
      "percentage": 13.33
    }
  ]
}
```

**Response Fields:**
- `total_ar`: Total outstanding AR amount (float)
- `total_ar_display`: Formatted total AR in lakhs (₹XX.XXL)
- `overdue_percentage`: Percentage of AR that is overdue (float)
- `portfolio_health`: Health indicator based on overdue percentage:
  - "Healthy - Minimal risk" (< 30%)
  - "Low Risk - Standard monitoring" (30-50%)
  - "Moderate Risk - Monitor closely" (50-70%)
  - "At Risk - Prioritize collections" (≥ 70%)
- `ageing_buckets`: Array of ageing buckets with:
  - `label`: Bucket label (Current, 1-30 Days, 31-60 Days, 61-90 Days, 90+ Days)
  - `amount`: Amount in this bucket (float)
  - `amount_display`: Formatted amount in lakhs (₹XX.XXL)
  - `percentage`: Percentage of total AR in this bucket (float)

---

## 4. Customer Balance Summary API

Get customer balance summary with outstanding amounts, credit limits, and utilization.

**Endpoint:** `GET /api/financial/customers/balance-summary/`

**Query Parameters:**
- `company_id` (optional): UUID of the company

**Request Example:**
```http
GET /api/financial/customers/balance-summary/?company_id=123e4567-e89b-12d3-a456-426614174000
```

**Response Example:**
```json
{
  "total_customers": 3,
  "customers": [
    {
      "customer_name": "CloudFirst Pvt Ltd",
      "outstanding": 2659202.00,
      "outstanding_display": "₹26.59L",
      "credit_limit": 500000.00,
      "credit_limit_display": "₹5.00L",
      "utilization": 531.8,
      "invoices": 2,
      "avg_days": 45
    },
    {
      "customer_name": "Digital Dynamics",
      "outstanding": 6100954.00,
      "outstanding_display": "₹61.01L",
      "credit_limit": 500000.00,
      "credit_limit_display": "₹5.00L",
      "utilization": 1220.2,
      "invoices": 4,
      "avg_days": 60
    },
    {
      "customer_name": "Acme Technologies Pvt Ltd",
      "outstanding": 3365994.00,
      "outstanding_display": "₹33.66L",
      "credit_limit": 500000.00,
      "credit_limit_display": "₹5.00L",
      "utilization": 673.2,
      "invoices": 3,
      "avg_days": 30
    }
  ],
  "summary": {
    "total_outstanding": 12126150.00,
    "total_outstanding_display": "₹1.21Cr",
    "high_utilization": 3,
    "slow_payers": 2
  }
}
```

**Response Fields:**
- `total_customers`: Total number of customers with outstanding invoices (integer)
- `customers`: Array of customer objects with:
  - `customer_name`: Name of the customer (string)
  - `outstanding`: Outstanding amount (float)
  - `outstanding_display`: Formatted outstanding amount in lakhs (₹XX.XXL)
  - `credit_limit`: Credit limit for the customer (float, default: ₹5,00,000)
  - `credit_limit_display`: Formatted credit limit in lakhs (₹XX.XXL)
  - `utilization`: Credit utilization percentage (float)
  - `invoices`: Number of outstanding invoices (integer)
  - `avg_days`: Average days outstanding based on oldest invoice (integer)
- `summary`: Summary statistics with:
  - `total_outstanding`: Total outstanding amount across all customers (float)
  - `total_outstanding_display`: Formatted total outstanding in crores (₹XX.XXCr)
  - `high_utilization`: Number of customers with ≥100% credit utilization (integer)
  - `slow_payers`: Number of customers with ≥45 days outstanding (integer)

---

## 5. Customer Segments API

Get customer segments based on payment behavior with detailed analytics.

**Endpoint:** `GET /api/financial/customers/segments/`

**Query Parameters:**
- `company_id` (optional): UUID of the company

**Request Example:**
```http
GET /api/financial/customers/segments/?company_id=123e4567-e89b-12d3-a456-426614174000
```

**Response Example:**
```json
{
  "segments": [
    {
      "segment_name": "Premium Payers",
      "customer_count": 1,
      "total_revenue": 1307788.00,
      "total_revenue_display": "₹13.08L",
      "avg_payment_days": 15,
      "risk_level": "Low Risk",
      "characteristics": [
        "Pay within 15 days",
        "< 10% overdue rate",
        "High revenue"
      ],
      "customers": [
        {
          "customer_name": "PrimeVentures",
          "invoice_count": 2,
          "total_revenue": 1307788.00,
          "total_revenue_display": "₹13.08L",
          "avg_payment_days": 15,
          "risk_level": "Low Risk"
        }
      ]
    },
    {
      "segment_name": "Reliable Partners",
      "customer_count": 3,
      "total_revenue": 7045712.00,
      "total_revenue_display": "₹70.46L",
      "avg_payment_days": 30,
      "risk_level": "Low Risk",
      "characteristics": [
        "Pay within terms",
        "< 20% overdue rate",
        "Consistent"
      ],
      "customers": [
        {
          "customer_name": "CloudFirst Pvt Ltd",
          "invoice_count": 2,
          "total_revenue": 2659202.00,
          "total_revenue_display": "₹26.59L",
          "avg_payment_days": 16,
          "risk_level": "Low Risk"
        },
        {
          "customer_name": "Acme Technologies Pvt Ltd",
          "invoice_count": 3,
          "total_revenue": 3365994.00,
          "total_revenue_display": "₹33.66L",
          "avg_payment_days": 30,
          "risk_level": "Low Risk"
        },
        {
          "customer_name": "Quantum Computing Ltd",
          "invoice_count": 1,
          "total_revenue": 1020516.00,
          "total_revenue_display": "₹10.21L",
          "avg_payment_days": 30,
          "risk_level": "Low Risk"
        }
      ]
    },
    {
      "segment_name": "Watch List",
      "customer_count": 0,
      "total_revenue": 0.0,
      "total_revenue_display": "₹0.00L",
      "avg_payment_days": 0,
      "risk_level": "Medium Risk",
      "characteristics": [
        "Pay 30-45 days",
        "20-40% overdue rate",
        "Need monitoring"
      ],
      "customers": []
    },
    {
      "segment_name": "High Risk",
      "customer_count": 8,
      "total_revenue": 21688752.00,
      "total_revenue_display": "₹216.89L",
      "avg_payment_days": 27,
      "risk_level": "High Risk",
      "characteristics": [
        "Pay > 45 days",
        "> 40% overdue rate",
        "Credit risk"
      ],
      "customers": [
        {
          "customer_name": "Digital Dynamics",
          "invoice_count": 4,
          "total_revenue": 6100954.00,
          "total_revenue_display": "₹61.01L",
          "avg_payment_days": 105,
          "risk_level": "High Risk"
        },
        {
          "customer_name": "Innovate Systems",
          "invoice_count": 4,
          "total_revenue": 4369066.00,
          "total_revenue_display": "₹43.69L",
          "avg_payment_days": 30,
          "risk_level": "High Risk"
        }
      ]
    }
  ],
  "segment_details": [
    {
      "segment": "Premium Payers",
      "customers": 1,
      "total_revenue": 1307788.00,
      "total_revenue_display": "₹13.08L",
      "avg_payment_days": 15,
      "risk_level": "Low Risk",
      "characteristics": [
        "Pay within 15 days",
        "< 10% overdue rate",
        "High revenue"
      ]
    },
    {
      "segment": "Reliable Partners",
      "customers": 3,
      "total_revenue": 7045712.00,
      "total_revenue_display": "₹70.46L",
      "avg_payment_days": 30,
      "risk_level": "Low Risk",
      "characteristics": [
        "Pay within terms",
        "< 20% overdue rate",
        "Consistent"
      ]
    },
    {
      "segment": "Watch List",
      "customers": 0,
      "total_revenue": 0.0,
      "total_revenue_display": "₹0.00L",
      "avg_payment_days": 0,
      "risk_level": "Medium Risk",
      "characteristics": [
        "Pay 30-45 days",
        "20-40% overdue rate",
        "Need monitoring"
      ]
    },
    {
      "segment": "High Risk",
      "customers": 8,
      "total_revenue": 21688752.00,
      "total_revenue_display": "₹216.89L",
      "avg_payment_days": 27,
      "risk_level": "High Risk",
      "characteristics": [
        "Pay > 45 days",
        "> 40% overdue rate",
        "Credit risk"
      ]
    }
  ],
  "customer_distribution": {
    "Premium Payers": 1,
    "Reliable Partners": 3,
    "Watch List": 0,
    "High Risk": 8
  },
  "revenue_by_segment": {
    "Premium Payers": 1307788.00,
    "Reliable Partners": 7045712.00,
    "Watch List": 0.0,
    "High Risk": 21688752.00
  }
}
```

**Response Fields:**

### Segments Array
- `segments`: Array of segment objects with full details including customer list:
  - `segment_name`: Name of the segment (string)
  - `customer_count`: Number of customers in this segment (integer)
  - `total_revenue`: Total revenue from this segment (float)
  - `total_revenue_display`: Formatted revenue in lakhs (₹XX.XXL)
  - `avg_payment_days`: Average payment days for the segment (integer)
  - `risk_level`: Risk level (Low Risk, Medium Risk, High Risk)
  - `characteristics`: Array of characteristic strings
  - `customers`: Array of customer objects with:
    - `customer_name`: Customer name (string)
    - `invoice_count`: Number of invoices (integer)
    - `total_revenue`: Total revenue from this customer (float)
    - `total_revenue_display`: Formatted revenue (₹XX.XXL)
    - `avg_payment_days`: Average payment days (integer)
    - `risk_level`: Risk level (string)

### Segment Details Array
- `segment_details`: Array of segment summary objects (for table display):
  - `segment`: Segment name (string)
  - `customers`: Number of customers (integer)
  - `total_revenue`: Total revenue (float)
  - `total_revenue_display`: Formatted revenue (₹XX.XXL)
  - `avg_payment_days`: Average payment days (integer)
  - `risk_level`: Risk level (string)
  - `characteristics`: Array of characteristic strings

### Distribution Data
- `customer_distribution`: Object with customer count per segment (key: segment name, value: count)
- `revenue_by_segment`: Object with revenue per segment (key: segment name, value: revenue amount)

**Segment Classification Logic:**
1. **Premium Payers**: Pay ≤15 days AND <10% overdue rate
2. **Reliable Partners**: Pay ≤30 days AND <20% overdue rate (but not Premium Payers)
3. **Watch List**: Pay 30-45 days OR 20-40% overdue rate (but not High Risk)
4. **High Risk**: Pay >45 days OR >40% overdue rate

---

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request
```json
{
  "error": "Invalid request data",
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
  "detail": "Not found."
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal server error"
}
```

---

## Notes

1. **Amount Formatting**: All amounts are returned as floats, with display formats in lakhs (₹XX.XXL) or crores (₹XX.XXCr) for readability.

2. **Date Format**: All dates are in ISO 8601 format (YYYY-MM-DD).

3. **Payment Terms**: Available options are: COD, Net 7, Net 15, Net 30, Net 45, Net 60, Net 90.

4. **Invoice Status**: Available statuses are: Draft, Pending, Partial, Paid, Overdue, Cancelled, Bad Debt.

5. **Invoice Category**: Available categories are: Products Sales, Services, Subscriptions, Consulting, Maintenance, Other.

6. **Company Selection**: If `company_id` is not provided, the API uses the first company owned by the authenticated user.

7. **Credit Limits**: Customer credit limits default to ₹5,00,000 and can be managed through the Credit model.

