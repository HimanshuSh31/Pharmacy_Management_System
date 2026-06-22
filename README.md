# 💊 Pharmacy Management System

<div align="center">

[![Live Demo](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://pharmacymanagementsystem.streamlit.app/)
&nbsp;
[![CI](https://github.com/HimanshuSh31/Pharmacy_Management_System/actions/workflows/ci.yml/badge.svg)](https://github.com/HimanshuSh31/Pharmacy_Management_System/actions)
&nbsp;
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
&nbsp;
![Streamlit](https://img.shields.io/badge/Streamlit-1.x-FF4B4B?logo=streamlit&logoColor=white)
&nbsp;
![SQLite](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite&logoColor=white)
&nbsp;
![Tests](https://img.shields.io/badge/Tests-73%20passed-22C55E?logo=pytest&logoColor=white)
&nbsp;
![License](https://img.shields.io/badge/License-Educational-F59E0B)

<br/>

A **full-featured, enterprise-grade** pharmacy management web application built with Python and Streamlit, backed by SQLite. Features separate Admin and Customer portals with secure authentication, real-time inventory tracking, order management, and bulk operations.

[**▶ Open Live Demo**](https://pharmacymanagementsystem.streamlit.app/) · [Report Bug](https://github.com/HimanshuSh31/Pharmacy_Management_System/issues) · [Request Feature](https://github.com/HimanshuSh31/Pharmacy_Management_System/issues)

</div>

---

## 🚀 Live Demo

> **[https://pharmacymanagementsystem.streamlit.app](https://pharmacymanagementsystem.streamlit.app/)**

The demo is pre-loaded with **10 realistic drugs** across 6 categories, including deliberately low-stock items and a ready-made customer account so you can explore every feature immediately.

| Role | Login | Password | What you can do |
|---|---|---|---|
| 🛡️ **Admin** | `admin` | `Demo@2024` | Manage inventory, bulk import, view all orders & revenue |
| 🛒 **Customer** | `demo@pharma.com` | `Demo@2024` | Browse catalog, place orders, view history |

> ℹ️ The demo database resets on each redeployment. All changes are for demonstration only.

---

## ✨ Feature Overview

### 🛡️ Admin Portal

| Feature | Details |
|---|---|
| **Dashboard Metrics** | 5 live cards — Total Drugs, Low Stock, Customers, Orders, Revenue (₹) |
| **Drug Inventory** | Add / View / Update / Delete with image upload, category, supplier, Rx flag |
| **Expiry Highlighting** | 🔴 Expired · 🟠 Expiring ≤30 days · 🟡 Low stock (≤10 units) |
| **Paginated View** | 20 drugs per page with search + category filter dropdown |
| **Add Stock** | Increment stock on update (adds to existing, doesn't replace) |
| **Update Expiry** | Fix expiry date typos via the Update form |
| **Bulk CSV Import** | Upload a CSV to import hundreds of drugs at once + template download |
| **Low-Stock Email Alert** | One-click email to admin (requires SMTP config in `.env`) |
| **Customer Management** | View, search, update phone, delete customer accounts |
| **Order Management** | Full order history, revenue by customer, CSV export on all tables |
| **Cache Layer** | `@st.cache_data` (30–120 s TTL) with write-through invalidation |

### 🛒 Customer Portal

| Feature | Details |
|---|---|
| **Medicine Card Grid** | 3-column responsive grid with drug image, price, stock, expiry |
| **Category Badges** | Blue category pill + amber **Rx Prescription** badge |
| **Search & Filter** | Search by name/use · filter by category dropdown |
| **Expired Drugs** | Shown as blocked red cards — cannot be added to cart |
| **Expiring Soon** | ⏰ Warning badge on cards expiring within 30 days |
| **Out of Stock** | Clearly marked, slider disabled |
| **Live Subtotals** | Real-time `qty × price` shown below each slider |
| **Order Confirmation** | Review full summary + grand total before confirming |
| **Order History** | Per-order totals table + CSV download |
| **Profile Sidebar** | View name/email/state/phone, update phone number |

### 🔐 Security

| Feature | Details |
|---|---|
| **Password Hashing** | PBKDF2-HMAC-SHA256 · 260,000 iterations · unique 16-byte salt per password |
| **Admin Credentials** | Via `.env` / Streamlit Cloud secrets — never hardcoded |
| **Rate Limiting** | 5-attempt lockout with 5-minute cooldown |
| **Session Timeout** | Auto-logout after 60 minutes of inactivity |
| **Password Strength** | Min 6 chars · 1 uppercase · 1 lowercase · 1 digit — enforced on sign-up |
| **SQL Injection** | Parameterised `?` queries throughout — no string interpolation |
| **Negative Stock** | `CHECK(D_Qty >= 0)` DB constraint + app-level guard in `order_place()` |

---

## 🖥️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend / UI | [Streamlit](https://streamlit.io/) |
| Database | SQLite 3 (Python stdlib) — WAL mode, FK enforcement |
| Data Tables | [Pandas](https://pandas.pydata.org/) |
| Image Handling | [Pillow](https://python-pillow.org/) |
| Password Hashing | `hashlib` PBKDF2-HMAC-SHA256 (Python stdlib) |
| Email Alerts | `smtplib` STARTTLS (Python stdlib) |
| Caching | `@st.cache_data` (Streamlit) |
| Env Config | `python-dotenv` |
| Testing | [pytest](https://pytest.org/) 73 tests |
| CI/CD | GitHub Actions |
| Containerisation | Docker + Docker Compose |
| Cloud Deploy | Streamlit Community Cloud |

---

## 📁 Project Structure

```
Pharmacy_Management_System/
│
├── main.py              # Entry point — routing, session state, auth screens
├── database.py          # All SQLite CRUD, schema, auto-migrations, bulk import
├── auth.py              # PBKDF2 hashing, input validators, admin auth
├── admin_ui.py          # Admin dashboard (metrics, CRUD, import, email alerts)
├── customer_ui.py       # Customer portal (card grid, search, order flow)
├── data.py              # @st.cache_data read layer + invalidators
├── notifier.py          # SMTP low-stock email notifications
├── demo_data.py         # Seeds 10 demo drugs + 1 customer on first run
├── styles.py            # Master CSS injection + HTML component helpers
│
├── drug_data.db         # SQLite database (auto-created on first run)
├── drugdatabase.sql     # Schema reference
├── images/              # Drug images uploaded via admin UI
│
├── tests/
│   ├── conftest.py      # pytest fixtures — isolated in-memory DB per test
│   ├── test_database.py # 40 tests — CRUD, atomic orders, rollback, CASCADE
│   └── test_auth.py     # 33 tests — hashing, validators, rate limiting
│
├── .streamlit/
│   ├── config.toml           # Premium medical-blue color theme
│   └── secrets.toml.example  # Secrets template for Streamlit Cloud
│
├── .github/
│   └── workflows/ci.yml      # Run pytest on every push / PR to main
│
├── Dockerfile               # Slim Python 3.11, non-root user, health check
├── docker-compose.yml       # One-command deploy with persistent volumes
├── requirements.txt
├── pytest.ini
└── .env.example             # All supported environment variables
```

---

## 🚀 Getting Started

### ☁️ Option 1 — Streamlit Community Cloud *(Recommended · Free · 60 seconds)*

1. **Fork** this repository
2. Go to **[share.streamlit.io](https://share.streamlit.io)** → sign in with GitHub
3. Click **New app** → select your fork → main file: `main.py`
4. Click **Advanced settings → Secrets** and paste:
   ```toml
   PHARMACY_ADMIN_USER = "admin"
   PHARMACY_ADMIN_PASS = "YourSecurePassword"
   ```
5. Click **Deploy** ✅

### 🐳 Option 2 — Docker *(One command)*

```bash
git clone https://github.com/HimanshuSh31/Pharmacy_Management_System.git
cd Pharmacy_Management_System
cp .env.example .env        # Set your credentials
docker compose up --build
```
Open **http://localhost:8501**

### 🐍 Option 3 — Local Python

```bash
git clone https://github.com/HimanshuSh31/Pharmacy_Management_System.git
cd Pharmacy_Management_System

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

pip install -r requirements.txt
cp .env.example .env          # Set your credentials
streamlit run main.py
```

---

## 🧪 Tests

```bash
python -m pytest tests/ -v
```

**73 tests · ~2.5 s · in-memory SQLite · no server required**

| Test File | Count | What's Covered |
|---|---|---|
| `test_database.py` | 40 | CRUD, atomic orders, rollback, CASCADE delete, low-stock, bulk import, constraint violations |
| `test_auth.py` | 33 | PBKDF2 hashing, strength validation, email/phone regex, rate limiting, admin auth |

CI runs automatically on every push and PR via [GitHub Actions](https://github.com/HimanshuSh31/Pharmacy_Management_System/actions).

---

## 🗄️ Database Schema

```sql
Customers  (C_Email PK · C_Name · C_Password · C_State · C_Number)

Drugs      (D_id PK · D_Name · D_ExpDate · D_Use
            D_Qty CHECK(>=0) · D_Price · D_Image
            D_Category · D_Supplier · D_Prescription)

Orders     (O_id PK · O_Name · O_Timestamp
            C_Email FK → Customers)

OrderItems (OI_id PK AUTOINCREMENT
            O_id FK → Orders ON DELETE CASCADE
            D_id FK → Drugs
            D_name · quantity CHECK(>0) · unit_price)
```

---

## 📧 Low-Stock Email Alerts

Add these to `.env` or Streamlit Cloud secrets to enable the **📧 Email Alert** button in the admin dashboard:

```ini
SMTP_HOST   = smtp.gmail.com
SMTP_PORT   = 587
SMTP_USER   = you@gmail.com
SMTP_PASS   = xxxx-xxxx-xxxx-xxxx   # 16-char Gmail App Password
ALERT_EMAIL = admin@yourpharmacy.com
```

> For Gmail: create an App Password at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)

---

## 🐋 Docker Quick Reference

```bash
# Build and start
docker compose up --build -d

# View logs
docker compose logs -f

# Stop
docker compose down

# Rebuild after code change
docker compose up --build
```

The `docker-compose.yml` mounts `./drug_data.db` and `./images/` as volumes so your data persists across container restarts.

---

## 👤 Author

**Made by Himanshu Sharma**

[![GitHub](https://img.shields.io/badge/GitHub-HimanshuSh31-181717?logo=github)](https://github.com/HimanshuSh31)

---

## 📄 License

This project is for educational purposes.
