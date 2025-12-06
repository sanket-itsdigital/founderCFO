# Accounts API Documentation

Base URL: `https://<host>/api/account/`  
Authentication: unless noted, send `Authorization: Bearer <token>`. JWT tokens are issued via the Signin / Signup endpoints and include custom `role` and `company_id` claims.

---

## Authentication

### Sign Up
`POST /signup/` *(no auth required)*

Request:
```json
{
  "first_name": "Jane",
  "middle_name": null,
  "last_name": "Doe",
  "email": "jane@example.com",
  "mobile_number": "+14155550123",
  "role": "Founder",
  "profile_image": null,
  "password": "Str0ngPass!23",
  "status": "Pending"
}
```

Response:
```json
{
  "access": "<jwt_access>",
  "refresh": "<jwt_refresh>",
  "role": "Founder",
  "company_id": null,
  "message": "Registration successful. Thank you for joining us."
}
```

### Sign In
`POST /signin/`

Request:
```json
{
  "email": "jane@example.com",
  "password": "Str0ngPass!23"
}
```

Response (`401` if founder is still pending verification or any rejected user):
```json
{
  "access": "<jwt_access>",
  "refresh": "<jwt_refresh>",
  "role": "Founder",
  "company_id": "5e41c5f0-0c1c-4bec-9a5a-0fe968f19e92"
}
```

### Logout
`POST /logout/`

Request:
```json
{"refresh": "<jwt_refresh>"}
```

Response:
```json
{"message": "User successfully logged out."}
```

### Change Password
`PATCH /change-password/`

Request:
```json
{
  "old_password": "Str0ngPass!23",
  "password": "N3wPass!45",
  "confirm_password": "N3wPass!45"
}
```

Response:
```json
{"message": "Password changed successfully."}
```

---

## Profile & User Info

### Profile
`GET | PATCH /profile/`

Response (GET):
```json
{
  "id": "4fdd…",
  "first_name": "Jane",
  "middle_name": null,
  "last_name": "Doe",
  "full_name": "Jane Doe",
  "email": "jane@example.com",
  "mobile_number": "+14155550123",
  "profile_image": "https://cdn.example.com/media/profile/jane.png",
  "role": "Founder",
  "status": "Accepted",
  "created_at": "2025-10-01T10:00:00Z"
}
```

`PATCH` accepts any subset of profile fields (except read-only ones) and returns the updated document.

### User Info
`GET | PATCH /user-info/`

Simplified view for dashboards. Fields: `id, role, email, first_name, last_name, mobile_number, profile_image`. `PATCH` allows partial updates of these same fields.

---

## Company Management

### Create Company
`POST /company/register/`

Request:
```json
{
  "name": "Acme Pvt Ltd",
  "GST_number": "22AAAAA0000A1Z5",
  "address": "221B Baker Street, London",
  "no_of_employees": 42,
  "nature_of_business": "Professional Services"
}
```

Response:
```json
{
  "id": "5e41…",
  "name": "Acme Pvt Ltd",
  "GST_number": "22AAAAA0000A1Z5",
  "address": "221B Baker Street, London",
  "no_of_employees": 42,
  "nature_of_business": "Professional Services",
  "owner": {
    "id": "4fdd…",
    "first_name": "Jane",
    "last_name": "Doe",
    "email": "jane@example.com",
    "role": "Founder",
    "status": "Accepted",
    "profile_image": null
  }
}
```

If a founder already has a company, response is `400` with:
```json
{
  "detail": "You already have a company. Each user can only have one company.",
  "existing_company": {
    "id": "5e41…",
    "name": "Acme Pvt Ltd"
  }
}
```

### Company Info
`GET /company/?company_id=<optional>` *(exposed via Cap Table's `CompanyInfoView`, re-used here)*

- Without `company_id`: returns every company where the user is an owner or an active team member.
- With `company_id`: returns that company’s detailed record.

---

## Team Members

Permissions: `IsAuthenticated`, `IsFounder`, `HasActiveSubscription`. The founder must have created a company first.

### List / Invite
`GET | POST /company/team-members/`

List response:
```json
[
  {
    "id": "b6ca…",
    "company": "Acme Pvt Ltd",
    "role": "Accountant",
    "is_active": true,
    "user": {
      "id": "9158…",
      "first_name": "Alex",
      "last_name": "Smith",
      "email": "alex@example.com",
      "role": "Accountant",
      "status": "Accepted",
      "profile_image": null
    },
    "invited_by": {...},
    "created_at": "2025-11-05T09:00:00Z",
    "updated_at": "2025-11-05T09:00:00Z"
  }
]
```

Invite payload:
```json
{
  "role": "Accountant",
  "email": "alex@example.com",
  "mobile_number": "+14155550999",
  "profile_image": null,
  "password": "TempPass!42"
}
```

### Detail / Update / Remove
`GET | PATCH | DELETE /company/team-members/<uuid:pk>/`

- `GET` returns the same schema as the list item.
- `PATCH` accepts `role`, `is_active`, optional profile fields (`first_name`, `middle_name`, `last_name`, `mobile_number`, `profile_image`).
- `DELETE` removes the team member from the company.

---

## Company/User Helpers

### User Info (basic)
See `/user-info/` above for quick profile refresh.

### Company Selector
`GET /company/` (again via `CompanyInfoView`) returns all companies available to the current user—useful for dropdown selectors or switching context in other modules.

---

## Notes

- All endpoints return standard DRF validation errors, e.g. `{"field": ["message"]}`.
- JWT tokens carry `role` and `company_id` claims to simplify client-side routing.
- Team APIs enforce company ownership and active subscription checks server-side.
- Explore `/swagger/` or `/redoc/` (project root) for the live OpenAPI schema covering these endpoints.

