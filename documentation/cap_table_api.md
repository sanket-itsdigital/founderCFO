# Cap Table API Documentation

Base URL: `https://<host>/api/captable/`  
Authentication: `Authorization: Bearer <token>` (all endpoints require an authenticated founder).  
Company scope: endpoints automatically filter to the caller’s companies; pass `company_id=<uuid>` query param when you manage multiple companies.

---

## Shareholders

### List
`GET /shareholders/?company_id=<uuid>`

```json
[
  {
    "id": "41e5…",
    "name": "Jane VC",
    "investor_type": "VC_FUND",
    "email": "jane@example.com",
    "kyc_verified": true,
    "created_at": "2025-11-01T11:22:33Z"
  }
]
```

### Create
`POST /shareholders/`

```json
{
  "company_id": "2dd8…",
  "name": "John Doe",
  "investor_type": "ANGEL",
  "email": "john@angel.com",
  "kyc_verified": false
}
```

### Detail / Update / Delete
`GET | PATCH | DELETE /shareholders/<shareholder_id>/`

- `GET` returns the same schema as list.
- `PATCH` accepts the create fields (without `company_id`).
- `DELETE` removes the record.

---

## Cap Table Events

### List
`GET /events/?company_id=<uuid>`

```json
{
  "id": "c5aa…",
  "event_name": "Seed Round",
  "event_type": "EQUITY",
  "date": "2025-10-10",
  "valuation": "5000000",
  "amount_raised": "750000",
  "share_price": "1.25",
  "documents_count": 2,
  "total_shares": "150000",
  "total_invested": "750000"
}
```

### Create
`POST /events/`

```json
{
  "company_id": "2dd8…",
  "event_name": "Seed Round",
  "event_type": "EQUITY",
  "date": "2025-10-10",
  "description": "Pre-seed bridge",
  "valuation": "5000000",
  "amount_raised": "750000",
  "share_price": "1.25",
  "notes": "Board approved"
}
```

### Detail / Update / Delete
`GET | PATCH | DELETE /events/<event_id>/`

- `GET` adds `notes`, `documents`, `transactions`, and `shareholder_summary`.
- `PATCH` accepts the create fields (without `company_id`).
- `DELETE` removes the event (transactions follow FK rules).

---

## Event Documents

### List
`GET /events/<event_id>/documents/?company_id=<uuid>`

```json
[
  {"id": "d1", "name": "SPA.pdf", "file": "/media/.../SPA.pdf", "created_at": "2025-11-10T10:00:00Z"}
]
```

### Upload
`POST /events/<event_id>/documents/` (multipart)

- Single: `file`, optional `name`.
- Multiple: `files[]`, optional `names[]` (same length).

Response is the array of saved documents.

---

## Capitalization Table Rows

### List
`GET /transactions/?company_id=<uuid>&event_id=<optional>`

```json
{
  "id": "t1",
  "event": "c5aa…",
  "shareholder": {...},
  "share_class_type": "PREFERENCE",
  "share_class_name": "Series Seed",
  "shares_issued": "100000",
  "price_per_share": "1.25",
  "lock_in_ends": "2026-10-10",
  "amount": "125000",
  "total_invested": "125000",
  "created_at": "2025-11-10T10:05:00Z"
}
```

### Create
`POST /transactions/`

```json
{
  "event_id": "c5aa…",
  "shareholder_id": "41e5…",
  "share_class_type": "PREFERENCE",
  "share_class_name": "Series Seed",
  "shares_issued": "100000",
  "price_per_share": "1.25",
  "lock_in_ends": "2026-10-10"
}
```

### Detail / Update / Delete
`GET | PATCH | DELETE /transactions/<row_id>/`

- `PATCH` accepts the create fields (event/shareholder optional).

---

## Bulk Event + Transactions

### Retrieve
`GET /events/transactions/?company_id=<uuid>`

Returns every event using the detail serializer (documents, transactions, shareholder summary).

### Create
`POST /events/transactions/`

```json
{
  "event": {
    "company_id": "2dd8…",
    "event_name": "Series A",
    "event_type": "EQUITY",
    "date": "2025-12-01",
    "valuation": "12000000",
    "amount_raised": "3000000",
    "share_price": "2.50",
    "notes": "Led by XYZ"
  },
  "transactions": [
    {
      "shareholder_id": "41e5…",
      "share_class_type": "PREFERENCE",
      "share_class_name": "Series A",
      "shares_issued": "800000",
      "price_per_share": "2.50",
      "lock_in_ends": "2027-12-01"
    },
    {
      "shareholder_id": "7c0d…",
      "share_class_type": "PREFERENCE",
      "share_class_name": "Series A",
      "shares_issued": "400000",
      "price_per_share": "2.50"
    }
  ]
}
```

Validation rules:
- `event.share_price` is mandatory.
- Each transaction `price_per_share` must equal the event `share_price`.
- Shareholders must belong to the same company (and owner must match the caller).

Response:

```json
{
  "event": { /* CapTableEventDetailSerializer */ },
  "transactions": [ /* CapitalizationTableSerializer items */ ]
}
```

---

## Summary & Helpers

### Cap Table Summary
`GET /summary/?company_id=<uuid>`

```json
{
  "company_id": "2dd8…",
  "total_shares_outstanding": "1500000",
  "shareholders": [
    {
      "shareholder_id": "41e5…",
      "name": "Jane VC",
      "investor_type": "VC_FUND",
      "email": "jane@example.com",
      "kyc_verified": true,
      "total_shares": "800000",
      "total_invested": "2000000",
      "ownership_percent": "53.33"
    }
  ]
}
```

### Shareholder Dropdown
`GET /shareholders-list/?company_id=<uuid>`  
Lightweight list identical to `/shareholders/` (useful for selectors).

---

## Tips

- Pagination/query params follow DRF defaults (`?page=`, `?page_size=`).  
- Errors use standard DRF format, e.g. `{"field": ["message"]}`.  
- File uploads must be multipart requests.  
- Explore `/swagger/` or `/redoc/` (project root) for live OpenAPI schema.  
- In Django admin, ensure dropdowns (events, shareholders) are filtered to the selected company to mirror API constraints.

