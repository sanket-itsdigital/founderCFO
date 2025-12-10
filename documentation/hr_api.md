# HR Module API Documentation

## Overview
The HR (Human Resources) module provides comprehensive APIs for managing employee data, tracking headcount metrics, analyzing compensation, and generating HR analytics. This documentation covers all available endpoints, request/response formats, and usage examples.

---

## Table of Contents
1. [Authentication](#authentication)
2. [Base URL](#base-url)
3. [Common Parameters](#common-parameters)
4. [API Endpoints](#api-endpoints)
   - [HR Dashboard](#1-hr-dashboard)
   - [Headcount Overview](#2-headcount-overview)
   - [Headcount by Department](#3-headcount-by-department)
   - [Headcount by Location](#4-headcount-by-location)
   - [Headcount Employees](#5-headcount-employees)
   - [Compensation Overview](#6-compensation-overview)
   - [HR Analytics](#7-hr-analytics)
5. [Models](#models)
6. [Enums](#enums)
7. [Error Handling](#error-handling)

---

## Authentication
All HR API endpoints require authentication using Bearer token.

**Header:**
```
Authorization: Bearer <your_access_token>
```

---

## Base URL
```
/api/hr/
```

---

## Common Parameters

### Query Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| company_id | UUID | Yes | The unique identifier of the company |

---

## API Endpoints

### 1. HR Dashboard

**Endpoint:** `GET /api/hr/dashboard/`

**Description:** Returns comprehensive HR dashboard data including high-level KPIs, detailed HR metrics, workforce composition, and gender diversity.

#### Request
```http
GET /api/hr/dashboard/?company_id=<company_id>
Authorization: Bearer <token>
```

#### Response Structure
```json
{
  "kpi_cards": [
    {
      "title": "HR Health",
      "value": "85",
      "change": "+5%",
      "trend": "up",
      "icon": "health",
      "color": "#4CAF50"
    },
    {
      "title": "Total Headcount",
      "value": "150",
      "change": "+10",
      "trend": "up",
      "icon": "people",
      "color": "#2196F3"
    },
    {
      "title": "Turnover Rate",
      "value": "12.5%",
      "change": "-2%",
      "trend": "down",
      "icon": "trending_down",
      "color": "#FF9800"
    },
    {
      "title": "Time to Hire",
      "value": "45 days",
      "change": "-5 days",
      "trend": "down",
      "icon": "schedule",
      "color": "#9C27B0"
    },
    {
      "title": "Cost per Hire",
      "value": "₹3.5L",
      "change": "+₹0.2L",
      "trend": "up",
      "icon": "attach_money",
      "color": "#F44336"
    }
  ],
  "hr_metrics": {
    "engagement_score": {
      "current": 78.5,
      "target": 80.0,
      "progress": 98.1,
      "status": "warning"
    },
    "retention_rate": {
      "current": 87.5,
      "target": 90.0,
      "progress": 97.2,
      "status": "warning"
    },
    "time_to_fill": {
      "current": 45.0,
      "target": 30.0,
      "progress": 66.7,
      "status": "critical"
    },
    "diversity_index": {
      "current": 65.0,
      "target": 50.0,
      "progress": 100.0,
      "status": "good"
    }
  },
  "workforce_composition": {
    "full_time": {
      "count": 120,
      "percentage": 80.0
    },
    "part_time": {
      "count": 15,
      "percentage": 10.0
    },
    "contract": {
      "count": 10,
      "percentage": 6.7
    },
    "intern": {
      "count": 5,
      "percentage": 3.3
    },
    "total": 150
  },
  "gender_diversity": {
    "male": {
      "count": 90,
      "percentage": 60.0
    },
    "female": {
      "count": 55,
      "percentage": 36.7
    },
    "other": {
      "count": 5,
      "percentage": 3.3
    },
    "total": 150
  }
}
```

#### Key Metrics Explained

**KPI Cards:**
- **HR Health**: Overall HR health score (0-100)
- **Total Headcount**: Total number of active employees
- **Turnover Rate**: Percentage of employees who left in the last year
- **Time to Hire**: Average days to fill a position
- **Cost per Hire**: Average cost to hire a new employee

**HR Metrics:**
- **Engagement Score**: Employee engagement level (target: 80%)
- **Retention Rate**: Percentage of employees retained (target: 90%)
- **Time to Fill**: Days to fill open positions (target: 30 days)
- **Diversity Index**: Diversity score (target: 50%)

**Status Indicators:**
- `good`: Progress >= 100% of target
- `warning`: Progress >= 90% but < 100%
- `critical`: Progress < 90%

---

### 2. Headcount Overview

**Endpoint:** `GET /api/hr/headcount/overview/`

**Description:** Returns comprehensive headcount dashboard data including overview metrics, headcount by department, location, and level distribution.

#### Request
```http
GET /api/hr/headcount/overview/?company_id=<company_id>
Authorization: Bearer <token>
```

#### Response Structure
```json
{
  "overview": {
    "total_headcount": 150,
    "total_departments": 8,
    "total_locations": 5
  },
  "headcount_by_department": [
    {
      "department": "Engineering",
      "headcount": 60,
      "percentage": 40.0,
      "avg_tenure_years": 3.5
    },
    {
      "department": "Sales",
      "headcount": 30,
      "percentage": 20.0,
      "avg_tenure_years": 2.8
    },
    {
      "department": "Marketing",
      "headcount": 20,
      "percentage": 13.3,
      "avg_tenure_years": 2.1
    }
  ],
  "headcount_by_location": [
    {
      "location": "Mumbai",
      "headcount": 80,
      "percentage": 53.3
    },
    {
      "location": "Bangalore",
      "headcount": 45,
      "percentage": 30.0
    },
    {
      "location": "Delhi",
      "headcount": 25,
      "percentage": 16.7
    }
  ],
  "level_distribution": [
    {
      "level": "Senior",
      "headcount": 20,
      "percentage": 13.3
    },
    {
      "level": "Mid",
      "headcount": 60,
      "percentage": 40.0
    },
    {
      "level": "Junior",
      "headcount": 50,
      "percentage": 33.3
    },
    {
      "level": "Intern",
      "headcount": 20,
      "percentage": 13.3
    }
  ]
}
```

---

### 3. Headcount by Department

**Endpoint:** `GET /api/hr/headcount/by-department/`

**Description:** Returns detailed headcount breakdown by department with drill-down capability.

#### Request
```http
GET /api/hr/headcount/by-department/?company_id=<company_id>&department=<department_name>
Authorization: Bearer <token>
```

#### Query Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| company_id | UUID | Yes | Company identifier |
| department | String | No | Department name for drill-down |

#### Response Structure

**Without department parameter (summary view):**
```json
{
  "departments": [
    {
      "department": "Engineering",
      "headcount": 60,
      "percentage": 40.0
    },
    {
      "department": "Sales",
      "headcount": 30,
      "percentage": 20.0
    }
  ],
  "total_headcount": 150
}
```

**With department parameter (detailed view):**
```json
{
  "department": "Engineering",
  "total_headcount": 60,
  "employees": [
    {
      "id": "uuid",
      "name": "John Doe",
      "role": "Senior Software Engineer",
      "level": "Senior",
      "tenure_years": 3.5,
      "location": "Mumbai",
      "employment_type": "Full-time"
    }
  ]
}
```

---

### 4. Headcount by Location

**Endpoint:** `GET /api/hr/headcount/by-location/`

**Description:** Returns detailed headcount breakdown by location with drill-down capability.

#### Request
```http
GET /api/hr/headcount/by-location/?company_id=<company_id>&location=<location_name>
Authorization: Bearer <token>
```

#### Query Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| company_id | UUID | Yes | Company identifier |
| location | String | No | Location name for drill-down |

#### Response Structure

**Without location parameter (summary view):**
```json
{
  "locations": [
    {
      "location": "Mumbai",
      "headcount": 80,
      "percentage": 53.3
    },
    {
      "location": "Bangalore",
      "headcount": 45,
      "percentage": 30.0
    }
  ],
  "total_headcount": 150
}
```

**With location parameter (detailed view):**
```json
{
  "location": "Mumbai",
  "total_headcount": 80,
  "employees": [
    {
      "id": "uuid",
      "name": "Jane Smith",
      "role": "Product Manager",
      "department": "Product",
      "level": "Senior",
      "tenure_years": 4.2,
      "employment_type": "Full-time"
    }
  ]
}
```

---

### 5. Headcount Employees

**Endpoint:** `GET /api/hr/headcount/employees/`

**Description:** Returns a list of all active employees with filtering and search capabilities.

#### Request
```http
GET /api/hr/headcount/employees/?company_id=<company_id>&department=<dept>&location=<loc>&search=<query>
Authorization: Bearer <token>
```

#### Query Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| company_id | UUID | Yes | Company identifier |
| department | String | No | Filter by department name |
| location | String | No | Filter by location |
| level | String | No | Filter by level (Senior, Mid, Junior, Intern) |
| employment_type | String | No | Filter by type (Full-time, Part-time, Contract, Intern) |
| search | String | No | Search by name or role |

#### Response Structure
```json
{
  "employees": [
    {
      "id": "uuid",
      "name": "John Doe",
      "email": "john.doe@example.com",
      "role": "Senior Software Engineer",
      "department": "Engineering",
      "location": "Mumbai",
      "level": "Senior",
      "employment_type": "Full-time",
      "start_date": "2020-01-15",
      "tenure_years": 4.0,
      "base_salary_annual": 1200000.00,
      "status": "Active"
    }
  ],
  "total_count": 150,
  "filters_applied": {
    "department": "Engineering",
    "location": null,
    "level": null,
    "employment_type": null,
    "search": null
  }
}
```

---

### 6. Compensation Overview

**Endpoint:** `GET /api/hr/compensation/overview/`

**Description:** Returns comprehensive compensation dashboard data including overview metrics, compensation by department, salary by level, and compensation summary.

#### Request
```http
GET /api/hr/compensation/overview/?company_id=<company_id>
Authorization: Bearer <token>
```

#### Response Structure
```json
{
  "overview": {
    "avg_salary_annual": 850000.00,
    "median_salary_annual": 750000.00,
    "total_payroll_annual": 127500000.00,
    "total_employees": 150,
    "total_benefits_annual": 12750000.00,
    "benefits_percentage_of_payroll": 10.0,
    "bonus_pool_annual": 6375000.00,
    "bonus_percentage_of_base": 5.0
  },
  "compensation_by_department": [
    {
      "department": "Engineering",
      "avg_salary": 1100000.00,
      "median_salary": 950000.00,
      "min_salary": 600000.00,
      "max_salary": 2500000.00,
      "headcount": 60
    },
    {
      "department": "Sales",
      "avg_salary": 900000.00,
      "median_salary": 800000.00,
      "min_salary": 500000.00,
      "max_salary": 1800000.00,
      "headcount": 30
    }
  ],
  "salary_by_level": [
    {
      "level": "Senior",
      "total_salary": 45000000.00,
      "percentage_of_total": 35.3,
      "headcount": 20,
      "avg_salary": 2250000.00
    },
    {
      "level": "Mid",
      "total_salary": 54000000.00,
      "percentage_of_total": 42.4,
      "headcount": 60,
      "avg_salary": 900000.00
    },
    {
      "level": "Junior",
      "total_salary": 25000000.00,
      "percentage_of_total": 19.6,
      "headcount": 50,
      "avg_salary": 500000.00
    },
    {
      "level": "Intern",
      "total_salary": 3500000.00,
      "percentage_of_total": 2.7,
      "headcount": 20,
      "avg_salary": 175000.00
    }
  ],
  "compensation_summary": {
    "base_salaries": 127500000.00,
    "benefits": 12750000.00,
    "bonus_pool": 6375000.00,
    "total_compensation": 146625000.00
  }
}
```

---

### 7. HR Analytics

**Endpoint:** `GET /api/hr/analytics/`

**Description:** Returns advanced HR analytics including turnover analysis, tenure distribution, hiring trends, and department growth.

#### Request
```http
GET /api/hr/analytics/?company_id=<company_id>&period=<period>
Authorization: Bearer <token>
```

#### Query Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| company_id | UUID | Yes | Company identifier |
| period | String | No | Time period (month, quarter, year, all). Default: year |

#### Response Structure
```json
{
  "turnover_analysis": {
    "period": "year",
    "total_separations": 18,
    "voluntary_separations": 12,
    "involuntary_separations": 6,
    "turnover_rate": 12.5,
    "voluntary_turnover_rate": 8.3,
    "involuntary_turnover_rate": 4.2,
    "avg_tenure_at_exit": 2.3
  },
  "tenure_distribution": [
    {
      "tenure_range": "0-1 years",
      "count": 40,
      "percentage": 26.7
    },
    {
      "tenure_range": "1-3 years",
      "count": 50,
      "percentage": 33.3
    },
    {
      "tenure_range": "3-5 years",
      "count": 35,
      "percentage": 23.3
    },
    {
      "tenure_range": "5+ years",
      "count": 25,
      "percentage": 16.7
    }
  ],
  "hiring_trends": {
    "last_12_months": [
      {
        "month": "2024-12",
        "hires": 8,
        "separations": 2,
        "net_change": 6
      },
      {
        "month": "2024-11",
        "hires": 5,
        "separations": 1,
        "net_change": 4
      }
    ],
    "total_hires_ytd": 45,
    "total_separations_ytd": 18,
    "net_growth_ytd": 27
  },
  "department_growth": [
    {
      "department": "Engineering",
      "start_of_period": 50,
      "current": 60,
      "growth": 10,
      "growth_percentage": 20.0
    },
    {
      "department": "Sales",
      "start_of_period": 25,
      "current": 30,
      "growth": 5,
      "growth_percentage": 20.0
    }
  ]
}
```

---

## Models

### Headcount Model
Represents an employee in the system.

**Fields:**
- `id` (UUID): Unique identifier
- `company` (FK): Reference to Company
- `first_name` (String): Employee's first name
- `last_name` (String): Employee's last name
- `email` (String): Employee's email address
- `department` (FK): Reference to Department
- `role` (FK): Reference to Role
- `level` (Enum): Employee level (Senior, Mid, Junior, Intern)
- `location` (String): Work location
- `employment_type` (Enum): Type of employment (Full-time, Part-time, Contract, Intern)
- `employment_status` (Enum): Current status (Active, Inactive, Resigned, Terminated)
- `start_date` (Date): Employment start date
- `end_date` (Date): Employment end date (if applicable)
- `base_salary_annual` (Decimal): Annual base salary
- `benefits_annual` (Decimal): Annual benefits amount
- `bonus_percentage` (Decimal): Bonus as percentage of base salary
- `gender` (Enum): Gender (Male, Female, Other, Prefer not to say)
- `created_at` (DateTime): Record creation timestamp
- `updated_at` (DateTime): Record update timestamp

### Department Model
Represents a department within the company.

**Fields:**
- `id` (UUID): Unique identifier
- `company` (FK): Reference to Company
- `name` (String): Department name
- `description` (Text): Department description
- `created_at` (DateTime): Record creation timestamp
- `updated_at` (DateTime): Record update timestamp

### Role Model
Represents a job role/position.

**Fields:**
- `id` (UUID): Unique identifier
- `company` (FK): Reference to Company
- `title` (String): Role title
- `description` (Text): Role description
- `department` (FK): Reference to Department
- `created_at` (DateTime): Record creation timestamp
- `updated_at` (DateTime): Record update timestamp

---

## Enums

### EmploymentStatus
- `ACTIVE`: Currently employed
- `INACTIVE`: Temporarily inactive
- `RESIGNED`: Voluntarily resigned
- `TERMINATED`: Involuntarily terminated

### EmploymentType
- `FULL_TIME`: Full-time employee
- `PART_TIME`: Part-time employee
- `CONTRACT`: Contract worker
- `INTERN`: Intern

### Level
- `SENIOR`: Senior level
- `MID`: Mid level
- `JUNIOR`: Junior level
- `INTERN`: Intern level

### Gender
- `MALE`: Male
- `FEMALE`: Female
- `OTHER`: Other
- `PREFER_NOT_TO_SAY`: Prefer not to say

---

## Error Handling

### Standard Error Response
```json
{
  "error": "Error message description"
}
```

### Common HTTP Status Codes

| Status Code | Description |
|------------|-------------|
| 200 | Success |
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Missing or invalid authentication |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Company or resource not found |
| 500 | Internal Server Error |

### Common Error Scenarios

**Missing company_id:**
```json
{
  "error": "company_id is required"
}
```
Status Code: 400

**Company not found:**
```json
{
  "error": "Company not found"
}
```
Status Code: 404

**Unauthorized access:**
```json
{
  "detail": "Authentication credentials were not provided."
}
```
Status Code: 401

---

## Usage Examples

### Example 1: Get HR Dashboard
```bash
curl -X GET \
  'https://api.example.com/api/hr/dashboard/?company_id=123e4567-e89b-12d3-a456-426614174000' \
  -H 'Authorization: Bearer your_access_token'
```

### Example 2: Get Headcount by Department with Drill-down
```bash
# Get all departments
curl -X GET \
  'https://api.example.com/api/hr/headcount/by-department/?company_id=123e4567-e89b-12d3-a456-426614174000' \
  -H 'Authorization: Bearer your_access_token'

# Drill down into Engineering department
curl -X GET \
  'https://api.example.com/api/hr/headcount/by-department/?company_id=123e4567-e89b-12d3-a456-426614174000&department=Engineering' \
  -H 'Authorization: Bearer your_access_token'
```

### Example 3: Search Employees
```bash
curl -X GET \
  'https://api.example.com/api/hr/headcount/employees/?company_id=123e4567-e89b-12d3-a456-426614174000&department=Engineering&search=John' \
  -H 'Authorization: Bearer your_access_token'
```

### Example 4: Get Analytics for Last Quarter
```bash
curl -X GET \
  'https://api.example.com/api/hr/analytics/?company_id=123e4567-e89b-12d3-a456-426614174000&period=quarter' \
  -H 'Authorization: Bearer your_access_token'
```

---

## Best Practices

1. **Always include company_id**: All endpoints require a valid company_id parameter
2. **Cache responses**: Dashboard and overview data can be cached for performance
3. **Use pagination**: For large employee lists, implement pagination on the client side
4. **Handle errors gracefully**: Always check for error responses and handle them appropriately
5. **Secure tokens**: Keep authentication tokens secure and refresh them regularly
6. **Rate limiting**: Be mindful of API rate limits and implement appropriate retry logic

---

## Support

For issues or questions regarding the HR API, please contact:
- Email: support@foundercfo.com
- Documentation: https://docs.foundercfo.com/hr

---

## Changelog

### Version 1.0 (December 2025)
- Initial release of HR API
- Dashboard, Headcount, Compensation, and Analytics endpoints
- Support for department and location drill-downs
- Employee search and filtering capabilities
