# Tool Code Library

A Django-based internal web application for creating, managing, and approving standardized tool codes. Built to streamline the tool request process with role-based access, an approval workflow, master data configuration, and PDF export.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [User Roles and Permissions](#user-roles-and-permissions)
- [How Tool Codes Work](#how-tool-codes-work)
- [Author](#author)

---

## Features

- **Tool Code Generation** — Automatically generates unique, structured tool codes (max 40 characters) from field attributes, raw material, joint type, and supplier data
- **Role-Based Access Control** — Configurable roles with per-tab permission toggles managed from the UI
- **Approval Workflow** — Requests move through Draft → Pending → Approved / Rejected states
- **Draft Support** — Users can save incomplete requests and return to finish them later
- **Master Data Management** — Full CRUD for Suppliers, Raw Materials, Joint Types, Fields, and Field Attributes
- **PDF Export** — Download any tool request as a formatted PDF with a configurable footer
- **Audit Logging** — All actions (logins, approvals, errors) are logged to both the database and log files
- **Soft Delete** — Nothing is permanently deleted; records are deactivated to preserve data history

---

## Tech Stack

| Layer      | Technology                                        |
|------------|---------------------------------------------------|
| Backend    | Python 3.x, Django                                |
| Database   | SQLite3                                           |
| Frontend   | Django Templates, HTML, CSS, JavaScript           |
| PDF Export | ReportLab via custom `pdf_generator.py`           |
| Auth       | Django built-in auth extended with `UserProfile`  |
| Logging    | Python `logging` + Django ORM (`AuditLog` model)  |

---

## Project Structure

```
Tool-Code-Library/
├── README.md
└── tool/
    └── example/
        ├── accounts/
        │   ├── migrations/
        │   ├── management/
        │   ├── models.py          # All data models
        │   ├── views.py           # All view and business logic
        │   ├── urls.py            # App URL routes
        │   ├── admin.py
        │   ├── pdf_generator.py   # PDF export logic
        │   └── tests.py
        ├── example/
        │   ├── settings.py
        │   ├── urls.py
        │   ├── middleware.py      # Audit logging middleware
        │   ├── asgi.py
        │   └── wsgi.py
        ├── templates/
        │   ├── base.html
        │   ├── dashboard.html
        │   ├── tool_code.html
        │   ├── review_request.html
        │   ├── master_report.html
        │   ├── role_master.html
        │   ├── user_creation.html
        │   └── ...
        ├── static/
        ├── logs/
        │   ├── activity.log
        │   ├── audit.log
        │   └── error.log
        ├── db.sqlite3
        └── manage.py
```

---

## Getting Started

### Prerequisites

- Python 3.9+
- pip
- Git

### 1. Clone the repository

```bash
git clone https://github.com/AmeyPawar1414/Tool-Code-Library.git
cd Tool-Code-Library
```

### 2. Create and activate a virtual environment

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Windows (Git Bash):**
```bash
python -m venv venv
source venv/Scripts/activate
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run migrations

```bash
cd tool/example
python manage.py migrate
```

### 5. Create a superuser

```bash
python manage.py createsuperuser
```

After creating the superuser, go to `/admin/` and:
1. Create a **Role** with all permissions enabled (e.g. "Super Admin")
2. Create a **UserProfile** linking that role to your superuser

### 6. Start the development server

```bash
python manage.py runserver
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

---

## User Roles and Permissions

Roles are created and managed from the **Role Master** tab in the application. Each role has the following configurable permissions:

| Permission             | What it controls                          |
|------------------------|-------------------------------------------|
| `can_access_tool_code` | View the Tool Code tab                    |
| `can_create_requests`  | Create and edit tool requests             |
| `can_approve_requests` | Approve or reject pending requests        |
| `can_access_master`    | Access all Master Data tabs               |
| `can_access_reports`   | View the Master Report                    |
| `can_manage_users`     | Create new user accounts                  |
| `can_manage_roles`     | Create and manage roles                   |

The **Super Admin** role is protected and cannot be deactivated.

---

## How Tool Codes Work

Tool codes are built automatically from the request data using this format:

```
SHORT_CODE - FIXED_VALUE - ATTR1 X ATTR2 - ATTR3 - JOINT[0] - MATERIAL[0:2]
```

Rules:
- Text attribute values are truncated to 2 uppercase characters
- Number attribute values are kept as-is (e.g. `14`, `1.5`, `1/2`)
- Total length is capped at **40 characters**
- If a generated code already exists, a counter suffix is appended (`-01`, `-02`, etc.)

Workflow states:

```
[Draft] → [Pending] → [Approved]
                    ↘ [Rejected] → (user edits and resubmits) → [Pending]
```

---

## Pushing Updates to GitHub

```bash
git add .
git commit -m "Your message here"
git push
```

---

## Author

**Amey Pawar**  
GitHub: [@AmeyPawar1414](https://github.com/AmeyPawar1414)
