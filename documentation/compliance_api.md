# Compliance API Documentation

Base URL: `https://<host>/api/compliance/`  
Authentication: `Authorization: Bearer <token>` (all endpoints require authenticated users).  
Unless stated otherwise, endpoints operate on all compliance records the authenticated user can access.

---

## Tasks

### List / Create
`GET | POST /tasks/`

Query params:
- `act` — filter by act name (exact match).
- `status` — filter by status (`Pending`, `In Progress`, `Completed`, etc.).
- `is_overdue` — `true` / `false`.

List response:

```json
[
  {
    "id": "9f5c…",
    "task_id": "COM-001",
    "act": "Companies Act, 2013",
    "particulars": "File DIR-3 KYC",
    "due_date": "2025-11-30",
    "frequency": "Annually",
    "severity": "High",
    "status": "Pending",
    "company_type": "Private Limited",
    "assignee": "Legal Team",
    "last_filed_date": null,
    "next_due_date": "2025-11-30",
    "completed_date": null,
    "reminder_days": 60,
    "penalty_amount": "5000",
    "payment_amount": null,
    "payment_reference": null,
    "consequences": "Director DIN deactivation",
    "notes": "Collect PAN copies",
    "evidence_url": null,
    "days_until_due": 25,
    "is_overdue": false,
    "interest_percentage": null,
    "penalty": null,
    "late_fee": null,
    "interest_amount": null,
    "created_at": "2025-10-01T10:00:00Z",
    "updated_at": "2025-10-01T10:00:00Z"
  }
]
```

Create payload (read-only fields like `task_id`, `status`, `days_until_due` are ignored):

```json
{
  "act": "Companies Act, 2013",
  "particulars": "File DIR-3 KYC",
  "due_date": "2025-11-30",
  "frequency": "Annually",
  "severity": "High",
  "company_type": "Private Limited",
  "assignee": "Legal Team",
  "notes": "Collect PAN copies",
  "evidence_url": "https://drive.example.com/dir3"
}
```

### Detail / Update / Delete
`GET | PATCH | DELETE /tasks/<task_id>/`

- `GET` returns the same schema as list.
- `PATCH` accepts the create fields; server recomputes derived attributes (status, reminders, etc.).
- `DELETE` removes the task.

---

## Payments

### List / Create
`GET | POST /payments/`

Query params:
- `task_id` — exact `task_id` string.
- `related_act` — act value (matches `ComplianceTaskMaster.act`).
- `is_late` — `true` / `false`.

List response:

```json
[
  {
    "id": "3db4…",
    "payment_id": "PAY-005",
    "compliance_task": "9f5c…",
    "compliance_task_id": "9f5c…",
    "task_id": "COM-001",
    "payment_type": "Government Portal",
    "period": "FY24",
    "payment_date": "2025-11-15",
    "amount": "5000",
    "reference_number": "GRN12345",
    "notes": "Challan uploaded",
    "related_act": "Companies Act, 2013",
    "due_date": "2025-11-30",
    "days_early_or_late": -15,
    "is_late": false,
    "estimated_penalty": "0.00",
    "estimated_interest": "0.00",
    "estimated_late_fee": "0.00",
    "created_at": "2025-11-15T09:00:00Z",
    "updated_at": "2025-11-15T09:00:00Z"
  }
]
```

Create payload (server auto-derives `payment_id`, `task_id`, `related_act`, `due_date`, `days_early_or_late`, `is_late`):

```json
{
  "compliance_task": "9f5c…",
  "payment_type": "Government Portal",
  "period": "FY24",
  "payment_date": "2025-11-15",
  "amount": "5000",
  "reference_number": "GRN12345",
  "notes": "Challan uploaded",
  "estimated_penalty": "0.00",
  "estimated_interest": "0.00",
  "estimated_late_fee": "0.00"
}
```

### Detail / Update / Delete
`GET | PATCH | DELETE /payments/<payment_id>/`

- `PATCH` accepts mutable fields (`compliance_task`, `payment_type`, financials, etc.).
- `DELETE` removes the payment record.

---

## Act-wise Summary

`GET /act-wise-summary/?act=<optional>`

Aggregates compliance health per act. Response:

```json
[
  {
    "act_name": "Companies Act, 2013",
    "total_tasks": 12,
    "completed": 8,
    "pending": 2,
    "in_progress": 2,
    "overdue": 1,
    "critical_tasks": 3,
    "high_severity": 5,
    "completion_rate": 66.67,
    "health_status": "Good"
  }
]
```

`act` query param limits the computation to a single act while keeping the response structure consistent.

---

## Exposure Analysis

`GET /exposure-analysis/?act=<optional>`

Combines task-level figures and payment estimates to show total exposure per act.

```json
[
  {
    "act_name": "Companies Act, 2013",
    "estimated_penalty": 15000.0,
    "estimated_interest": 1200.0,
    "estimated_late_fee": 500.0,
    "total_exposure": 16700.0,
    "overdue_tasks": 2,
    "critical_overdue": 1
  }
]
```

---

## Dashboard

`GET /dashboard/`

Returns portfolio-wide compliance KPIs:

```json
{
  "total_tasks": 40,
  "completed_tasks": 24,
  "pending_tasks": 10,
  "in_progress": 6,
  "overdue_tasks": 3,
  "critical_tasks": 5,
  "high_severity": 9,
  "due_this_month": 7,
  "completion_rate": 60.0,
  "compliance_health_score": 72.5,
  "total_exposure": 25000.0,
  "litigation_exposure": 0.0,
  "total_provisions": 0.0,
  "payments_this_month": 4500.0,
  "doughnut_chart": {
    "completed_portion": 24,
    "remaining": 16
  }
}
```

Metrics such as `litigation_exposure` and `total_provisions` are placeholders today but structured for future expansion.

---

## Notes

- Pagination/query parameters follow DRF defaults (`?page=`, `?page_size=`).  
- Validation errors return standard DRF structures, e.g. `{"field": ["message"]}`.  
- Derived fields on tasks (IDs, statuses, reminder windows) and payments (payment IDs, lateness metrics) are calculated server-side.  
- Use `/swagger/` or `/redoc/` at the project root for the OpenAPI view of these endpoints.

