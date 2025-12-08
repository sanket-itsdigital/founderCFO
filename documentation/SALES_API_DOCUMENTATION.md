# Sales API Documentation

Complete API payload documentation for all Sales endpoints.

**Base URL:** `/api/sales/`

**Authentication:** All endpoints require JWT authentication. Include the token in the Authorization header:
```
Authorization: Bearer <access_token>
```

---

## 1. Sales Overview API

### GET `/api/sales/overview/`

Get comprehensive sales dashboard data including summary cards, pipeline health, KPIs, funnel, and leaderboard.

**Query Parameters:**
- `period` (optional, string): Time period filter. Options: `"7"`, `"30"`, `"90"`, `"365"`, `"year"`, `"quarter"`. Default: `"30"`
- `funnel_period` (optional, boolean): If `true`, funnel uses period-based data; if `false`, uses all-time data. Default: `"false"`
- `leaderboard_limit` (optional, integer): Number of top performers to return. Default: `5`
- `pipeline_stage` (optional, string): Filter pipeline overview by stage. Options: `"Discovery"`, `"Qualification"`, `"Proposal"`, `"Negotiation"`, `"Closed Won"`, `"Closed Lost"`, `"Unqualified"`, or `"All Stages"`. Default: `null` (all stages)
- `pipeline_search` (optional, string): Search deals by deal name, client, deal ID, or sales team name
- `pipeline_limit` (optional, integer): Limit number of pipeline deals returned. Default: `10`

**Response (200 OK):**
```json
{
  "summary_cards": [
    {
      "title": "Quota",
      "value": 31000000.0,
      "value_display": "₹3.10Cr",
      "subtitle": "",
      "icon": "target"
    },
    {
      "title": "Closed",
      "value": 15000000.0,
      "value_display": "₹1.50Cr",
      "subtitle": "48%",
      "icon": "checkmark"
    },
    {
      "title": "Commit",
      "value": 8000000.0,
      "value_display": "₹80.00L",
      "subtitle": "26%",
      "icon": "trend-up"
    },
    {
      "title": "Best Case",
      "value": 5000000.0,
      "value_display": "₹50.00L",
      "subtitle": "",
      "icon": "trend-up"
    }
  ],
  "gap_card": {
    "title": "Gap",
    "value": 8000000.0,
    "value_display": "₹80.00L",
    "subtitle": "",
    "icon": "warning",
    "gap": 8000000.0,
    "gap_display": "₹80.00L"
  },
  "pipeline_health": {
    "health_score": 72,
    "health_status": "Good",
    "open_deals": 15,
    "pipeline_value": 25000000.0,
    "pipeline_value_display": "₹2.50Cr",
    "avg_velocity": 25.5,
    "avg_velocity_display": "25.5 days",
    "stalled_deals": 3,
    "stalled_amount": 5000000.0,
    "stalled_amount_display": "₹50.00L",
    "critical_count": 2
  },
  "kpi_cards": [
    {
      "title": "Total Revenue (ARR)",
      "value": "180000000.0",
      "value_display": "₹18.00Cr",
      "subtitle": "Annual Recurring Revenue",
      "icon": "dollar",
      "icon_color": "blue"
    },
    {
      "title": "Monthly Recurring Revenue",
      "value": "15000000.0",
      "value_display": "₹1.50Cr",
      "subtitle": "MRR growth trajectory",
      "icon": "trend-up",
      "icon_color": "green"
    },
    {
      "title": "Win Rate",
      "value": "65.5",
      "value_display": "65.5%",
      "subtitle": "Opportunities closed won",
      "icon": "target",
      "icon_color": "purple"
    },
    {
      "title": "Sales Velocity",
      "value": "45.2",
      "value_display": "45.2 days",
      "subtitle": "Daily revenue generation rate",
      "icon": "trend-up",
      "icon_color": "green"
    },
    {
      "title": "Average Deal Size",
      "value": "500000.0",
      "value_display": "₹5.00L",
      "subtitle": "Mean contract value",
      "icon": "dollar",
      "icon_color": "pink"
    },
    {
      "title": "Pipeline Coverage",
      "value": "0.8",
      "value_display": "0.8x",
      "subtitle": "Pipeline vs quarterly target",
      "icon": "bar-chart",
      "icon_color": "purple"
    }
  ],
  "sales_funnel": [
    {
      "stage": "Discovery",
      "deals_count": 5,
      "amount": 5000000.0,
      "amount_display": "₹50.00L"
    },
    {
      "stage": "Qualification",
      "deals_count": 4,
      "amount": 8000000.0,
      "amount_display": "₹80.00L"
    },
    {
      "stage": "Proposal",
      "deals_count": 3,
      "amount": 6000000.0,
      "amount_display": "₹60.00L"
    },
    {
      "stage": "Negotiation",
      "deals_count": 2,
      "amount": 4000000.0,
      "amount_display": "₹40.00L"
    },
    {
      "stage": "Closed Won",
      "deals_count": 10,
      "amount": 15000000.0,
      "amount_display": "₹1.50Cr"
    }
  ],
  "sales_leaderboard": [
    {
      "rank": 1,
      "rep_name": "John Doe",
      "deals_closed": 5,
      "revenue": 8000000.0,
      "revenue_display": "₹80.00L",
      "quota_attainment": 120.0,
      "quota_attainment_display": "120%"
    },
    {
      "rank": 2,
      "rep_name": "Jane Smith",
      "deals_closed": 4,
      "revenue": 6000000.0,
      "revenue_display": "₹60.00L",
      "quota_attainment": 95.0,
      "quota_attainment_display": "95%"
    }
  ],
  "pipeline_overview": {
    "title": "Pipeline Overview",
    "deals": [
      {
        "deal_id": "550e8400-e29b-41d4-a716-446655440000",
        "account_name": "Acme Corporation",
        "owner": "John Doe",
        "product": "Enterprise",
        "amount": 2000000.0,
        "amount_display": "₹20.00L",
        "mrr": 166666.67,
        "mrr_display": "₹1.67L",
        "stage": "Negotiation",
        "probability": 70.0,
        "probability_display": "70%",
        "close_date": "2024-12-31",
        "close_date_display": "31 Dec 2024",
        "status": "Open"
      }
    ],
    "total_count": 25,
    "filtered_count": 10
  }
}
```

---

## 2. Pipeline Overview API

### GET `/api/sales/overview/pipeline/`

Get list of all deals in pipeline table format.

**Query Parameters:**
- `stage` (optional, string): Filter by stage. Options: `"Discovery"`, `"Qualification"`, `"Proposal"`, `"Negotiation"`, `"Closed Won"`, `"Closed Lost"`, `"Unqualified"`, or `"All Stages"`. Default: `null` (all stages)
- `search` (optional, string): Search deals by deal name, client, deal ID, or sales team name

**Response (200 OK):**
```json
{
  "title": "Pipeline Overview",
  "deals": [
    {
      "deal_id": "550e8400-e29b-41d4-a716-446655440000",
      "account_name": "Acme Corporation",
      "owner": "John Doe",
      "product": "Enterprise",
      "amount": 2000000.0,
      "amount_display": "₹2,000,000",
      "mrr": 166666.67,
      "mrr_display": "₹166,667",
      "stage": "Negotiation",
      "probability": 70.0,
      "probability_display": "70%",
      "close_date": "2024-12-31",
      "close_date_display": "31 Dec 2024",
      "status": "Open"
    }
  ],
  "total_count": 25
}
```

---

## 3. Create Deal API

### POST `/api/sales/overview/deals/create/`

Create a new deal in the sales pipeline.

**Request Body:**
```json
{
  "account_name": "Acme Corporation",
  "deal_owner_id": "660e8400-e29b-41d4-a716-446655440000",
  "product": "Enterprise",
  "expected_close_date": "2024-12-31",
  "deal_amount": "2000000.00",
  "monthly_recurring_revenue": "166666.67",
  "stage": "Negotiation",
  "probability": "70.00",
  "notes": "High priority deal with strong budget approval"
}
```

**Field Descriptions:**
- `account_name` (required, string): Name of the client/account
- `deal_owner_id` (optional, UUID): ID of the sales team member assigned to the deal
- `product` (optional, string): Product type. Options: `"Enterprise"`, `"Pro"`, `"Starter"`
- `expected_close_date` (required, date): Expected close date (YYYY-MM-DD)
- `deal_amount` (required, decimal): Total deal value (min: 0.00)
- `monthly_recurring_revenue` (optional, decimal): Monthly recurring revenue (MRR) (min: 0.00)
- `stage` (required, string): Current stage. Options: `"Discovery"`, `"Qualification"`, `"Proposal"`, `"Negotiation"`, `"Closed Won"`, `"Closed Lost"`, `"Unqualified"`
- `probability` (optional, decimal): Probability of closing (0.00-100.00). If not provided, defaults based on stage:
  - Discovery: 20%
  - Qualification: 30%
  - Proposal: 50%
  - Negotiation: 70%
  - Closed Won: 100%
- `notes` (optional, string): Additional notes about the deal

**Response (201 Created):**
```json
{
  "message": "Deal created successfully",
  "deal_id": "550e8400-e29b-41d4-a716-446655440000",
  "deal": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "deal_id": "DEAL1A2B3C",
    "deal_name": "Acme Corporation Deal",
    "account_name": "Acme Corporation",
    "owner": "John Doe",
    "product": "Enterprise",
    "amount": 2000000.0,
    "mrr": 166666.67,
    "stage": "Negotiation",
    "probability": 70.0,
    "close_date": "2024-12-31",
    "status": "Open"
  }
}
```

**Error Responses:**
- `400 Bad Request`: Invalid input data
- `404 Not Found`: Company or sales team member not found

---

## 4. Revenue Analytics API

### GET `/api/sales/revenue-analytics/`

Get combined revenue analytics including ARR summary, cohort performance, pipeline health, and sales performance.

**Query Parameters:**
- `period` (optional, string): Time period filter. Options: `"7"`, `"30"`, `"90"`, `"year"`. Default: `"30"`

**Response (200 OK):**
```json
{
  "arr_summary": {
    "new_arr": {
      "title": "New ARR (Period)",
      "value": 12000000.0,
      "value_display": "₹1.20Cr",
      "subtitle": "15 deals closed"
    },
    "expansion_arr": {
      "title": "Expansion ARR (Est.)",
      "value": 3000000.0,
      "value_display": "₹30.00L",
      "subtitle": "~25.00% expansion rate"
    },
    "churned_arr": {
      "title": "Churned ARR (Est.)",
      "value": 1000000.0,
      "value_display": "₹10.00L",
      "subtitle": "2 deals lost"
    },
    "net_new_arr": {
      "title": "Net New ARR",
      "value": 14000000.0,
      "value_display": "₹1.40Cr",
      "subtitle": "Growth momentum"
    }
  },
  "cohort_performance": {
    "title": "Customer Cohort Performance (Estimated)",
    "data": [
      {
        "period": "Q1 2024",
        "retention_percentage": 85.5,
        "expansion_percentage": 25.0,
        "churn_percentage": 14.5
      },
      {
        "period": "Q2 2024",
        "retention_percentage": 88.2,
        "expansion_percentage": 30.5,
        "churn_percentage": 11.8
      },
      {
        "period": "Q3 2024",
        "retention_percentage": 90.1,
        "expansion_percentage": 28.3,
        "churn_percentage": 9.9
      },
      {
        "period": "Q4 2024",
        "retention_percentage": 92.5,
        "expansion_percentage": 32.1,
        "churn_percentage": 7.5
      }
    ]
  },
  "pipeline_health": {
    "stages": [
      {
        "stage": "Negotiation",
        "opportunities": 5,
        "pipeline_value": 10000000.0,
        "pipeline_value_display": "₹1.00Cr",
        "conversion_rate": 80.0,
        "conversion_rate_display": "80.00%",
        "health_percentage": 80.0
      },
      {
        "stage": "Proposal",
        "opportunities": 8,
        "pipeline_value": 8000000.0,
        "pipeline_value_display": "₹80.00L",
        "conversion_rate": 62.5,
        "conversion_rate_display": "62.50%",
        "health_percentage": 62.5
      }
    ]
  },
  "sales_performance": {
    "summary_metrics": {
      "deals": 45,
      "reps": 8,
      "activities": 120
    },
    "arr_waterfall": {
      "title": "ARR Growth Waterfall (By Month)",
      "data": [
        {
          "month": "Jan",
          "new_revenue": 2000000.0,
          "new_revenue_display": "₹20.00L",
          "expansion": 500000.0,
          "expansion_display": "₹5.00L",
          "churn": 0.0,
          "churn_display": "₹0.00L",
          "total_arr": 2500000.0,
          "total_arr_display": "₹25.00L"
        },
        {
          "month": "Feb",
          "new_revenue": 3000000.0,
          "new_revenue_display": "₹30.00L",
          "expansion": 800000.0,
          "expansion_display": "₹8.00L",
          "churn": 200000.0,
          "churn_display": "₹2.00L",
          "total_arr": 6100000.0,
          "total_arr_display": "₹61.00L"
        }
      ]
    }
  }
}
```

---

## 5. Sales Forecast API

### GET `/api/sales/forecast/`

Get sales forecast data including summary cards, waterfall chart, monthly breakdown, and pipeline coverage.

**Query Parameters:**
- `period` (optional, string): Quarter period (e.g., `"Q4 FY25"`). If not provided, defaults to current quarter.

**Response (200 OK):**
```json
{
  "period": "Q4 FY25",
  "summary_cards": [
    {
      "title": "Quota",
      "value": 30000000.0,
      "value_display": "₹3.00Cr",
      "subtitle": "Q4 FY25",
      "icon": "target"
    },
    {
      "title": "Closed",
      "value": 12000000.0,
      "value_display": "₹1.20Cr",
      "subtitle": "40.00% of quota",
      "icon": "checkmark"
    },
    {
      "title": "Commit",
      "value": 10000000.0,
      "value_display": "₹1.00Cr",
      "subtitle": "High confidence",
      "icon": "trend-up"
    },
    {
      "title": "Best Case",
      "value": 5000000.0,
      "value_display": "₹50.00L",
      "subtitle": "60%+ probability",
      "icon": "bar-chart"
    },
    {
      "title": "Gap to Quota",
      "value": 3000000.0,
      "value_display": "₹30.00L",
      "subtitle": "10.00% gap remaining",
      "icon": "warning"
    }
  ],
  "forecast_waterfall": {
    "title": "Forecast Waterfall",
    "subtitle": "Path to quota achievement",
    "data": [
      {
        "category": "Closed",
        "value": 12000000.0,
        "value_display": "₹1.20Cr",
        "cumulative_value": 12000000.0,
        "cumulative_value_display": "₹1.20Cr"
      },
      {
        "category": "Commit",
        "value": 10000000.0,
        "value_display": "₹1.00Cr",
        "cumulative_value": 22000000.0,
        "cumulative_value_display": "₹2.20Cr"
      },
      {
        "category": "Best Case",
        "value": 5000000.0,
        "value_display": "₹50.00L",
        "cumulative_value": 27000000.0,
        "cumulative_value_display": "₹2.70Cr"
      },
      {
        "category": "Pipeline",
        "value": 3000000.0,
        "value_display": "₹30.00L",
        "cumulative_value": 30000000.0,
        "cumulative_value_display": "₹3.00Cr"
      }
    ],
    "quota": 30000000.0,
    "quota_display": "₹3.00Cr"
  },
  "monthly_breakdown": {
    "title": "Monthly Breakdown",
    "subtitle": "Expected close by month",
    "data": [
      {
        "month": "Oct 2024",
        "closed": 4000000.0,
        "closed_display": "₹40.00L",
        "commit": 3000000.0,
        "commit_display": "₹30.00L",
        "best_case": 2000000.0,
        "best_case_display": "₹20.00L",
        "pipeline": 1000000.0,
        "pipeline_display": "₹10.00L",
        "total": 10000000.0,
        "total_display": "₹1.00Cr"
      },
      {
        "month": "Nov 2024",
        "closed": 4000000.0,
        "closed_display": "₹40.00L",
        "commit": 3500000.0,
        "commit_display": "₹35.00L",
        "best_case": 1500000.0,
        "best_case_display": "₹15.00L",
        "pipeline": 1000000.0,
        "pipeline_display": "₹10.00L",
        "total": 10000000.0,
        "total_display": "₹1.00Cr"
      },
      {
        "month": "Dec 2024",
        "closed": 4000000.0,
        "closed_display": "₹40.00L",
        "commit": 3500000.0,
        "commit_display": "₹35.00L",
        "best_case": 1500000.0,
        "best_case_display": "₹15.00L",
        "pipeline": 1000000.0,
        "pipeline_display": "₹10.00L",
        "total": 10000000.0,
        "total_display": "₹1.00Cr"
      }
    ]
  },
  "pipeline_coverage": {
    "title": "Pipeline Coverage Analysis",
    "coverage_multiplier": 0.6,
    "coverage_display": "0.6x Coverage",
    "cards": [
      {
        "category": "Commit",
        "value": 10000000.0,
        "value_display": "₹1.00Cr",
        "deals": 8,
        "weighted_value": 8000000.0,
        "weighted_value_display": "₹80.00L"
      },
      {
        "category": "Best Case",
        "value": 5000000.0,
        "value_display": "₹50.00L",
        "deals": 5,
        "weighted_value": 3000000.0,
        "weighted_value_display": "₹30.00L"
      },
      {
        "category": "Pipeline",
        "value": 3000000.0,
        "value_display": "₹30.00L",
        "deals": 4,
        "weighted_value": 1200000.0,
        "weighted_value_display": "₹12.00L"
      },
      {
        "category": "Upside",
        "value": 2000000.0,
        "value_display": "₹20.00L",
        "deals": 3,
        "weighted_value": 400000.0,
        "weighted_value_display": "₹4.00L"
      }
    ]
  }
}
```

---

## 6. Forecast Deal Detail API

### GET `/api/sales/forecast/deal-detail/`

Get all open deals with forecast category and risk assessment.

**Query Parameters:**
- `period` (optional, string): Quarter period (e.g., `"Q4 FY25"`). If not provided, defaults to current quarter.

**Response (200 OK):**
```json
{
  "title": "Forecast Deal Detail",
  "subtitle": "All open deals with forecast category and risk assessment",
  "deals": [
    {
      "account": "Acme Corporation",
      "owner": "John Doe",
      "amount": 2000000.0,
      "amount_display": "₹20.00L",
      "stage": "Negotiation",
      "category": "commit",
      "confidence": "high",
      "close_date": "2024-12-31",
      "close_date_display": "31 Dec",
      "risk": 1
    },
    {
      "account": "Tech Solutions Inc",
      "owner": "Jane Smith",
      "amount": 1500000.0,
      "amount_display": "₹15.00L",
      "stage": "Proposal",
      "category": "best_case",
      "confidence": "medium",
      "close_date": "2024-12-15",
      "close_date_display": "15 Dec",
      "risk": 2
    }
  ]
}
```

**Category Values:**
- `"commit"`: Probability >= 75%
- `"best_case"`: Probability >= 50% and < 75%
- `"pipeline"`: Probability >= 25% and < 50%
- `"upside"`: Probability < 25%

**Confidence Levels:**
- `"high"`: Probability >= 75%
- `"medium"`: Probability >= 50% and < 75%
- `"low"`: Probability < 50%

**Risk Levels:**
- `1`: Low risk (days in stage <= 30 and probability >= 50%)
- `2`: Medium risk (days in stage > 30 OR probability < 50%)
- `3`: High risk (days in stage > 30 AND probability < 50%)

---

## 7. Forecast By Rep API

### GET `/api/sales/forecast/by-rep/`

Get forecast breakdown by sales representative.

**Query Parameters:**
- `period` (optional, string): Quarter period (e.g., `"Q4 FY25"`). If not provided, defaults to current quarter.

**Response (200 OK):**
```json
{
  "reps": [
    {
      "rep_name": "John Doe",
      "quota": 8000000.0,
      "quota_display": "₹80.00L",
      "current_attainment": 75.0,
      "current_attainment_display": "75.0%",
      "closed_commit_percentage": 87.5,
      "closed_commit_percentage_display": "87.5%",
      "metrics": {
        "closed": 4000000.0,
        "closed_display": "₹40.00L",
        "commit": 3000000.0,
        "commit_display": "₹30.00L",
        "best_case": 2000000.0,
        "best_case_display": "₹20.00L",
        "accuracy": 88.5,
        "accuracy_display": "89%"
      }
    },
    {
      "rep_name": "Jane Smith",
      "quota": 6000000.0,
      "quota_display": "₹60.00L",
      "current_attainment": 66.7,
      "current_attainment_display": "66.7%",
      "closed_commit_percentage": 83.3,
      "closed_commit_percentage_display": "83.3%",
      "metrics": {
        "closed": 3000000.0,
        "closed_display": "₹30.00L",
        "commit": 2000000.0,
        "commit_display": "₹20.00L",
        "best_case": 1500000.0,
        "best_case_display": "₹15.00L",
        "accuracy": 85.2,
        "accuracy_display": "85%"
      }
    }
  ]
}
```

---

## 8. Forecast Accuracy API

### GET `/api/sales/forecast/accuracy/`

Get forecast accuracy metrics and historical comparison.

**Query Parameters:**
- None (uses current year quarters and last 2 months)

**Response (200 OK):**
```json
{
  "forecast_vs_actual": {
    "title": "Forecast vs Actual",
    "subtitle": "Historical accuracy tracking",
    "data": [
      {
        "period": "Q1 FY24",
        "forecast": 10500000.0,
        "forecast_display": "₹1.05Cr",
        "actual": 10000000.0,
        "actual_display": "₹1.00Cr"
      },
      {
        "period": "Q2 FY24",
        "forecast": 11550000.0,
        "forecast_display": "₹1.16Cr",
        "actual": 11000000.0,
        "actual_display": "₹1.10Cr"
      },
      {
        "period": "Q3 FY24",
        "forecast": 12600000.0,
        "forecast_display": "₹1.26Cr",
        "actual": 12000000.0,
        "actual_display": "₹1.20Cr"
      },
      {
        "period": "Nov 2024",
        "forecast": 4125000.0,
        "forecast_display": "₹41.25L",
        "actual": 4000000.0,
        "actual_display": "₹40.00L"
      },
      {
        "period": "Dec 2024",
        "forecast": 4125000.0,
        "forecast_display": "₹41.25L",
        "actual": 4000000.0,
        "actual_display": "₹40.00L"
      }
    ]
  },
  "accuracy_trend": {
    "title": "Accuracy Trend",
    "subtitle": "Forecast accuracy over time",
    "data": [
      {
        "period": "Q1 FY24",
        "accuracy": 95.24
      },
      {
        "period": "Q2 FY24",
        "accuracy": 95.24
      },
      {
        "period": "Q3 FY24",
        "accuracy": 95.24
      },
      {
        "period": "Nov 2024",
        "accuracy": 96.97
      },
      {
        "period": "Dec 2024",
        "accuracy": 96.97
      }
    ]
  },
  "accuracy_summary": {
    "title": "Accuracy Summary",
    "data": [
      {
        "period": "Q1 FY24",
        "forecast": 10500000.0,
        "forecast_display": "₹1.05Cr",
        "actual": 10000000.0,
        "actual_display": "₹1.00Cr",
        "variance": -500000.0,
        "variance_display": "+₹5.00L",
        "accuracy": 95.24,
        "accuracy_display": "95.2%"
      },
      {
        "period": "Q2 FY24",
        "forecast": 11550000.0,
        "forecast_display": "₹1.16Cr",
        "actual": 11000000.0,
        "actual_display": "₹1.10Cr",
        "variance": -550000.0,
        "variance_display": "+₹5.50L",
        "accuracy": 95.24,
        "accuracy_display": "95.2%"
      },
      {
        "period": "Q3 FY24",
        "forecast": 12600000.0,
        "forecast_display": "₹1.26Cr",
        "actual": 12000000.0,
        "actual_display": "₹1.20Cr",
        "variance": -600000.0,
        "variance_display": "+₹6.00L",
        "accuracy": 95.24,
        "accuracy_display": "95.2%"
      },
      {
        "period": "Nov 2024",
        "forecast": 4125000.0,
        "forecast_display": "₹41.25L",
        "actual": 4000000.0,
        "actual_display": "₹40.00L",
        "variance": -125000.0,
        "variance_display": "+₹1.25L",
        "accuracy": 96.97,
        "accuracy_display": "97.0%"
      },
      {
        "period": "Dec 2024",
        "forecast": 4125000.0,
        "forecast_display": "₹41.25L",
        "actual": 4000000.0,
        "actual_display": "₹40.00L",
        "variance": -125000.0,
        "variance_display": "+₹1.25L",
        "accuracy": 96.97,
        "accuracy_display": "97.0%"
      }
    ]
  }
}
```

---

## 9. Team Performance Combined API

### GET `/api/sales/team/performance/`

Get combined team performance overview including individual rep metrics and revenue by product.

**Query Parameters:**
- `period` (optional, string): Time period filter. Options: `"7"`, `"30"`, `"90"`, `"365"`, `"year"`, `"quarter"`. Default: `"30"`

**Response (200 OK):**
```json
{
  "team_performance": {
    "title": "Sales Team Performance Overview",
    "subtitle": "Performance metrics for 30 days period",
    "reps": [
      {
        "rep_id": "550e8400-e29b-41d4-a716-446655440000",
        "rep_name": "John Doe",
        "designation": "Senior Sales Manager",
        "quota": 5000000.0,
        "quota_display": "₹50.00L",
        "achieved": 6000000.0,
        "achieved_display": "₹60.00L",
        "attainment": 120.0,
        "attainment_display": "120%",
        "deals": 8,
        "avg_deal_size": 750000.0,
        "avg_deal_size_display": "₹7.50L",
        "win_rate": 75.0,
        "win_rate_display": "75%",
        "pipeline": 1.2,
        "pipeline_display": "1.2x",
        "rating": 4.8,
        "rating_display": "★ 4.8"
      }
    ]
  },
  "revenue_by_product": {
    "title": "Revenue by Product Line",
    "subtitle": "Revenue breakdown for 30 days period",
    "product_lines": [
      {
        "product": "Enterprise",
        "revenue": 20000000.0,
        "revenue_display": "₹2.00Cr",
        "deals_closed": 12,
        "avg_deal_size": 1666666.67,
        "avg_deal_size_display": "₹1.67Cr",
        "yoy_growth": 25.0,
        "yoy_growth_display": "+25%"
      },
      {
        "product": "Pro",
        "revenue": 10000000.0,
        "revenue_display": "₹1.00Cr",
        "deals_closed": 20,
        "avg_deal_size": 500000.0,
        "avg_deal_size_display": "₹5.00L",
        "yoy_growth": 15.0,
        "yoy_growth_display": "+15%"
      },
      {
        "product": "Starter",
        "revenue": 2000000.0,
        "revenue_display": "₹20.00L",
        "deals_closed": 15,
        "avg_deal_size": 133333.33,
        "avg_deal_size_display": "₹1.33L",
        "yoy_growth": 10.0,
        "yoy_growth_display": "+10%"
      }
    ],
    "total": {
      "product": "Total",
      "revenue": 32000000.0,
      "revenue_display": "₹3.20Cr",
      "deals_closed": 47,
      "avg_deal_size": 680851.06,
      "avg_deal_size_display": "₹6.81L",
      "yoy_growth": null,
      "yoy_growth_display": null
    }
  }
}
```

---

## 10. Team Performance Individual API

### GET `/api/sales/team/performance/individual/`

Get individual sales team member performance metrics.

**Query Parameters:**
- `period` (optional, string): Time period filter. Options: `"7"`, `"30"`, `"90"`, `"365"`, `"year"`, `"quarter"`. Default: `"30"`

**Response (200 OK):**
```json
{
  "title": "Sales Team Performance Overview",
  "subtitle": "Performance metrics for 30 days period",
  "reps": [
    {
      "rep_id": "550e8400-e29b-41d4-a716-446655440000",
      "rep_name": "John Doe",
      "designation": "Senior Sales Manager",
      "quota": 5000000.0,
      "quota_display": "₹50.00L",
      "achieved": 6000000.0,
      "achieved_display": "₹60.00L",
      "attainment": 120.0,
      "attainment_display": "120%",
      "deals": 8,
      "avg_deal_size": 750000.0,
      "avg_deal_size_display": "₹7.50L",
      "win_rate": 75.0,
      "win_rate_display": "75%",
      "pipeline": 1.2,
      "pipeline_display": "1.2x",
      "rating": 4.8,
      "rating_display": "★ 4.8"
    }
  ]
}
```

---

## 11. Revenue By Product API

### GET `/api/sales/team/revenue-by-product/`

Get revenue breakdown by product line.

**Query Parameters:**
- `period` (optional, string): Time period filter. Options: `"7"`, `"30"`, `"90"`, `"365"`, `"year"`, `"quarter"`. Default: `"30"`

**Response (200 OK):**
```json
{
  "title": "Revenue by Product Line",
  "subtitle": "Revenue breakdown for 30 days period",
  "product_lines": [
    {
      "product": "Enterprise",
      "revenue": 20000000.0,
      "revenue_display": "₹2.00Cr",
      "deals_closed": 12,
      "avg_deal_size": 1666666.67,
      "avg_deal_size_display": "₹1.67Cr",
      "yoy_growth": 25.0,
      "yoy_growth_display": "+25%"
    },
    {
      "product": "Pro",
      "revenue": 10000000.0,
      "revenue_display": "₹1.00Cr",
      "deals_closed": 20,
      "avg_deal_size": 500000.0,
      "avg_deal_size_display": "₹5.00L",
      "yoy_growth": 15.0,
      "yoy_growth_display": "+15%"
    },
    {
      "product": "Starter",
      "revenue": 2000000.0,
      "revenue_display": "₹20.00L",
      "deals_closed": 15,
      "avg_deal_size": 133333.33,
      "avg_deal_size_display": "₹1.33L",
      "yoy_growth": 10.0,
      "yoy_growth_display": "+10%"
    }
  ],
  "total": {
    "product": "Total",
    "revenue": 32000000.0,
    "revenue_display": "₹3.20Cr",
    "deals_closed": 47,
    "avg_deal_size": 680851.06,
    "avg_deal_size_display": "₹6.81L",
    "yoy_growth": null,
    "yoy_growth_display": null
  }
}
```

---

## 12. Team Summary API

### GET `/api/sales/team/summary/`

Get high-level team summary cards with key metrics.

**Query Parameters:**
- `period` (optional, string): Time period filter. Options: `"7"`, `"30"`, `"90"`, `"365"`, `"year"`, `"quarter"`. Default: `"30"`

**Response (200 OK):**
```json
{
  "top_performer": {
    "title": "Top Performer",
    "name": "John Doe",
    "detail": "120% quota attainment"
  },
  "team_avg_attainment": {
    "title": "Team Avg Attainment",
    "percentage": 85.5,
    "percentage_display": "86%",
    "status": "Below target"
  },
  "total_deals_closed": {
    "title": "Total Deals Closed",
    "count": 47,
    "count_display": "47",
    "period": "This period"
  },
  "reps_at_above_quota": {
    "title": "Reps At/Above Quota",
    "count": "5/8",
    "count_display": "5/8",
    "success_rate": "63% success rate"
  }
}
```

---

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request
```json
{
  "error": "Error message describing what went wrong"
}
```

### 401 Unauthorized
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden
```json
{
  "detail": "You do not have permission to perform this action."
}
```

### 404 Not Found
```json
{
  "error": "Company not found"
}
```

or

```json
{
  "deal_owner_id": "Sales team member not found"
}
```

### 500 Internal Server Error
```json
{
  "error": "Failed to create deal: <error details>"
}
```

---

## Field Descriptions

### Sales Stage Values
- `"Discovery"`: Initial contact and discovery phase
- `"Qualification"`: Qualifying the opportunity
- `"Proposal"`: Proposal submitted
- `"Negotiation"`: Negotiating terms
- `"Closed Won"`: Deal successfully closed
- `"Closed Lost"`: Deal lost
- `"Unqualified"`: Opportunity unqualified

### Product Values
- `"Enterprise"`: Enterprise tier product
- `"Pro"`: Professional tier product
- `"Starter"`: Starter tier product

### Amount Display Format
- Amounts >= ₹1,00,00,000 (1 Crore) are displayed as `₹XX.XXCr`
- Amounts < ₹1,00,00,000 are displayed as `₹XX.XXL` (Lakhs)
- Example: `₹3.10Cr` = ₹3,10,00,000, `₹50.00L` = ₹50,00,000

### Probability Categories
- **Commit**: Probability >= 75% (High confidence)
- **Best Case**: Probability >= 50% and < 75% (Medium confidence)
- **Pipeline**: Probability >= 25% and < 50% (Low confidence)
- **Upside**: Probability < 25% (Very low confidence)

---

## Notes

1. **Authentication**: All endpoints require JWT authentication via the `Authorization: Bearer <token>` header.

2. **Company Context**: All endpoints automatically filter data by the authenticated user's company. The company is extracted from the request context.

3. **Date Formats**: 
   - Request dates: `YYYY-MM-DD` (e.g., `"2024-12-31"`)
   - Response dates: ISO 8601 format or formatted strings (e.g., `"31 Dec 2024"`)

4. **Decimal Precision**: 
   - Amounts are returned as floats with 2 decimal places
   - Display values are formatted with appropriate currency symbols and units (L/Cr)

5. **Default Values**:
   - Default quota: ₹3.10Cr (31,000,000) for company-level, ₹50L (5,000,000) for individual reps
   - Default period: 30 days
   - Default probability is set based on stage if not provided

6. **Deal ID Generation**: When creating a deal, a unique `deal_id` is automatically generated in the format `DEAL{6-character-hex}` (e.g., `DEAL1A2B3C`).

7. **Forecast Categories**: Deals are automatically categorized into commit, best_case, pipeline, or upside based on their probability percentage.

8. **Pipeline Health Score**: Calculated based on pipeline coverage ratio and stalled deals percentage. Ranges from 0-100:
   - 80-100: Excellent
   - 60-79: Good
   - 40-59: Moderate
   - 0-39: Poor

9. **Sales Velocity**: Average number of days to close a deal, calculated from deal creation to close date for closed won deals.

10. **Win Rate**: Percentage of total deals that were closed won, calculated as (won deals / total deals) × 100.
