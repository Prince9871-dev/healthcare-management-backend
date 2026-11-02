# Healthcare Management Backend

A production-conscious, secure, and robust Django REST Framework backend designed for healthcare management systems. Built with clean architecture, enterprise security practices, and thorough automated test coverage.

---

## Tech Stack

- **Language:** Python 3.12+
- **Framework:** Django 6.1+
- **API Framework:** Django REST Framework 3.18+
- **Authentication:** `djangorestframework-simplejwt` (JWT Bearer tokens)
- **Database:** PostgreSQL 18 with `psycopg` (v3)
- **Environment Management:** `django-environ`

---

## Architecture & Database Integrity

### 1. Custom User Model (`accounts.User`)
- **Base Classes:** Extends Django's `AbstractBaseUser` and `PermissionsMixin`.
- **Primary Key:** `UUID` (`uuid.uuid4`) to prevent sequential enumeration attacks and support distributed database designs.
- **Login Identifier:** `email` (`USERNAME_FIELD = 'email'`), indexed and normalized.
- **User Manager:** Custom `UserManager` (`BaseUserManager`) implementing case-insensitive email natural key resolution, email normalization, and password hashing via Django's cryptographic PBKDF2/Argon2 hashing algorithm.

### 2. Database-Level Case-Insensitive Email Uniqueness
To prevent duplicate accounts regardless of capitalization (e.g., `Prince@example.com`, `prince@example.com`, and `PRINCE@example.com`), the model enforces a **database-level functional unique constraint**:

```python
constraints = [
    UniqueConstraint(
        Lower("email"),
        name="unique_case_insensitive_email",
    ),
]
```

In PostgreSQL, this creates a functional unique B-Tree index:
```sql
CREATE UNIQUE INDEX "unique_case_insensitive_email" ON "accounts_user" ((LOWER("email")));
```

**Benefits:**
- Enforced directly by the database engine, eliminating race conditions from concurrent registrations.
- `RegisterSerializer` and `RegisterView` gracefully catch `IntegrityError` and return standard HTTP 400 validation errors instead of unhandled 500 server crashes.
- Consistent model-level `clean()` and `save()` normalization strips leading/trailing whitespace and lowercases email addresses.

### 3. Patient Management Module (`patients.Patient`)
- **Primary Key:** `UUID` (`uuid.uuid4`) to prevent ID enumeration across patient records.
- **Ownership & Isolation:** Each patient record is foreign-keyed to `settings.AUTH_USER_MODEL` via `created_by` (`on_delete=models.CASCADE`, `related_name='patients'`).
- **Data Isolation:** All queries filter strictly by `created_by=request.user` at the database level (`get_queryset()`). Attempts by another authenticated user to retrieve, update, or delete a patient return `404 Not Found`, completely preventing Insecure Direct Object Reference (IDOR) attacks.
- **Auditing:** `created_at` (`auto_now_add=True`) and `updated_at` (`auto_now=True`) track record lifecycles.

### 4. Doctor Management Module (`doctors.Doctor`)
- **Primary Key:** `UUID` (`uuid.uuid4`) to prevent ID enumeration across doctor records.
- **Directory Access & Scoping:** Doctor records are accessible as a shared directory across all authenticated users (`GET /api/doctors/` and `GET /api/doctors/<id>/`), allowing staff and patients to browse available practitioners.
- **Ownership & Modification Control:** Each doctor record tracks its creator (`created_by=request.user`, `on_delete=models.CASCADE`, `related_name='doctors'`). Updating or deleting a doctor is strictly restricted to the user who created the record via `IsDoctorOwnerOrReadOnly`. Unauthorized modifications return `403 Forbidden`.
- **Fields & Constraints:** Required legal name, professional email, phone number (validated regex & digit bounds), medical specialization, non-negative clinical experience years, qualifications, and practice address.
- **Auditing:** `created_at` (`auto_now_add=True`) and `updated_at` (`auto_now=True`) track creation and modification timestamps.

### 5. Patient-Doctor Mapping Module (`mappings.PatientDoctorMapping`)
- **Primary Key:** `UUID` (`uuid.uuid4`) for distinct, un-enumerable assignment identifiers.
- **Many-to-Many Architecture:** Explicit intermediary model joining `Patient` and `Doctor` entities without data duplication.
- **Database-Level Unique Constraint:** Composite constraint `UniqueConstraint(fields=['patient', 'doctor'], name='unique_patient_doctor_mapping')` prevents assigning the same doctor to the same patient multiple times.
- **Cascade Referential Integrity:** `on_delete=models.CASCADE` on both `patient` and `doctor` foreign keys automatically cleans up mappings when either referenced entity is deleted.
- **Strict Ownership & Access Control:** Serializer and views enforce that the authenticated user owns both the patient and doctor records (`patient.created_by == request.user and doctor.created_by == request.user`). Attempts to associate records owned by another user are rejected with validation errors.
- **IDOR Concealment:** Query-level isolation filters mappings by `patient__created_by=request.user`. Attempting to retrieve another user's patient mappings or delete another user's mapping returns `404 Not Found`.

### 6. JWT Flow & Token Lifetimes
- **Stateless Bearer Tokens:** Authenticated endpoints require `Authorization: Bearer <access_token>`.
- **Access Token Lifetime:** 30 minutes (mitigates replay and credential compromise risk).
- **Refresh Token Lifetime:** 1 day (enables seamless token renewal without frequent re-logins).
- **Default Security Posture:** Global `DEFAULT_PERMISSION_CLASSES = ['rest_framework.permissions.IsAuthenticated']`. Public endpoints (Registration and Login) explicitly opt-out using `permission_classes = [AllowAny]`.

---

## Environment Variables

Copy `.env.example` to `.env` and configure your credentials:

```bash
cp .env.example .env
```

| Variable | Description | Example / Default |
| :--- | :--- | :--- |
| `SECRET_KEY` | Cryptographic secret key | `django-insecure-...` (required in prod) |
| `DEBUG` | Enable/disable debug mode | `True` (dev) / `False` (prod) |
| `ALLOWED_HOSTS` | Comma-separated allowed hostnames | `localhost,127.0.0.1,testserver` |
| `DB_NAME` | PostgreSQL database name | `healthcare_db` |
| `DB_USER` | PostgreSQL role | `healthcare_admin` |
| `DB_PASSWORD` | PostgreSQL role password | `your_secure_password` |
| `DB_HOST` | Database host | `localhost` |
| `DB_PORT` | Database port | `5432` |
| `USE_SQLITE_TEST_DB` | Opt-in to in-memory SQLite testing | `False` (default: PostgreSQL test DB) |
| `TEST_DB_NAME` | Dedicated PostgreSQL test database | `healthcare_test_db` |

---

## API Endpoints

### Authentication APIs (`/api/auth/`)

| Method | Endpoint | Permissions | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/auth/register/` | Public (`AllowAny`) | Register a new user |
| `POST` | `/api/auth/login/` | Public (`AllowAny`) | Login and obtain JWT tokens |
| `POST` | `/api/auth/token/refresh/` | Public (`AllowAny`) | Obtain fresh access token |
| `GET` | `/api/auth/profile/` | Authenticated | Retrieve authenticated user profile |

#### Register User
- **URL:** `/api/auth/register/`
- **Method:** `POST`

**Request Payload:**
```json
{
  "name": "Prince Jha",
  "email": "prince@example.com",
  "password": "StrongPassword123"
}
```

**Success Response (`201 Created`):**
```json
{
  "message": "User registered successfully.",
  "user": {
    "id": "c1f7b920-7469-450a-bf1c-5d9e5b7b9148",
    "name": "Prince Jha",
    "email": "prince@example.com",
    "date_joined": "2026-11-02T09:00:00.000000Z"
  }
}
```

#### Login
- **URL:** `/api/auth/login/`
- **Method:** `POST`

**Request Payload:**
```json
{
  "email": "prince@example.com",
  "password": "StrongPassword123"
}
```

**Success Response (`200 OK`):**
```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "c1f7b920-7469-450a-bf1c-5d9e5b7b9148",
    "name": "Prince Jha",
    "email": "prince@example.com"
  }
}
```

---

### Patient Management APIs (`/api/patients/`)

All patient endpoints require a valid JWT bearer token in the `Authorization` header:
`Authorization: Bearer <access_token>`

| Method | Endpoint | Permissions | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/patients/` | Authenticated | Create a new patient (assigns `created_by=request.user`) |
| `GET` | `/api/patients/` | Authenticated | List all patients created by the authenticated user |
| `GET` | `/api/patients/<uuid:id>/` | Authenticated | Retrieve a specific patient record (owner only) |
| `PUT` | `/api/patients/<uuid:id>/` | Authenticated | Update all fields of a patient record (owner only) |
| `PATCH` | `/api/patients/<uuid:id>/` | Authenticated | Partially update a patient record (owner only) |
| `DELETE` | `/api/patients/<uuid:id>/` | Authenticated | Delete a patient record (owner only) |

#### 1. Create Patient
- **URL:** `/api/patients/`
- **Method:** `POST`
- **Headers:** `Authorization: Bearer <access_token>`

**Request Payload:**
```json
{
  "full_name": "Charlie Brown",
  "email": "charlie.brown@example.com",
  "phone_number": "+1-555-0377",
  "date_of_birth": "1995-10-10",
  "gender": "Male",
  "address": "789 Pine Rd, Smallville",
  "medical_history": "No known drug allergies. Mild seasonal asthma."
}
```

**Success Response (`201 Created`):**
```json
{
  "id": "e3b0c442-98fc-1c14-9afb-4c8996fb9242",
  "full_name": "Charlie Brown",
  "email": "charlie.brown@example.com",
  "phone_number": "+1-555-0377",
  "date_of_birth": "1995-10-10",
  "gender": "Male",
  "address": "789 Pine Rd, Smallville",
  "medical_history": "No known drug allergies. Mild seasonal asthma.",
  "created_by": "c1f7b920-7469-450a-bf1c-5d9e5b7b9148",
  "created_at": "2026-11-02T10:00:00.000000Z",
  "updated_at": "2026-11-02T10:00:00.000000Z"
}
```

**Validation Error Response (`400 Bad Request`):**
```json
{
  "phone_number": [
    "Enter a valid phone number (e.g. +1234567890 or 9876543210)."
  ],
  "date_of_birth": [
    "Date of birth cannot be in the future."
  ]
}
```

#### 2. IDOR & Ownership Protection
If a client attempts to retrieve, update, or delete a patient created by another user:
- **Response:** `404 Not Found` (`{"detail": "No Patient matches the given query."}`)
- **Security Guarantee:** The system does not return `403 Forbidden` (which would reveal that the record exists to unauthorized callers).

---

### Doctor Management APIs (`/api/doctors/`)

All doctor endpoints require a valid JWT bearer token in the `Authorization` header:
`Authorization: Bearer <access_token>`

| Method | Endpoint | Permissions | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/doctors/` | Authenticated | Create a new doctor (assigns `created_by=request.user`) |
| `GET` | `/api/doctors/` | Authenticated | List all doctors in the directory |
| `GET` | `/api/doctors/<uuid:id>/` | Authenticated | Retrieve doctor profile details |
| `PUT` | `/api/doctors/<uuid:id>/` | Authenticated Owner | Update all fields of a doctor profile (creator only) |
| `PATCH` | `/api/doctors/<uuid:id>/` | Authenticated Owner | Partially update a doctor profile (creator only) |
| `DELETE` | `/api/doctors/<uuid:id>/` | Authenticated Owner | Delete a doctor profile (creator only) |

#### 1. Create Doctor
- **URL:** `/api/doctors/`
- **Method:** `POST`
- **Headers:** `Authorization: Bearer <access_token>`

**Request Payload:**
```json
{
  "full_name": "Gregory House",
  "email": "dr.house@diagnostics.org",
  "phone_number": "+1-555-0101",
  "specialization": "Diagnostic Medicine",
  "experience_years": 20,
  "qualification": "MD, Board Certified",
  "address": "Princeton-Plainsboro Teaching Hospital"
}
```

**Success Response (`201 Created`):**
```json
{
  "id": "7f8b3c9e-28b9-4a41-b0e2-63b728b93402",
  "full_name": "Gregory House",
  "email": "dr.house@diagnostics.org",
  "phone_number": "+1-555-0101",
  "specialization": "Diagnostic Medicine",
  "experience_years": 20,
  "qualification": "MD, Board Certified",
  "address": "Princeton-Plainsboro Teaching Hospital",
  "created_by": "c1f7b920-7469-450a-bf1c-5d9e5b7b9148",
  "created_at": "2026-11-02T10:15:00.000000Z",
  "updated_at": "2026-11-02T10:15:00.000000Z"
}
```

**Validation Error Response (`400 Bad Request`):**
```json
{
  "experience_years": [
    "Years of experience cannot be negative."
  ],
  "phone_number": [
    "Enter a valid phone number (e.g. +1234567890 or 9876543210)."
  ],
  "email": [
    "Enter a valid email address."
  ]
}
```

#### 2. Directory Access & Modification Protection
- **Directory Access (`GET /api/doctors/` & `GET /api/doctors/<uuid:id>/`):** Accessible to all authenticated users to facilitate appointment booking and doctor discovery.
- **Modification Protection (`PUT`, `PATCH`, `DELETE`):** Restricted to the creator via `IsDoctorOwnerOrReadOnly`. Attempts by non-owners to update or delete a doctor return `403 Forbidden` (`{"detail": "You do not have permission to perform this action."}`). Non-existent doctor IDs return `404 Not Found`.

---

### Patient-Doctor Mapping APIs (`/api/mappings/`)

All mapping endpoints require a valid JWT bearer token in the `Authorization` header:
`Authorization: Bearer <access_token>`

| Method | Endpoint | Permissions | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/mappings/` | Authenticated | Assign a doctor to a patient |
| `GET` | `/api/mappings/` | Authenticated | List all mappings accessible to the authenticated user |
| `GET` | `/api/mappings/<patient_id>/` | Authenticated | Retrieve all doctors assigned to the specified patient |
| `DELETE` | `/api/mappings/<id>/` | Authenticated | Delete a specific mapping by mapping ID (owner only) |

#### 1. Assign Doctor to Patient
- **URL:** `/api/mappings/`
- **Method:** `POST`
- **Headers:** `Authorization: Bearer <access_token>`

**Request Payload:**
Supports both `{"patient": "<uuid>", "doctor": "<uuid>"}` and `{"patient_id": "<uuid>", "doctor_id": "<uuid>"}`:
```json
{
  "patient_id": "e3b0c442-98fc-1c14-9afb-4c8996fb9242",
  "doctor_id": "7f8b3c9e-28b9-4a41-b0e2-63b728b93402"
}
```

**Success Response (`201 Created`):**
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "patient": "e3b0c442-98fc-1c14-9afb-4c8996fb9242",
  "doctor": "7f8b3c9e-28b9-4a41-b0e2-63b728b93402",
  "patient_id": "e3b0c442-98fc-1c14-9afb-4c8996fb9242",
  "doctor_id": "7f8b3c9e-28b9-4a41-b0e2-63b728b93402",
  "patient_name": "Charlie Brown",
  "doctor_name": "Gregory House",
  "specialization": "Diagnostic Medicine",
  "assigned_at": "2026-11-02T10:30:00.000000Z"
}
```

**Duplicate Assignment Error (`400 Bad Request`):**
```json
{
  "non_field_errors": [
    "This doctor is already assigned to this patient."
  ]
}
```

**Unauthorized Cross-User Assignment Error (`400 Bad Request`):**
```json
{
  "patient": [
    "Patient does not exist or you do not have permission to access this record."
  ]
}
```

#### 2. Retrieve Doctors Assigned to Patient
- **URL:** `/api/mappings/<patient_id>/`
- **Method:** `GET`
- **Headers:** `Authorization: Bearer <access_token>`

**Success Response (`200 OK`):**
Returns a list containing complete doctor details and assignment metadata:
```json
[
  {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "mapping_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "assigned_at": "2026-11-02T10:30:00.000000Z",
    "doctor_id": "7f8b3c9e-28b9-4a41-b0e2-63b728b93402",
    "doctor_name": "Gregory House",
    "full_name": "Gregory House",
    "email": "dr.house@diagnostics.org",
    "phone_number": "+1-555-0101",
    "specialization": "Diagnostic Medicine",
    "experience_years": 20,
    "qualification": "MD, Board Certified",
    "address": "Princeton-Plainsboro Teaching Hospital",
    "doctor": {
      "id": "7f8b3c9e-28b9-4a41-b0e2-63b728b93402",
      "full_name": "Gregory House",
      "email": "dr.house@diagnostics.org",
      "phone_number": "+1-555-0101",
      "specialization": "Diagnostic Medicine",
      "experience_years": 20,
      "qualification": "MD, Board Certified",
      "address": "Princeton-Plainsboro Teaching Hospital"
    }
  }
]
```

#### 3. Delete Mapping
- **URL:** `/api/mappings/<id>/`
- **Method:** `DELETE`
- **Headers:** `Authorization: Bearer <access_token>`

**Success Response (`204 No Content`):**
Empty response body indicating successful deletion.

#### 4. IDOR & Ownership Protection
- Accessing or deleting mappings for patients/doctors created by another user returns `404 Not Found`.
- Clients cannot access or delete mappings outside their ownership scope.

---

## Automated Testing Strategy (PostgreSQL-First)

The project enforces a **PostgreSQL-first testing policy**:

### 1. Default: PostgreSQL Automated Testing
By default, running `python manage.py test` executes against an isolated PostgreSQL test database (`healthcare_test_db`). This guarantees that PostgreSQL-specific behaviors—such as functional unique indexes (`LOWER(email)`), transaction savepoints, and collation—are always tested in the actual database environment:

```powershell
python manage.py test
```

- **Database Used:** `healthcare_test_db`
- **User Credentials:** `healthcare_admin` (non-superuser with `CREATEDB`)
- **Lifecycle:** Automatically created before tests and destroyed upon completion.
- **Safety:** The development database (`healthcare_db`) and company `SIS` databases are strictly guarded and never touched.

### 2. Optional: Fast SQLite Unit Testing (Explicit Opt-In)
If fast, in-memory SQLite testing is desired during rapid local unit test iterations, you must explicitly opt in:

**PowerShell:**
```powershell
$env:USE_SQLITE_TEST_DB="True"; python manage.py test; Remove-Item Env:\USE_SQLITE_TEST_DB
```

**Bash / Linux:**
```bash
USE_SQLITE_TEST_DB=True python manage.py test
```

### 3. Test Database Isolation & Safety Guards
Six safety guards are hardcoded in `config/settings.py` to prevent accidental data corruption:
1. `TEST_DB_NAME` is strictly required.
2. The test database name must **never** equal the development database (`healthcare_db`).
3. The test database name must **never** be a protected database (`postgres`, `template1`, `sis`, `sis_db`).
4. The test database must strictly be `healthcare_test_db`.
5. Testing must use the dedicated `healthcare_admin` user (superuser `postgres` is blocked).
6. No silent fallback: if PostgreSQL testing cannot run safely, Django aborts with `ImproperlyConfigured` rather than silently degrading to SQLite.
