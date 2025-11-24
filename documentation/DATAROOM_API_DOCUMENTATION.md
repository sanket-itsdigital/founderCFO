# Dataroom API Documentation

Complete API payload documentation for all Dataroom endpoints.

**Base URL:** `/api/dataroom/`

**Authentication:** All endpoints require JWT authentication. Include the token in the Authorization header:
```
Authorization: Bearer <access_token>
```

---

## 1. Overview API

### GET `/api/dataroom/overview/`

Get comprehensive overview and analytics for a company's dataroom.

**Query Parameters:**
- `company_id` (required, UUID): Company ID

**Response (200 OK):**
```json
{
  "total_documents": 150,
  "total_storage_bytes": 52428800,
  "total_storage_mb": 50.0,
  "total_storage_gb": 0.05,
  "total_views": 1250,
  "downloads": 340,
  "active_users": 12,
  "avg_response_time_hours": 4.5,
  "analytics": {
    "uploads_over_time": [
      {
        "month": "2024-01",
        "count": 25
      },
      {
        "month": "2024-02",
        "count": 30
      }
    ],
    "document_engagement_score": [
      {
        "document_id": "uuid",
        "document_name": "Financial Report Q1",
        "folder_name": "Financial Documents",
        "score": 450
      }
    ],
    "upload_trend_30_days": [
      {
        "date": "2024-03-01",
        "count": 5
      }
    ],
    "user_activity_heatmap": [
      {
        "hour": 0,
        "count": 2
      },
      {
        "hour": 9,
        "count": 45
      }
    ],
    "file_type_distribution": [
      {
        "type": "pdf",
        "count": 80,
        "percentage": 53.33
      },
      {
        "type": "xlsx",
        "count": 40,
        "percentage": 26.67
      }
    ]
  }
}
```

---

## 2. Folder APIs

### GET `/api/dataroom/folders/`

List all folders available to the user.

**Response (200 OK):**
```json
[
  {
    "id": "uuid",
    "name": "Financial Documents",
    "description": "All financial related documents",
    "is_active": true,
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

### POST `/api/dataroom/folders/`

Create a new folder (Superuser only).

**Request Body:**
```json
{
  "name": "Legal Documents",
  "description": "Legal and compliance documents",
  "is_active": true
}
```

**Response (201 Created):**
```json
{
  "id": "uuid",
  "name": "Legal Documents",
  "description": "Legal and compliance documents",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z"
}
```

### GET `/api/dataroom/folders/{folder_id}/`

Retrieve a specific folder.

**Response (200 OK):**
```json
{
  "id": "uuid",
  "name": "Financial Documents",
  "description": "All financial related documents",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z"
}
```

### PATCH/PUT `/api/dataroom/folders/{folder_id}/`

Update a folder.

**Request Body:**
```json
{
  "name": "Updated Folder Name",
  "description": "Updated description",
  "is_active": false
}
```

**Response (200 OK):**
```json
{
  "id": "uuid",
  "name": "Updated Folder Name",
  "description": "Updated description",
  "is_active": false,
  "created_at": "2024-01-15T10:30:00Z"
}
```

### GET `/api/dataroom/folders/{folder_id}/documents/`

Get all documents in a specific folder.

**Response (200 OK):**
```json
[
  {
    "id": "uuid",
    "company": "uuid",
    "folder": "uuid",
    "folder_name": "Financial Documents",
    "name": "Q1 Financial Report.pdf",
    "file": "/media/dataroom/docs/2024/03/report.pdf",
    "size_bytes": 1048576,
    "size": "1.00 MB",
    "access_notes": "Confidential",
    "views_count": 25,
    "downloads_count": 10,
    "upload_date": "2024-03-01T10:00:00Z",
    "questions_count": 3
  }
]
```

---

## 3. Document APIs

### GET `/api/dataroom/documents/`

List documents with optional filtering.

**Query Parameters:**
- `company_id` (optional, UUID): Filter by company
- `folder_id` (optional, UUID): Filter by folder
- `search` (optional, string): Search by document name

**Response (200 OK):**
```json
[
  {
    "id": "uuid",
    "company": "uuid",
    "folder": "uuid",
    "folder_name": "Financial Documents",
    "name": "Q1 Financial Report.pdf",
    "file": "/media/dataroom/docs/2024/03/report.pdf",
    "size_bytes": 1048576,
    "size": "1.00 MB",
    "access_notes": "Confidential",
    "views_count": 25,
    "downloads_count": 10,
    "upload_date": "2024-03-01T10:00:00Z",
    "questions_count": 3
  }
]
```

### POST `/api/dataroom/documents/`

Upload a new document.

**Request Body (multipart/form-data):**
```
company: uuid (required)
folder: uuid (required)
name: string (required)
file: file (required)
access_notes: string (optional)
```

**Response (201 Created):**
```json
{
  "id": "uuid",
  "company": "uuid",
  "folder": "uuid",
  "folder_name": "Financial Documents",
  "name": "Q1 Financial Report.pdf",
  "file": "/media/dataroom/docs/2024/03/report.pdf",
  "size_bytes": 1048576,
  "size": "1.00 MB",
  "access_notes": "Confidential",
  "views_count": 0,
  "downloads_count": 0,
  "upload_date": "2024-03-01T10:00:00Z",
  "questions_count": 0
}
```

### GET `/api/dataroom/documents/{document_id}/`

Retrieve a specific document (logs view access).

**Response (200 OK):**
```json
{
  "id": "uuid",
  "company": "uuid",
  "folder": "uuid",
  "folder_name": "Financial Documents",
  "name": "Q1 Financial Report.pdf",
  "file": "/media/dataroom/docs/2024/03/report.pdf",
  "size_bytes": 1048576,
  "size": "1.00 MB",
  "access_notes": "Confidential",
  "views_count": 26,
  "downloads_count": 10,
  "upload_date": "2024-03-01T10:00:00Z",
  "questions_count": 3
}
```

### PATCH/PUT `/api/dataroom/documents/{document_id}/`

Update a document.

**Request Body:**
```json
{
  "name": "Updated Document Name.pdf",
  "access_notes": "Updated notes"
}
```

**Response (200 OK):**
```json
{
  "id": "uuid",
  "company": "uuid",
  "folder": "uuid",
  "folder_name": "Financial Documents",
  "name": "Updated Document Name.pdf",
  "file": "/media/dataroom/docs/2024/03/report.pdf",
  "size_bytes": 1048576,
  "size": "1.00 MB",
  "access_notes": "Updated notes",
  "views_count": 26,
  "downloads_count": 10,
  "upload_date": "2024-03-01T10:00:00Z",
  "questions_count": 3
}
```

### GET `/api/dataroom/documents/{document_id}/download/`

Download a document file (logs download access).

**Response (200 OK):**
- Content-Type: `application/octet-stream`
- Content-Disposition: `attachment; filename="document_name.pdf"`
- File stream

**Note:** Increments `downloads_count` and logs access.

---

## 4. Document Version APIs

### GET `/api/dataroom/versions/`

List document versions.

**Query Parameters:**
- `document_id` (required, UUID): Filter by document

**Response (200 OK):**
```json
[
  {
    "id": "uuid",
    "document": "uuid",
    "version_no": 1,
    "file": "/media/dataroom/versions/2024/03/v1.pdf",
    "size_bytes": 1048576,
    "created_at": "2024-03-01T10:00:00Z"
  },
  {
    "id": "uuid",
    "document": "uuid",
    "version_no": 2,
    "file": "/media/dataroom/versions/2024/03/v2.pdf",
    "size_bytes": 1052672,
    "created_at": "2024-03-15T14:30:00Z"
  }
]
```

### POST `/api/dataroom/versions/`

Create a new document version.

**Request Body (multipart/form-data):**
```
document: uuid (required)
file: file (required)
```

**Response (201 Created):**
```json
{
  "id": "uuid",
  "document": "uuid",
  "version_no": 3,
  "file": "/media/dataroom/versions/2024/03/v3.pdf",
  "size_bytes": 1060864,
  "created_at": "2024-03-20T09:00:00Z"
}
```

**Note:** Automatically increments version number and updates document's latest file.

### POST `/api/dataroom/versions/compare/`

Compare two document versions.

**Request Body:**
```json
{
  "old_version_id": "uuid",
  "new_version_id": "uuid"
}
```

**Response (200 OK):**
```json
{
  "document": "uuid",
  "old": {
    "version_no": 1,
    "size_bytes": 1048576,
    "created_at": "2024-03-01T10:00:00Z"
  },
  "new": {
    "version_no": 2,
    "size_bytes": 1052672,
    "created_at": "2024-03-15T14:30:00Z"
  },
  "changed_size_bytes": 4096
}
```

---

## 5. Q&A APIs

### GET `/api/dataroom/qa/`

List questions and answers.

**Query Parameters:**
- `document_id` (optional, UUID): Filter by document
- `company_id` (optional, UUID): Filter by company

**Response (200 OK):**
```json
[
  {
    "id": "uuid",
    "document": "uuid",
    "question": "What is the revenue for Q1?",
    "asked_by": "uuid",
    "asked_by_email": "user@example.com",
    "answer_by": "uuid",
    "answer_by_email": "admin@example.com",
    "answer": "The revenue for Q1 is $500,000.",
    "is_answered": true,
    "created_at": "2024-03-01T10:00:00Z",
    "updated_at": "2024-03-01T11:30:00Z"
  }
]
```

### POST `/api/dataroom/qa/`

Create a new question.

**Request Body:**
```json
{
  "document": "uuid",
  "question": "What is the revenue for Q1?"
}
```

**Response (201 Created):**
```json
{
  "id": "uuid",
  "document": "uuid",
  "question": "What is the revenue for Q1?",
  "asked_by": "uuid",
  "asked_by_email": "user@example.com",
  "answer_by": null,
  "answer_by_email": null,
  "answer": "",
  "is_answered": false,
  "created_at": "2024-03-01T10:00:00Z",
  "updated_at": "2024-03-01T10:00:00Z"
}
```

### GET `/api/dataroom/qa/{question_id}/`

Retrieve a specific question.

**Response (200 OK):**
```json
{
  "id": "uuid",
  "document": "uuid",
  "question": "What is the revenue for Q1?",
  "asked_by": "uuid",
  "asked_by_email": "user@example.com",
  "answer_by": "uuid",
  "answer_by_email": "admin@example.com",
  "answer": "The revenue for Q1 is $500,000.",
  "is_answered": true,
  "created_at": "2024-03-01T10:00:00Z",
  "updated_at": "2024-03-01T11:30:00Z"
}
```

### PATCH/PUT `/api/dataroom/qa/{question_id}/`

Update a question (typically to add an answer).

**Request Body:**
```json
{
  "answer": "The revenue for Q1 is $500,000."
}
```

**Response (200 OK):**
```json
{
  "id": "uuid",
  "document": "uuid",
  "question": "What is the revenue for Q1?",
  "asked_by": "uuid",
  "asked_by_email": "user@example.com",
  "answer_by": "uuid",
  "answer_by_email": "admin@example.com",
  "answer": "The revenue for Q1 is $500,000.",
  "is_answered": true,
  "created_at": "2024-03-01T10:00:00Z",
  "updated_at": "2024-03-01T11:30:00Z"
}
```

**Note:** If `answer` is provided and `is_answered` is false, it automatically sets `is_answered=true` and `answer_by` to the current user.

---

## 6. Access Log APIs

### GET `/api/dataroom/access-logs/`

List access logs.

**Query Parameters:**
- `company_id` (required, UUID): Filter by company
- `action` (optional, string): Filter by action (`view` or `download`)

**Response (200 OK):**
```json
[
  {
    "id": "uuid",
    "company": "uuid",
    "user": "uuid",
    "user_email": "user@example.com",
    "document": "uuid",
    "document_name": "Q1 Financial Report.pdf",
    "action": "view",
    "timestamp": "2024-03-01T10:00:00Z",
    "ip_address": "192.168.1.1",
    "created_at": "2024-03-01T10:00:00Z"
  }
]
```

### POST `/api/dataroom/access-logs/`

Create a new access log entry.

**Request Body:**
```json
{
  "company": "uuid",
  "document": "uuid",
  "action": "view",
  "ip_address": "192.168.1.1"
}
```

**Response (201 Created):**
```json
{
  "id": "uuid",
  "company": "uuid",
  "user": "uuid",
  "user_email": "user@example.com",
  "document": "uuid",
  "document_name": "Q1 Financial Report.pdf",
  "action": "view",
  "timestamp": "2024-03-01T10:00:00Z",
  "ip_address": "192.168.1.1",
  "created_at": "2024-03-01T10:00:00Z"
}
```

---

## 7. Company Folder Selection APIs

### GET `/api/dataroom/company/folders/available/`

List all available folders with selection status for the company.

**Response (200 OK):**
```json
[
  {
    "id": "uuid",
    "name": "Financial Documents",
    "description": "All financial related documents",
    "is_active": true,
    "is_selected": true,
    "created_at": "2024-01-15T10:30:00Z"
  },
  {
    "id": "uuid",
    "name": "Legal Documents",
    "description": "Legal and compliance documents",
    "is_active": true,
    "is_selected": false,
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

### POST `/api/dataroom/company/folders/select/`

Select folders for the company.

**Request Body:**
```json
{
  "folder_ids": ["uuid1", "uuid2", "uuid3"]
}
```

**Response (201 Created):**
```json
{
  "message": "Selected 3 folder(s).",
  "selected_count": 3,
  "total_selected": 5
}
```

### DELETE `/api/dataroom/company/folders/select/`

Deselect folders for the company.

**Request Body:**
```json
{
  "folder_ids": ["uuid1", "uuid2"]
}
```

**Response (200 OK):**
```json
{
  "message": "Deselected 2 folder(s).",
  "deselected_count": 2,
  "total_selected": 3
}
```

### GET `/api/dataroom/company/folders/selected/`

List folders selected by the company.

**Response (200 OK):**
```json
[
  {
    "id": "uuid",
    "folder": "uuid",
    "folder_name": "Financial Documents",
    "folder_description": "All financial related documents",
    "selected_at": "2024-03-01T10:00:00Z",
    "created_at": "2024-03-01T10:00:00Z"
  }
]
```

---

## 8. Company Category Selection APIs

### GET `/api/dataroom/company/categories/available/`

List available categories from folders selected by the company.

**Response (200 OK):**
```json
[
  {
    "id": "uuid",
    "folder_id": "uuid",
    "folder_name": "Financial Documents",
    "name": "Quarterly Reports",
    "description": "Quarterly financial reports",
    "is_active": true,
    "is_selected": true,
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

**Note:** If no folders are selected, returns:
```json
{
  "results": [],
  "message": "Please select folders first to view available categories.",
  "selected_folders_count": 0,
  "hint": "Use POST /api/dataroom/company/folders/select/ to select folders first."
}
```

### POST `/api/dataroom/company/categories/select/`

Select categories for the company.

**Request Body:**
```json
{
  "category_ids": ["uuid1", "uuid2", "uuid3"]
}
```

**Response (201 Created):**
```json
{
  "message": "Selected 3 category/categories.",
  "selected_count": 3,
  "total_selected": 5
}
```

**Note:** Categories must belong to folders already selected by the company.

### DELETE `/api/dataroom/company/categories/select/`

Deselect categories for the company.

**Request Body:**
```json
{
  "category_ids": ["uuid1", "uuid2"]
}
```

**Response (200 OK):**
```json
{
  "message": "Deselected 2 category/categories.",
  "deselected_count": 2,
  "total_selected": 3
}
```

### GET `/api/dataroom/company/categories/selected/`

List categories selected by the company.

**Response (200 OK):**
```json
[
  {
    "id": "uuid",
    "category": "uuid",
    "category_name": "Quarterly Reports",
    "category_description": "Quarterly financial reports",
    "folder_id": "uuid",
    "folder_name": "Financial Documents",
    "selected_at": "2024-03-01T10:00:00Z",
    "created_at": "2024-03-01T10:00:00Z"
  }
]
```

---

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request
```json
{
  "detail": "Error message describing what went wrong"
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
  "detail": "Not found."
}
```

### 500 Internal Server Error
```json
{
  "detail": "A server error occurred."
}
```

---

## Field Descriptions

### Folder Fields
- `id`: UUID - Unique identifier
- `name`: String (max 200) - Folder name (unique)
- `description`: Text - Folder description
- `is_active`: Boolean - Whether folder is active
- `created_at`: DateTime - Creation timestamp

### Document Fields
- `id`: UUID - Unique identifier
- `company`: UUID - Company ID (foreign key)
- `folder`: UUID - Folder ID (foreign key)
- `folder_name`: String (read-only) - Folder name
- `name`: String (max 255) - Document name
- `file`: File - Document file path
- `size_bytes`: BigInteger - File size in bytes
- `size`: String (read-only) - Human-readable file size (KB, MB, GB)
- `access_notes`: String (max 255) - Access notes
- `views_count`: Integer - Number of views
- `downloads_count`: Integer - Number of downloads
- `upload_date`: DateTime (read-only) - Upload timestamp
- `questions_count`: Integer (read-only) - Number of questions

### Document Version Fields
- `id`: UUID - Unique identifier
- `document`: UUID - Document ID (foreign key)
- `version_no`: Integer - Version number
- `file`: File - Version file path
- `size_bytes`: BigInteger - File size in bytes
- `created_at`: DateTime - Creation timestamp

### Question Fields
- `id`: UUID - Unique identifier
- `document`: UUID - Document ID (foreign key)
- `question`: Text - Question text
- `asked_by`: UUID - User who asked (foreign key)
- `asked_by_email`: String (read-only) - Email of user who asked
- `answer_by`: UUID - User who answered (foreign key, nullable)
- `answer_by_email`: String (read-only) - Email of user who answered
- `answer`: Text - Answer text
- `is_answered`: Boolean - Whether question is answered
- `created_at`: DateTime - Creation timestamp
- `updated_at`: DateTime - Last update timestamp

### Access Log Fields
- `id`: UUID - Unique identifier
- `company`: UUID - Company ID (foreign key)
- `user`: UUID - User ID (foreign key, nullable)
- `user_email`: String (read-only) - User email
- `document`: UUID - Document ID (foreign key, nullable)
- `document_name`: String (read-only) - Document name
- `action`: String - Action type (`view` or `download`)
- `timestamp`: DateTime - Action timestamp
- `ip_address`: IP Address - IP address of requester
- `created_at`: DateTime - Creation timestamp

---

## Notes

1. **Authentication**: All endpoints require JWT authentication via the `Authorization: Bearer <token>` header.

2. **Permissions**:
   - Superusers can create folders and see all folders
   - Regular users only see folders selected by their company
   - Documents are filtered by company's selected folders for non-superusers

3. **File Uploads**: Use `multipart/form-data` content type for file uploads.

4. **Automatic Logging**: 
   - Viewing a document (GET `/documents/{id}/`) automatically logs a view and increments `views_count`
   - Downloading a document (GET `/documents/{id}/download/`) automatically logs a download and increments `downloads_count`

5. **Version Management**: Creating a new version automatically:
   - Increments the version number
   - Updates the document's latest file and size

6. **Q&A Auto-flagging**: When an answer is provided to a question, `is_answered` is automatically set to `true` and `answer_by` is set to the current user.

