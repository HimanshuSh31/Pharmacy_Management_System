# 💊 Pharmacy Management System

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.x-red?logo=streamlit&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3-lightblue?logo=sqlite&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-62%20passed-brightgreen?logo=pytest&logoColor=white)
![License](https://img.shields.io/badge/License-Educational-orange)

A full-featured pharmacy management web application built with **Python** and **Streamlit**, backed by **SQLite**. Supports separate Admin and Customer portals with secure authentication, inventory management, and order tracking.

---

## ✨ Features

### 🔐 Authentication & Security
- PBKDF2-HMAC-SHA256 password hashing (260,000 iterations, unique 16-byte salt per password)
- Admin credentials loaded from environment variables — never hardcoded in source
- Email and phone number validation on sign-up

### 🛡️ Admin Portal
- **Drug Inventory** — Add, view, update, and delete drugs with price and image support
- **Low-Stock Alerts** — Banner warning when any drug falls at or below 10 units; low-stock rows highlighted red
- **Inventory Search** — Filter drugs by name or ID instantly
- **Customer Management** — View, update, and delete customer accounts
- **Order Management** — View all orders with line totals and per-customer summaries; delete orders

### 🛒 Customer Portal
- Browse available medicines with prices, expiry dates, and live stock levels
- Quantity sliders with real-time order total preview before confirming
- Atomic order placement — stock is decremented in the same transaction; full rollback on any failure
- Order history with per-order totals

### 🗄️ Database
- **Normalised schema** — `OrderItems` join table replaces fragile comma-string order storage
- **Atomic transactions** — every multi-step write rolls back completely on failure
- **Foreign key enforcement** — `PRAGMA foreign_keys = ON` on every connection
- **Check constraints** — `D_Qty >= 0` prevents negative stock at the DB level
- **Auto-migration** — `_run_migrations()` safely adds new columns to existing databases on startup with no data loss

---

## 🖥️ Tech Stack

| Layer | Technology |
|---|---|
| UI | [Streamlit](https://streamlit.io/) |
| Database | SQLite 3 (Python stdlib) |
| Data display | [Pandas](https://pandas.pydata.org/) |
| Image handling | [Pillow](https://python-pillow.org/) |
| Password hashing | `hashlib` PBKDF2-HMAC-SHA256 (Python stdlib) |
| Testing | [pytest](https://pytest.org/) |

---

## 📁 Project Structure

```
Pharmacy_Management_System/
│
├── main.py              # App entry point — routing & session state
├── database.py          # All SQLite CRUD operations & schema migrations
├── auth.py              # Password hashing, validation & authentication
├── admin_ui.py          # Admin dashboard UI
├── customer_ui.py       # Customer-facing UI
│
├── drug_data.db         # SQLite database (auto-created on first run)
├── drugdatabase.sql     # Schema reference (valid SQLite SQL + useful views)
│
├── images/              # Drug images (referenced by D_Image column)
│   ├── dolo650.jpg
│   ├── strepsils.jpg
│   └── vicks.jpg
│
├── tests/
│   ├── conftest.py      # pytest fixtures — isolated in-memory DB per test
│   ├── test_database.py # 37 CRUD & transaction tests
│   └── test_auth.py     # 25 auth, hashing & validation tests
│
├── requirements.txt
├── pytest.ini
├── .env.example         # Template for admin credential env vars
└── README.md
```

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/HimanshuSh31/Pharmacy_Management_System.git
cd Pharmacy_Management_System
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure admin credentials *(optional but recommended)*

Copy `.env.example` to `.env` and fill in your credentials:

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

```ini
PHARMACY_ADMIN_USER=your_admin_username
PHARMACY_ADMIN_PASS=your_secure_password
```

> If these are not set, the app falls back to `admin` / `admin` and logs a warning at startup.

### 5. Run the app

```bash
streamlit run main.py
```

Open **[http://localhost:8501](http://localhost:8501)** in your browser.

---

## 🧑‍💼 Default Credentials

| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `admin` |
| Customer | *(register via Sign Up)* | — |

> ⚠️ Change the admin password via environment variables before deploying.

---

## 🧪 Running Tests

```bash
# Windows
python -m pytest tests\ -v

# macOS / Linux
python -m pytest tests/ -v
```

The test suite runs **62 tests** against a fresh in-memory SQLite database — no running Streamlit server required.

```
62 passed in ~2.5s  ✅
```

### What's tested

| File | Tests | Coverage |
|---|---|---|
| `test_database.py` | 37 | All CRUD, atomic order placement, rollback on failure, CASCADE delete, low-stock query |
| `test_auth.py` | 25 | Password hashing uniqueness, correct/wrong/malformed verify, email & phone validators, customer auth |

---

## 🗄️ Database Schema

```sql
Customers  (C_Email PK, C_Name, C_Password, C_State, C_Number)
Drugs      (D_id PK, D_Name, D_ExpDate, D_Use, D_Qty >= 0, D_Price, D_Image)
Orders     (O_id PK, O_Name, O_Timestamp)
OrderItems (OI_id PK, O_id FK→Orders, D_id FK→Drugs,
            D_name, quantity > 0, unit_price)
```

- Deleting an `Orders` row cascades to all its `OrderItems`
- The full schema with SQL views is in [`drugdatabase.sql`](drugdatabase.sql)

---

## 📸 Drug Images

Place image files inside the `images/` folder. When adding a drug in the Admin portal, enter the filename (e.g. `aspirin.jpg`) in the **Image filename** field. That image will then be displayed in the customer medicine catalogue.

---

## 🔒 Security Notes

| Concern | Approach |
|---|---|
| Password storage | PBKDF2-HMAC-SHA256, unique random salt per password |
| Admin credentials | Environment variables (`PHARMACY_ADMIN_USER`, `PHARMACY_ADMIN_PASS`) |
| SQL injection | Parameterised queries throughout (`?` placeholders) |
| Negative stock | `CHECK(D_Qty >= 0)` DB constraint + app-level guard in `order_place()` |
| Partial orders | Full transaction rollback if any item in an order fails |

---

## 👤 Author

**Made by Himanshu Sharma**

---

## 📄 License

This project is for educational purposes.
