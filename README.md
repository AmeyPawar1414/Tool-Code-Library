# 🔧 Tool Code Library

A web-based Django application for managing and generating standardized tool codes in a manufacturing or procurement environment. It supports role-based access, multi-stage approval workflows, master data management, audit logging, and PDF export.

\---

## 📋 Table of Contents

* [Features](#features)
* [Tech Stack](#tech-stack)
* [Project Structure](#project-structure)
* [Getting Started](#getting-started)
* [Environment Setup](#environment-setup)
* [Running the Project](#running-the-project)
* [User Roles \& Permissions](#user-roles--permissions)
* [Key Modules](#key-modules)
* [Pushing to GitHub](#pushing-to-github)

\---

## ✨ Features

* **Dynamic Tool Code Generation** — Auto-generates unique tool codes (up to 40 characters) based on field attributes, material, joint type, and supplier data
* **Role-Based Access Control (RBAC)** — Fully configurable roles with granular tab-level permissions
* **Approval Workflow** — Submit → Pending → Approved / Rejected flow with rejection reasons
* **Draft Support** — Save incomplete tool requests as drafts and submit later
* **Master Data Management** — Manage Suppliers, Raw Materials, Joint Types, Fields, and Field Attributes
* **PDF Export** — Download tool request details as a formatted PDF with configurable footer
* **Audit Logging** — Tracks all user actions (logins, approvals, errors) in both the database and log files
* **Soft Delete** — Records are deactivated rather than permanently deleted to preserve data integrity
* **Responsive UI** — Built with Django templates and a clean base layout

\---

## 🛠 Tech Stack

|Layer|Technology|
|-|-|
|Backend|Python 3.x, Django|
|Database|SQLite3 (development)|
|Frontend|Django Templates, HTML/CSS/JS|
|PDF Export|Custom PDF generator (`pdf\_generator.py`)|
|Auth|Django built-in auth + custom UserProfile|
|Logging|Python `logging` module + Django DB (`AuditLog`)|

\---

## 📁 Project Structure

```
tool/example/
├── accounts/                  # Main Django app
│   ├── migrations/            # Database migrations
│   ├── management/            # Custom management commands
│   ├── models.py              # All data models
│   ├── views.py               # All view logic
│   ├── urls.py                # App-level URL routing
│   ├── admin.py               # Django admin configuration
│   ├── pdf\_generator.py       # PDF export logic
│   └── tests.py
├── example/                   # Django project config
│   ├── settings.py
│   ├── urls.py
│   ├── middleware.py          # Custom middleware (audit logging)
│   ├── asgi.py
│   └── wsgi.py
├── templates/                 # HTML templates
│   ├── base.html
│   ├── dashboard.html
│   ├── tool\_code.html
│   ├── review\_request.html
│   ├── master\_report.html
│   ├── role\_master.html
│   ├── user\_creation.html
│   └── ...
├── static/                    # Static assets (CSS, JS, images)
├── logs/                      # Log files
│   ├── activity.log
│   ├── audit.log
│   └── error.log
├── db.sqlite3
└── manage.py
```

\---

## ⚙️ Getting Started

### Prerequisites

* Python 3.9 or higher
* pip
* Git

### 1\. Clone the Repository

```bash
git clone https://github.com/your-username/tool-code-library.git
cd tool-code-library
```

### 2\. Create and Activate a Virtual Environment

**Windows (PowerShell):**

```powershell
python -m venv venv
.\\venv\\Scripts\\Activate.ps1
```

**macOS / Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
```

\---

## 🔧 Environment Setup

### 3\. Install Dependencies

```bash
pip install -r requirements.txt
```

> If `requirements.txt` doesn't exist yet, generate it with:
> ```bash
> pip freeze > requirements.txt
> ```

### 4\. Apply Migrations

```bash
cd example
python manage.py migrate
```

### 5\. Create a Superuser

```bash
python manage.py createsuperuser
```

Follow the prompts to set a username, email, and password. This account will have full access.

> \*\*Important:\*\* After creating the superuser, log in to the Django Admin (`/admin/`) and:
> 1. Create a \*\*Role\*\* (e.g., "Super Admin") with all permissions enabled
> 2. Assign it to the superuser via \*\*UserProfile\*\*

\---

## 🚀 Running the Project

```bash
python manage.py runserver
```

Visit: [http://127.0.0.1:8000](http://127.0.0.1:8000)

\---

## 👥 User Roles \& Permissions

Roles are fully configurable from the **Role Master** tab. Each role has the following toggleable permissions:

|Permission|Description|
|-|-|
|`can\_access\_tool\_code`|View the Tool Code tab|
|`can\_create\_requests`|Create and edit tool requests|
|`can\_approve\_requests`|Approve or reject pending requests|
|`can\_access\_master`|Access all Master Data tabs|
|`can\_access\_reports`|View the Master Report|
|`can\_manage\_users`|Create new user accounts|
|`can\_manage\_roles`|Create and manage roles|

> The \*\*Super Admin\*\* role is protected and cannot be deactivated.

\---

## 📦 Key Modules

### Tool Code Generation

Tool codes are auto-generated using a dynamic algorithm that combines:

* Field short code
* Fixed value
* Attribute values (text truncated to 2 chars, numbers kept full)
* Joint type (first letter)
* Raw material (first 2 letters)

Codes are guaranteed unique (appends `-01`, `-02`, etc. if needed) and capped at **40 characters**.

### Approval Workflow

```
\[Draft] → \[Pending] → \[Approved]
                    ↘ \[Rejected] → (user edits) → \[Pending]
```

### Audit Logging

Every significant action is logged to:

* **Database** (`AuditLog` model) — queryable from Django Admin
* **Log files** — `activity.log`, `audit.log`, `error.log` under `/logs/`

### Soft Delete

All master data (Fields, Suppliers, Materials, Roles, etc.) supports soft delete — records are marked `is\_deleted=True` rather than removed, preserving referential integrity.

\---

## 🚢 Pushing to GitHub

### First-Time Setup

#### 1\. Create a `.gitignore` file

Create a file named `.gitignore` in the root of your project with the following content:

```
# Python
\_\_pycache\_\_/
\*.py\[cod]
\*.pyo
\*.pyd
.Python

# Virtual environment
venv/
env/
ENV/

# Django
\*.log
\*.pot
\*.pyc
db.sqlite3
media/

# Environment variables
.env
\*.env

# VS Code
.vscode/

# OS
.DS\_Store
Thumbs.db
```

#### 2\. Initialize Git and Push

```bash
# Navigate to your project root (where manage.py is NOT — one level up)
cd "C:\\Users\\namey\\OneDrive\\Desktop\\Tool Code Library\\tool"

# Initialize git
git init

# Stage all files
git add .

# First commit
git commit -m "Initial commit: Tool Code Library Django project"

# Connect to your GitHub repository
git remote add origin https://github.com/your-username/your-repo-name.git

# Push to GitHub
git branch -M main
git push -u origin main
```

#### 3\. Create the GitHub Repository First

Before pushing:

1. Go to [https://github.com/new](https://github.com/new)
2. Name your repo (e.g., `tool-code-library`)
3. Keep it **empty** (no README, no .gitignore — you're adding your own)
4. Copy the remote URL and use it in the `git remote add origin` command above

\---

### Subsequent Pushes

```bash
git add .
git commit -m "Your commit message here"
git push
```

\---

## 📄 License

This project is for internal use. Add a license here if you plan to make it public.

\---

## 🙋 Author

Built and maintained by **Amey Pawar**.  
For questions or issues, open a GitHub Issue or reach out directly.

