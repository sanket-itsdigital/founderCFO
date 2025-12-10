# Compliance Task API - Sample Payload

## Endpoint
**POST** `/api/compliance/tasks/`

## Sample Payload

### Minimal Required Fields
```json
{
  "act": "Companies Act, 2013",
  "particulars": "AOC-4-Annual Accounts filing (AOC-4) – late fee ₹1 L/day; interest on delayed accounts",
  "due_date": "2025-03-31",
  "frequency": "Annually",
  "severity": "High"
}
```

### Complete Payload (All Fields)
```json
{
  "act": "Companies Act, 2013",
  "particulars": "AOC-4-Annual Accounts filing (AOC-4) – late fee ₹1 L/day; interest on delayed accounts",
  "due_date": "2025-03-31",
  "frequency": "Annually",
  "severity": "High",
  "company_type": "Private Limited",
  "assignee": "John Doe",
  "last_filed_date": "2024-03-31",
  "next_due_date": "2026-03-31",
  "completed_date": null,
  "penalty_amount": "Int - NA - Late Fees - ₹100 per day - Penalty - ₹10,000 – ₹5 lakh",
  "payment_amount": "50000.00",
  "payment_reference": "CHALLAN-123456",
  "payment_method": "Online",
  "payment_period": "2025-03-31",
  "consequences": "Penalty under Sec 403 of Companies Act.",
  "notes": "Annual filing for FY 2024-25",
  "interest_percentage": "18%",
  "penalty": "₹10,000",
  "late_fee": "₹100 per day",
  "interest_amount": "₹5,000"
}
```

## Field Descriptions

### Required Fields

| Field | Type | Description | Example Values |
|-------|------|-------------|----------------|
| `act` | string | The act name (must be from ActNameChoices) | `"Companies Act, 2013"`, `"Income Tax Act, 1961"`, `"CGST ACT 2017"`, `"FEMA"`, `"LLP Act 2008"`, `"ESI Act 1948"`, `"EPF Act 1952"`, `"SEBI (LODR)"`, `"SEBI"`, `"MSME Act"` |
| `particulars` | string | Task particulars (must be from ParticularsType) | See list below |
| `due_date` | date (YYYY-MM-DD) | Due date for the task | `"2025-03-31"` |
| `frequency` | string | Frequency of the task (must be from Frequency) | `"Monthly"`, `"Quarterly"`, `"Half-yearly"`, `"Annually"` |
| `severity` | string | Severity level | `"High"`, `"Medium"`, `"Low"` |

### Optional Fields

| Field | Type | Description | Example Values |
|-------|------|-------------|----------------|
| `company_type` | string | Company type | `"Private Limited"`, `"Public Limited"`, `"LLP"` |
| `assignee` | string | Person assigned to the task | `"John Doe"` |
| `last_filed_date` | date (YYYY-MM-DD) | Last filing date | `"2024-03-31"` |
| `next_due_date` | date (YYYY-MM-DD) | Next due date | `"2026-03-31"` |
| `completed_date` | date (YYYY-MM-DD) | Completion date (null if not completed) | `null` or `"2025-03-15"` |
| `penalty_amount` | string | Penalty amount description | See PenaltyAmount choices below |
| `payment_amount` | decimal | Payment amount | `"50000.00"` |
| `payment_reference` | string | Payment reference number | `"CHALLAN-123456"` |
| `payment_method` | string | Payment method | `"Online"`, `"Cheque"`, `"Bank Transfer"` |
| `payment_period` | date (YYYY-MM-DD) | Payment period | `"2025-03-31"` |
| `consequences` | string | Consequences description | See ConsequencesType choices below |
| `notes` | string | Additional notes | `"Annual filing for FY 2024-25"` |
| `interest_percentage` | string | Interest percentage | `"18%"`, `"1%"`, `"12%"`, `"NA"` |
| `penalty` | string | Penalty amount | `"₹10,000"` |
| `late_fee` | string | Late fee description | `"₹100 per day"` |
| `interest_amount` | string | Interest amount | `"₹5,000"` |

## Available Choices

### Act Names (act field)
- `"Companies Act, 2013"`
- `"FEMA"`
- `"LLP Act 2008"`
- `"CGST ACT 2017"`
- `"Income Tax Act, 1961"`
- `"ESI Act 1948"`
- `"EPF Act 1952"`
- `"SEBI (LODR)"`
- `"SEBI"`
- `"MSME Act"`

### Frequency (frequency field)
- `"Monthly"`
- `"Quarterly"`
- `"Half-yearly"`
- `"Annually"`

### Company Type (company_type field)
- `"Private Limited"` (default)
- `"Public Limited"`
- `"LLP"`

### Sample Particulars (particulars field)
Some common examples:
- `"AOC-4-Annual Accounts filing (AOC-4) – late fee ₹1 L/day; interest on delayed accounts"`
- `"GSTR-3B-Summary return & tax payment – interest & late fee if delay"`
- `"ITR-6-Filing of return of income for companies not claiming exemption u/s 11"`
- `"MGT-7/MGT-7A-Annual return (MGT-7/MGT-7A)"`
- `"Challan 281-Monthly TDS/TCS deposit (non-March months)"`

**Note:** The `particulars` field has many options. Check the `ParticularsType` enum in `compliance/enums.py` for the complete list.

### Sample Consequences (consequences field)
- `"Penalty under Sec 403 of Companies Act."`
- `"Delay attracts ₹100/day penalty under LLP Act."`
- `"Late filing attracts 18% interest and ₹50/day fee."`
- `"Consequences as per applicable law."`
- `"Not Applicable"`

**Note:** Check the `ConsequencesType` enum in `compliance/enums.py` for the complete list.

### Sample Penalty Amount (penalty_amount field)
- `"Int - NA - Late Fees - ₹100 per day - Penalty - ₹10,000 – ₹5 lakh"`
- `"Int - 18 % p.a. - Late Fees - ₹50 / day (₹20 NIL) - Penalty - Up to ₹5,000"`
- `"Int - 18 % p.a. on tax payable u/s 50 - Late Fees - ₹50 / day (₹25 CGST + ₹25 SGST); ₹20 / day for NIL - Penalty - Up to ₹5,000 u/s 47"`

**Note:** Check the `PenaltyAmount` enum in `compliance/enums.py` for the complete list.

## Read-Only Fields (Auto-Generated)
These fields are automatically set and cannot be provided in the payload:
- `id` - Task ID (UUID)
- `task_id` - Auto-generated task identifier
- `status` - Auto-calculated based on dates
- `next_due_date` - Auto-calculated based on frequency
- `reminder_days` - Auto-calculated
- `days_until_due` - Auto-calculated
- `is_overdue` - Auto-calculated
- `is_admin_created` - Set to `false` for user-created tasks
- `created_by` - Current user
- `updated_by` - Current user
- `created_at` - Timestamp
- `updated_at` - Timestamp

## Important Notes

1. **Company Association**: When you create a task, it will automatically be associated with your company (from the `company_id` in your JWT token or query params). You don't need to specify this in the payload.

2. **Date Format**: All dates must be in `YYYY-MM-DD` format (ISO 8601).

3. **Enum Values**: Make sure to use exact enum values for `act`, `particulars`, `frequency`, `company_type`, `consequences`, and `penalty_amount`. The values are case-sensitive.

4. **Task Visibility**: Tasks you create will only be visible to your company. They won't be visible to other companies unless you're a superuser.

## Example cURL Request

```bash
curl --location 'http://0.0.0.0:8001/api/compliance/tasks/' \
--header 'Content-Type: application/json' \
--header 'Accept: application/json' \
--header 'Authorization: Bearer YOUR_TOKEN_HERE' \
--data '{
  "act": "Companies Act, 2013",
  "particulars": "AOC-4-Annual Accounts filing (AOC-4) – late fee ₹1 L/day; interest on delayed accounts",
  "due_date": "2025-03-31",
  "frequency": "Annually",
  "severity": "High",
  "company_type": "Private Limited",
  "assignee": "John Doe",
  "notes": "Annual filing for FY 2024-25"
}'
```

## Response

### Success Response (201 Created)
```json
{
  "id": "uuid-here",
  "task_id": "TASK-2025-001",
  "act": "Companies Act, 2013",
  "particulars": "AOC-4-Annual Accounts filing (AOC-4) – late fee ₹1 L/day; interest on delayed accounts",
  "due_date": "2025-03-31",
  "frequency": "Annually",
  "severity": "High",
  "status": "PENDING",
  "company_type": "Private Limited",
  "assignee": "John Doe",
  "last_filed_date": null,
  "next_due_date": null,
  "completed_date": null,
  "reminder_days": 0,
  "penalty_amount": null,
  "payment_amount": null,
  "payment_reference": null,
  "payment_method": null,
  "payment_period": null,
  "consequences": null,
  "notes": "Annual filing for FY 2024-25",
  "evidence_url": null,
  "days_until_due": 89,
  "is_overdue": false,
  "interest_percentage": null,
  "penalty": null,
  "late_fee": null,
  "interest_amount": null,
  "is_admin_created": false,
  "created_by": "user-uuid",
  "updated_by": "user-uuid",
  "created_at": "2025-01-01T10:00:00Z",
  "updated_at": "2025-01-01T10:00:00Z"
}
```

### Error Response (400 Bad Request)
```json
{
  "act": ["This field is required."],
  "particulars": ["Invalid choice."]
}
```
