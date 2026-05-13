"""
API Documentation - El Malick Gest REST API
=============================================

Base URL: http://localhost:8000/api

Authentication:
  - JWT Bearer Token (for admin/staff endpoints)
  - Parent PIN-based (for parent portal)

=============================================================================
SECTION 1: AUTHENTICATION & ADMIN ENDPOINTS
=============================================================================

1. POST /auth/token
   Purpose: Login and obtain JWT Bearer token
   
   Request Body:
   {
     "username": "admin",
     "password": "admin"
   }
   
   Response (200 OK):
   {
     "access_token": "eyJhbGciOiJIUzI1NiIs...",
     "token_type": "bearer",
     "role": "Admin",
     "username": "admin"
   }
   
   Error (401):
   {"detail": "Identifiants incorrects"}


=============================================================================
SECTION 2: STUDENT ENDPOINTS (Admin/Staff/Teacher only)
=============================================================================

2. GET /students/?q=<search>&page=<n>&page_size=<size>
   Purpose: List all students with optional search and pagination
   
   Headers:
     Authorization: Bearer <token>
   
   Query Parameters:
     - q: Search query (first_name, last_name, or Arabic names)
     - page: Page number (default: 1)
     - page_size: Items per page (default: 20, max: 100)
   
   Response (200 OK):
   {
     "total": 3,
     "page": 1,
     "page_size": 20,
     "data": [
       {
         "id": 1,
         "first_name_fr": "Ahmed",
         "last_name_fr": "Ben Ali",
         "first_name_ar": "أحمد",
         "last_name_ar": "بن علي",
         "gender": "M",
         "birth_date": "2015-05-10",
         "status": "Active",
         "class_name": "6e Année A"
       }
     ]
   }
   
   Error (401):
     {"detail": "Token invalide ou expiré"}
   Error (500):
     {"detail": "Erreur serveur"}


3. GET /students/{student_id}
   Purpose: Get detailed info about a specific student
   
   Headers:
     Authorization: Bearer <token>
   
   Path Parameters:
     - student_id: Student ID (integer)
   
   Response (200 OK):
   {
     "id": 1,
     "first_name_fr": "Ahmed",
     "last_name_fr": "Ben Ali",
     "birth_date": "2015-05-10",
     ...
   }
   
   Error (404):
     {"detail": "Élève introuvable"}


4. GET /students/{student_id}/grades
   Purpose: Get student's grades in current academic year
   
   Headers:
     Authorization: Bearer <token>
   
   Response (200 OK):
   [
     {
       "id": 5,
       "score": 15.5,
       "period": "1er Trimestre",
       "exam_type": "Interrogation",
       "subject": "Mathématiques",
       "coefficient": 2.0,
       "max_score": 20.0
     }
   ]


5. GET /students/{student_id}/attendance
   Purpose: Get student's attendance records (last 90 days)
   
   Headers:
     Authorization: Bearer <token>
   
   Response (200 OK):
   [
     {
       "date": "2026-05-01",
       "status": "Présent",
       "reason": null
     },
     {
       "date": "2026-04-30",
       "status": "Absent",
       "reason": "Malade"
     }
   ]
   
   Status values: "Présent", "Absent", "Retard", "Exclu"


6. GET /students/{student_id}/dues
   Purpose: Get student's school fees/dues for current year
   
   Headers:
     Authorization: Bearer <token>
   
   Response (200 OK):
   [
     {
       "id": 2,
       "label": "Frais d'inscription",
       "amount": 50000.0,
       "due_date": "2026-09-15",
       "is_paid": 0
     },
     {
       "id": 3,
       "label": "Frais de scolarité - Q1",
       "amount": 120000.0,
       "due_date": "2026-10-31",
       "is_paid": 1
     }
   ]
   
   Note: is_paid = 0 (unpaid), 1 (paid)


=============================================================================
SECTION 3: PARENT PORTAL ENDPOINTS
=============================================================================

7. POST /parent/login
   Purpose: Parent/Student login via student code + PIN
   
   Request Body:
   {
     "student_code": "1",
     "pin": "1234"
   }
   
   Response (200 OK):
   {
     "access_token": "eyJhbGciOiJIUzI1NiIs...",
     "token_type": "bearer",
     "student_name": "Ahmed Ben Ali",
     "parent_name": "Ali Ben Mohamed"
   }
   
   Error (404):
     {"detail": "Élève introuvable"}
   Error (401):
     {"detail": "PIN incorrect"}
   
   NOTE: On first login, if PIN is not set, any PIN is accepted and stored.
         On subsequent logins, the stored PIN is required.


8. GET /parent/me
   Purpose: Get authenticated student's profile (via parent token)
   
   Headers:
     Authorization: Bearer <parent_token>
   
   Response (200 OK):
   {
     "first_name_fr": "Ahmed",
     "last_name_fr": "Ben Ali",
     "first_name_ar": "أحمد",
     "last_name_ar": "بن علي",
     "birth_date": "2015-05-10",
     "gender": "M",
     "parent_name": "Ali Ben Mohamed",
     "parent_phone": "+212612345678",
     "parent_email": "ali@example.com",
     "class_name": "6e Année A",
     "academic_year": "2025-2026"
   }


9. GET /parent/grades
   Purpose: Get student's grades (parent view)
   
   Headers:
     Authorization: Bearer <parent_token>
   
   Response (200 OK):
   [
     {
       "period": "1er Trimestre",
       "exam_type": "Interrogation",
       "score": 15.5,
       "subject": "Mathématiques",
       "coefficient": 2.0,
       "max_score": 20.0
     }
   ]


10. GET /parent/attendance
    Purpose: Get student's attendance (parent view)
    
    Headers:
      Authorization: Bearer <parent_token>
    
    Response (200 OK):
    [
      {
        "date": "2026-05-01",
        "status": "Présent",
        "reason": null
      }
    ]


11. GET /parent/dues
    Purpose: Get student's school fees (parent view)
    
    Headers:
      Authorization: Bearer <parent_token>
    
    Response (200 OK):
    [
      {
        "label": "Frais d'inscription",
        "amount": 50000.0,
        "due_date": "2026-09-15",
        "is_paid": 0
      }
    ]


=============================================================================
SECTION 4: HEALTH & SYSTEM ENDPOINTS
=============================================================================

12. GET /health
    Purpose: Check API and database status
    
    Response (200 OK):
    {"status": "ok", "database": "connected"}
    
    Response (503 Service Unavailable):
    {"status": "error", "database": "Connection refused..."}


13. GET / (or /api)
    Purpose: API info and version
    
    Response (200 OK):
    {
      "name": "El Malick Gest API",
      "version": "1.0.0",
      "docs": "/api/docs"
    }


=============================================================================
EXAMPLE WORKFLOWS
=============================================================================

WORKFLOW 1: Admin accessing student list
─────────────────────────────────────────

Step 1: Login to get token
  POST /auth/token
  Body: {"username": "admin", "password": "admin"}
  Response: token = "eyJhbGciOiJIUzI1NiIs..."

Step 2: List students with token
  GET /students/?page=1&page_size=20
  Header: Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
  Response: 200 OK + 20 students

Step 3: Get specific student details
  GET /students/1
  Header: Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
  Response: 200 OK + detailed student record


WORKFLOW 2: Parent checking child's grades
───────────────────────────────────────────

Step 1: Parent login with student code + PIN
  POST /parent/login
  Body: {"student_code": "1", "pin": "1234"}
  Response: parent_token = "eyJhbGciOiJIUzI1NiIs..."

Step 2: Get child's grades
  GET /parent/grades
  Header: Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
  Response: 200 OK + list of grades

Step 3: Check attendance
  GET /parent/attendance
  Header: Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
  Response: 200 OK + attendance records


=============================================================================
ERROR CODES & MEANINGS
=============================================================================

200 OK              Request successful
201 Created         Resource created
400 Bad Request     Invalid request data
401 Unauthorized    Missing or invalid token/credentials
403 Forbidden       User role not allowed for this resource
404 Not Found       Resource not found
500 Server Error    Internal server error
503 Unavailable     Database or service unavailable


=============================================================================
TESTING & CURL EXAMPLES
=============================================================================

# 1. Test API health
curl -s http://localhost:8000/api/health

# 2. Login as admin
curl -X POST http://localhost:8000/api/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin"

# 3. List students (replace TOKEN with actual token)
curl -H "Authorization: Bearer TOKEN" \
  http://localhost:8000/api/students/

# 4. Get student 1 details
curl -H "Authorization: Bearer TOKEN" \
  http://localhost:8000/api/students/1

# 5. Parent login
curl -X POST http://localhost:8000/api/parent/login \
  -H "Content-Type: application/json" \
  -d '{"student_code":"1","pin":"1234"}'

# 6. Get parent's student profile (replace PARENT_TOKEN)
curl -H "Authorization: Bearer PARENT_TOKEN" \
  http://localhost:8000/api/parent/me


=============================================================================
INTERACTIVE API DOCUMENTATION
=============================================================================

Access Swagger UI for interactive testing:
  http://localhost:8000/api/docs

Access ReDoc for static documentation:
  http://localhost:8000/api/redoc


=============================================================================
DEPLOYMENT CHECKLIST
=============================================================================

Before going to production:

[ ] Set ELMALICK_API_SECRET environment variable (for JWT signing)
[ ] Set ELMALICK_DB_PASSWORD environment variable (for DB access)
[ ] Set ALLOWED_ORIGINS environment variable (CORS whitelisting)
[ ] Disable hot-reload: remove --reload flag from uvicorn
[ ] Enable SSL: use --ssl-certfile and --ssl-keyfile
[ ] Set up reverse proxy (nginx/Apache)
[ ] Monitor logs and errors
[ ] Rate limit endpoints (optional: FastAPI Limiter)
[ ] Set up alerting for 5xx errors


=============================================================================
TROUBLESHOOTING
=============================================================================

Q: Token expired error?
A: Tokens expire after 60 minutes. Request a new token via /auth/token

Q: Parent PIN login fails?
A: First login will accept any PIN and store it. Subsequent logins require
   the stored PIN. If forgotten, admin must reset via dashboard.

Q: Class name showing as null?
A: Ensure student is assigned to a class in the current academic year.

Q: API slow or timing out?
A: Check database connection, ensure PostgreSQL is running and accessible.

Q: CORS errors in browser?
A: Set ALLOWED_ORIGINS environment variable with your frontend domain.
   Example: ALLOWED_ORIGINS="http://localhost:3000,https://myapp.com"
"""
