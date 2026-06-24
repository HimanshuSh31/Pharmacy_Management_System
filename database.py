"""
database.py — All database operations for the Pharmacy Management System.

Round-2 improvements:
  - All UPDATE/DELETE check rowcount and return False when 0 rows matched
  - Schema migration via _run_migrations(): adds D_Price, D_Image, O_Timestamp,
    and the new OrderItems join table to existing databases
  - order_place() is fully atomic: inserts header + items + decrements stock
    in a single transaction, rolling back entirely on any failure
  - Optional[X] type hints (Python 3.7+ compatible, not 3.10+ X | Y syntax)
  - PRAGMA foreign_keys = ON enforced on every connection
  - CHECK(D_Qty >= 0) prevents negative stock at the DB level
  - LOW_STOCK_THRESHOLD constant + drug_get_low_stock() for admin alerts
"""

import sqlite3
import logging
import threading
from typing import List, Optional, Tuple

# Streamlit is only available when the app is running under `streamlit run`.
# During pytest we import without it, and get_connection is fully patched
# by conftest.py anyway — so the @st.cache_resource decorator is never called.
try:
    import streamlit as st
    _cache = st.cache_resource
except ModuleNotFoundError:
    # Minimal no-op decorator for test environments
    def _cache(fn):           # type: ignore[misc]
        return fn
    st = None                 # type: ignore[assignment]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

LOW_STOCK_THRESHOLD: int = 10   # drugs at or below this qty trigger an alert


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

_local = threading.local()


def get_connection() -> sqlite3.Connection:
    """
    Return a thread-local SQLite connection.
    Foreign-key enforcement is enabled and WAL mode is set on every connection.
    """
    if not hasattr(_local, "conn") or _local.conn is None:
        conn = sqlite3.connect("drug_data.db", check_same_thread=False)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        _local.conn = conn
        logger.info("Thread-local database connection established in WAL mode.")
    return _local.conn


# ---------------------------------------------------------------------------
# Table creation + migration
# ---------------------------------------------------------------------------

def create_all_tables() -> None:
    """
    Create all base tables (IF NOT EXISTS) then run any pending migrations.
    Safe to call on every startup — existing data is never touched.
    """
    conn = get_connection()

    conn.execute('''
        CREATE TABLE IF NOT EXISTS Customers (
            C_Name     VARCHAR(50)  NOT NULL,
            C_Password VARCHAR(200) NOT NULL,
            C_Email    VARCHAR(50)  PRIMARY KEY NOT NULL,
            C_State    VARCHAR(50)  NOT NULL,
            C_Number   VARCHAR(50)  NOT NULL
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS Drugs (
            D_Name         VARCHAR(50)  NOT NULL,
            D_ExpDate      DATE         NOT NULL,
            D_Use          VARCHAR(200) NOT NULL,
            D_Qty          INT          NOT NULL CHECK(D_Qty >= 0),
            D_id           VARCHAR(50)  PRIMARY KEY NOT NULL,
            D_Price        REAL         NOT NULL DEFAULT 0.0,
            D_Image        TEXT         DEFAULT NULL,
            D_Category     TEXT         NOT NULL DEFAULT 'General',
            D_Supplier     TEXT         NOT NULL DEFAULT '',
            D_Prescription INTEGER      NOT NULL DEFAULT 0
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS Orders (
            O_id        VARCHAR(100) PRIMARY KEY NOT NULL,
            O_Name      VARCHAR(100) NOT NULL,
            O_Timestamp TEXT         NOT NULL DEFAULT (datetime(\'now\')),
            C_Email     VARCHAR(50)  NOT NULL REFERENCES Customers(C_Email)
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS OrderItems (
            OI_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            O_id       VARCHAR(100) NOT NULL,
            D_id       VARCHAR(50)  NOT NULL,
            D_name     VARCHAR(50)  NOT NULL,
            quantity   INT          NOT NULL CHECK(quantity > 0),
            unit_price REAL         NOT NULL DEFAULT 0.0,
            FOREIGN KEY (O_id) REFERENCES Orders(O_id) ON DELETE CASCADE,
            FOREIGN KEY (D_id) REFERENCES Drugs(D_id)
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS Contraindications (
            CI_id          INTEGER PRIMARY KEY AUTOINCREMENT,
            Category_A     VARCHAR(100) NOT NULL,
            Category_B     VARCHAR(100) NOT NULL,
            Severity       VARCHAR(20) NOT NULL DEFAULT 'High',
            Warning_Message TEXT NOT NULL
        )
    ''')

    conn.commit()
    _seed_contraindications(conn)
    _run_migrations(conn)
    logger.info("All tables created/verified.")


def _seed_contraindications(conn: sqlite3.Connection) -> None:
    """Seed the database with standard drug-drug category conflicts if empty."""
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM Contraindications")
    if c.fetchone()[0] == 0:
        seeds = [
            ("Antibiotic", "Supplement", "High",
             "Taking mineral supplements (such as Iron, Calcium, or Zinc) at the same time as antibiotics can prevent the body from absorbing the antibiotic. Take them at least 2 hours apart."),
            ("Antihistamine", "Pain Relief", "Medium",
             "Combining antihistamines with certain pain relievers may cause increased drowsiness, dizziness, or impaired motor coordination. Avoid driving or operating machinery."),
            ("Cardiovascular", "Pain Relief", "High",
             "NSAIDs (like Ibuprofen/Aspirin) can interact with blood pressure medications and increase cardiovascular risk. Please consult your physician before combining them.")
        ]
        c.executemany(
            "INSERT INTO Contraindications (Category_A, Category_B, Severity, Warning_Message) VALUES (?, ?, ?, ?)",
            seeds
        )
        conn.commit()
        logger.info("Seeded default drug category contraindications.")


def _run_migrations(conn: sqlite3.Connection) -> None:
    """
    Add columns that were introduced after the initial schema deployment.
    SQLite only supports ADD COLUMN, so old columns are never removed.
    """
    c = conn.cursor()

    # --- Drugs migrations ---
    c.execute("PRAGMA table_info(Drugs)")
    drug_cols = {row[1] for row in c.fetchall()}

    if "D_Price" not in drug_cols:
        conn.execute("ALTER TABLE Drugs ADD COLUMN D_Price REAL DEFAULT 0.0")
        logger.info("Migration: added D_Price to Drugs")

    if "D_Image" not in drug_cols:
        conn.execute("ALTER TABLE Drugs ADD COLUMN D_Image TEXT DEFAULT NULL")
        logger.info("Migration: added D_Image to Drugs")

    if "D_Category" not in drug_cols:
        conn.execute("ALTER TABLE Drugs ADD COLUMN D_Category TEXT DEFAULT 'General'")
        logger.info("Migration: added D_Category to Drugs")

    if "D_Supplier" not in drug_cols:
        conn.execute("ALTER TABLE Drugs ADD COLUMN D_Supplier TEXT DEFAULT ''")
        logger.info("Migration: added D_Supplier to Drugs")

    if "D_Prescription" not in drug_cols:
        conn.execute("ALTER TABLE Drugs ADD COLUMN D_Prescription INTEGER DEFAULT 0")
        logger.info("Migration: added D_Prescription to Drugs")

    # --- Orders migrations ---
    c.execute("PRAGMA table_info(Orders)")
    order_cols = {row[1] for row in c.fetchall()}

    if "O_Timestamp" not in order_cols:
        # SQLite ALTER TABLE does not allow non-constant expressions as DEFAULT.
        # Use a constant empty string; new rows always supply the value explicitly.
        conn.execute(
            "ALTER TABLE Orders ADD COLUMN O_Timestamp TEXT DEFAULT ''"
        )
        logger.info("Migration: added O_Timestamp to Orders")

    if "C_Email" not in order_cols:
        # SQLite ADD COLUMN supports foreign key references
        conn.execute(
            "ALTER TABLE Orders ADD COLUMN C_Email VARCHAR(50) DEFAULT NULL REFERENCES Customers(C_Email)"
        )
        # Attempt to backpopulate C_Email from Customers
        conn.execute("""
            UPDATE Orders
            SET C_Email = (
                SELECT C_Email FROM Customers WHERE Customers.C_Name = Orders.O_Name LIMIT 1
            )
            WHERE C_Email IS NULL
        """)
        # If O_Name already holds an email format, copy it
        conn.execute("""
            UPDATE Orders
            SET C_Email = O_Name
            WHERE C_Email IS NULL AND O_Name LIKE '%@%'
        """)
        logger.info("Migration: added C_Email to Orders and backpopulated values")

    if "O_Status" not in order_cols:
        conn.execute("ALTER TABLE Orders ADD COLUMN O_Status VARCHAR(30) DEFAULT 'Preparing'")
        logger.info("Migration: added O_Status to Orders")

    if "O_Prescription_Path" not in order_cols:
        conn.execute("ALTER TABLE Orders ADD COLUMN O_Prescription_Path TEXT DEFAULT NULL")
        logger.info("Migration: added O_Prescription_Path to Orders")

    if "O_Rejection_Reason" not in order_cols:
        conn.execute("ALTER TABLE Orders ADD COLUMN O_Rejection_Reason TEXT DEFAULT NULL")
        logger.info("Migration: added O_Rejection_Reason to Orders")

    conn.commit()


# ---------------------------------------------------------------------------
# Customer CRUD
# ---------------------------------------------------------------------------

def customer_add_data(name: str, password_hash: str, email: str,
                      state: str, number: str) -> bool:
    """Insert a new customer. Returns False if the email already exists."""
    conn = get_connection()
    try:
        conn.execute(
            'INSERT INTO Customers (C_Name, C_Password, C_Email, C_State, C_Number) '
            'VALUES (?, ?, ?, ?, ?)',
            (name, password_hash, email, state, number)
        )
        conn.commit()
        logger.info("Customer added: %s", email)
        return True
    except sqlite3.IntegrityError:
        conn.rollback()
        logger.warning("Duplicate email on signup: %s", email)
        return False
    except Exception as exc:
        conn.rollback()
        logger.error("customer_add_data failed: %s", exc)
        return False


def customer_view_all_data() -> List[Tuple]:
    """Return all customer rows — password column excluded."""
    c = get_connection().cursor()
    c.execute('SELECT C_Name, C_Email, C_State, C_Number FROM Customers')
    return c.fetchall()


def customer_get_password_hash(email: str) -> Optional[str]:
    """Return the stored password hash for *email*, or None if not found."""
    c = get_connection().cursor()
    c.execute('SELECT C_Password FROM Customers WHERE C_Email = ?', (email,))
    row = c.fetchone()
    return row[0] if row else None


def customer_get_by_email(email: str) -> Optional[Tuple]:
    """Return (name, email, state, number) for *email*, or None."""
    c = get_connection().cursor()
    c.execute(
        'SELECT C_Name, C_Email, C_State, C_Number FROM Customers WHERE C_Email = ?',
        (email,)
    )
    return c.fetchone()


def customer_update(email: str, number: str) -> bool:
    """Update phone number. Returns False when email not found (rowcount=0)."""
    conn = get_connection()
    try:
        cur = conn.execute(
            'UPDATE Customers SET C_Number = ? WHERE C_Email = ?', (number, email)
        )
        if cur.rowcount == 0:
            logger.warning("customer_update: no customer with email=%s", email)
            return False
        conn.commit()
        logger.info("Customer updated: %s", email)
        return True
    except Exception as exc:
        conn.rollback()
        logger.error("customer_update failed: %s", exc)
        return False


def customer_delete(email: str) -> Tuple[bool, str]:
    """Delete customer by email. Returns (success, message)."""
    conn = get_connection()
    try:
        cur = conn.execute('DELETE FROM Customers WHERE C_Email = ?', (email,))
        if cur.rowcount == 0:
            logger.warning("customer_delete: no customer with email=%s", email)
            return False, "Customer not found."
        conn.commit()
        logger.info("Customer deleted: %s", email)
        return True, "Customer deleted successfully."
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        logger.warning("customer_delete integrity violation: %s", exc)
        return False, "Cannot delete customer because they have active orders linked to their account."
    except Exception as exc:
        conn.rollback()
        logger.error("customer_delete failed: %s", exc)
        return False, f"Database error: {str(exc)}"


# ---------------------------------------------------------------------------
# Drug CRUD
# ---------------------------------------------------------------------------

def drug_add_data(name: str, expdate: str, use: str, qty: int, drug_id: str,
                  price: float = 0.0, image: Optional[str] = None,
                  category: str = "General", supplier: str = "",
                  prescription: int = 0) -> bool:
    """Insert a new drug. Returns False if the drug ID already exists."""
    conn = get_connection()
    try:
        conn.execute(
            'INSERT INTO Drugs '
            '(D_Name, D_ExpDate, D_Use, D_Qty, D_id, D_Price, D_Image,'
            ' D_Category, D_Supplier, D_Prescription) '
            'VALUES (?,?,?,?,?,?,?,?,?,?)',
            (name, expdate, use, qty, drug_id, price, image,
             category, supplier, prescription)
        )
        conn.commit()
        logger.info("Drug added: %s", drug_id)
        return True
    except sqlite3.IntegrityError:
        conn.rollback()
        logger.warning("Duplicate drug ID: %s", drug_id)
        return False
    except Exception as exc:
        conn.rollback()
        logger.error("drug_add_data failed: %s", exc)
        return False


def drug_view_all_data() -> List[Tuple]:
    """Return all drug rows: (Name, ExpDate, Use, Qty, id, Price, Image)."""
    c = get_connection().cursor()
    c.execute('SELECT * FROM Drugs')
    return c.fetchall()


def drug_get_low_stock(threshold: int = LOW_STOCK_THRESHOLD) -> List[Tuple]:
    """Return (D_Name, D_id, D_Qty) for drugs at or below *threshold*."""
    c = get_connection().cursor()
    c.execute(
        'SELECT D_Name, D_id, D_Qty FROM Drugs WHERE D_Qty <= ?', (threshold,)
    )
    return c.fetchall()


def drug_update(drug_id: str, use: str) -> bool:
    """Update usage description. Returns False when drug ID not found."""
    conn = get_connection()
    try:
        cur = conn.execute(
            'UPDATE Drugs SET D_Use = ? WHERE D_id = ?', (use, drug_id)
        )
        if cur.rowcount == 0:
            logger.warning("drug_update: no drug with id=%s", drug_id)
            return False
        conn.commit()
        logger.info("Drug updated: %s", drug_id)
        return True
    except Exception as exc:
        conn.rollback()
        logger.error("drug_update failed: %s", exc)
        return False


def drug_update_price(drug_id: str, price: float) -> bool:
    """Update drug price. Returns False when drug ID not found."""
    conn = get_connection()
    try:
        cur = conn.execute(
            'UPDATE Drugs SET D_Price = ? WHERE D_id = ?', (price, drug_id)
        )
        if cur.rowcount == 0:
            return False
        conn.commit()
        return True
    except Exception as exc:
        conn.rollback()
        logger.error("drug_update_price failed: %s", exc)
        return False


def drug_decrement_qty(drug_id: str, amount: int) -> bool:
    """
    Decrement D_Qty by *amount* atomically.
    Returns False if the drug is missing or has insufficient stock.
    The CHECK(D_Qty >= 0) constraint additionally prevents going negative.
    """
    conn = get_connection()
    try:
        cur = conn.execute(
            'UPDATE Drugs SET D_Qty = D_Qty - ? '
            'WHERE D_id = ? AND D_Qty >= ?',
            (amount, drug_id, amount)
        )
        if cur.rowcount == 0:
            logger.warning(
                "drug_decrement_qty: insufficient stock or missing id=%s", drug_id
            )
            return False
        conn.commit()
        return True
    except Exception as exc:
        conn.rollback()
        logger.error("drug_decrement_qty failed: %s", exc)
        return False


def drug_delete(drug_id: str) -> Tuple[bool, str]:
    """Delete drug by ID. Returns (success, message)."""
    conn = get_connection()
    try:
        cur = conn.execute('DELETE FROM Drugs WHERE D_id = ?', (drug_id,))
        if cur.rowcount == 0:
            logger.warning("drug_delete: no drug with id=%s", drug_id)
            return False, "Drug not found."
        conn.commit()
        logger.info("Drug deleted: %s", drug_id)
        return True, "Drug deleted successfully."
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        logger.warning("drug_delete integrity violation: %s", exc)
        return False, "Cannot delete drug because it is present in existing customer orders. Consider setting its stock to 0 instead."
    except Exception as exc:
        conn.rollback()
        logger.error("drug_delete failed: %s", exc)
        return False, f"Database error: {str(exc)}"


def drug_update_details(drug_id: str, use: str, price: float, add_qty: int,
                        expdate: str = "", category: str = "",
                        supplier: str = "", prescription: int = -1) -> bool:
    """
    Update drug details atomically.
    - add_qty is ADDED to existing stock (pass 0 to leave unchanged).
    - expdate/category/supplier/prescription are only updated when non-empty / != -1.
    Returns True on success, False if drug not found or error.
    """
    conn = get_connection()
    try:
        # Build dynamic SET clause for optional fields
        sets   = ["D_Use = ?", "D_Price = ?", "D_Qty = D_Qty + ?"]
        params: List = [use, price, add_qty]
        if expdate:
            sets.append("D_ExpDate = ?")
            params.append(expdate)
        if category:
            sets.append("D_Category = ?")
            params.append(category)
        if supplier != "":
            sets.append("D_Supplier = ?")
            params.append(supplier)
        if prescription != -1:
            sets.append("D_Prescription = ?")
            params.append(int(prescription))
        params.append(drug_id)

        cur = conn.execute(
            f'UPDATE Drugs SET {", ".join(sets)} WHERE D_id = ?',
            params
        )
        if cur.rowcount == 0:
            logger.warning("drug_update_details: no drug with id=%s", drug_id)
            return False
        conn.commit()
        logger.info("Drug updated: %s (added %d stock)", drug_id, add_qty)
        return True
    except Exception as exc:
        conn.rollback()
        logger.error("drug_update_details failed: %s", exc)
        return False


def drug_update_expiry(drug_id: str, new_expdate: str) -> bool:
    """Update expiry date for a drug. Returns False if not found."""
    conn = get_connection()
    try:
        cur = conn.execute(
            'UPDATE Drugs SET D_ExpDate = ? WHERE D_id = ?', (new_expdate, drug_id)
        )
        if cur.rowcount == 0:
            return False
        conn.commit()
        logger.info("Drug expiry updated: %s -> %s", drug_id, new_expdate)
        return True
    except Exception as exc:
        conn.rollback()
        logger.error("drug_update_expiry failed: %s", exc)
        return False


def drug_get_categories() -> List[str]:
    """Return sorted list of distinct drug categories."""
    c = get_connection().cursor()
    c.execute("SELECT DISTINCT D_Category FROM Drugs ORDER BY D_Category")
    return [row[0] for row in c.fetchall() if row[0]]


def drug_bulk_import(drugs: List[dict]) -> tuple:
    """
    Import multiple drugs from a list of dicts.
    Expected keys per dict: id, name, expdate, use, qty, price,
                            image, category, supplier, prescription
    Returns (success_count, fail_count).
    """
    success, fail = 0, 0
    for d in drugs:
        ok = drug_add_data(
            str(d.get("name", "")).strip(),
            str(d.get("expdate", "")).strip(),
            str(d.get("use", "")).strip(),
            int(d.get("qty", 0)),
            str(d.get("id", "")).strip(),
            float(d.get("price", 0.0)),
            d.get("image") or None,
            str(d.get("category", "General")).strip(),
            str(d.get("supplier", "")).strip(),
            int(d.get("prescription", 0)),
        )
        if ok:
            success += 1
        else:
            fail += 1
    return success, fail


def drug_view_paginated(limit: int = 20, offset: int = 0,
                        search: str = "",
                        category: str = "") -> tuple:
    """
    Return (rows, total_count) for paginated drug listing.
    Filters by search (name or ID) and category if provided.
    """
    c = get_connection().cursor()
    conditions: List[str] = []
    params: List = []

    if search:
        conditions.append("(D_Name LIKE ? OR D_id LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])
    if category and category.lower() not in ("", "all"):
        conditions.append("D_Category = ?")
        params.append(category)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    c.execute(f"SELECT COUNT(*) FROM Drugs {where}", params)
    total = c.fetchone()[0]

    c.execute(
        f"SELECT * FROM Drugs {where} ORDER BY D_Name LIMIT ? OFFSET ?",
        params + [limit, offset]
    )
    return c.fetchall(), total


# ---------------------------------------------------------------------------
# Order CRUD — normalised (OrderItems join table)
# ---------------------------------------------------------------------------

def order_place(customer_email: str, order_id: str,
                items: List[dict], prescription_path: Optional[str] = None) -> bool:
    """
    Place an order atomically in a single transaction:
      1. Retrieve customer name matching customer_email
      2. Check if any drug in the order requires a prescription
      3. Set initial order status based on prescription requirement
      4. INSERT order header into Orders (including C_Email, O_Name, O_Status, O_Prescription_Path)
      5. INSERT each item into OrderItems
      6. Decrement D_Qty for each drug (fails if stock is insufficient)

    If any step fails the entire transaction is rolled back — no partial data.

    items: list of dicts with keys:
        drug_id (str), drug_name (str), quantity (int), unit_price (float)

    Returns True on success, False on any failure.
    """
    conn = get_connection()
    try:
        c = conn.cursor()
        # Resolve customer name by email
        c.execute("SELECT C_Name FROM Customers WHERE C_Email = ?", (customer_email,))
        row = c.fetchone()
        if not row:
            raise ValueError(f"Customer email '{customer_email}' does not exist.")
        customer_name = row[0]

        # Check if any drug requires a prescription
        requires_rx = False
        for item in items:
            c.execute("SELECT D_Prescription FROM Drugs WHERE D_id = ?", (item["drug_id"],))
            drug_row = c.fetchone()
            if drug_row and drug_row[0]:
                requires_rx = True

        # Initial status: 'Pending Verification' if prescription is required, otherwise 'Preparing'
        initial_status = "Pending Verification" if requires_rx else "Preparing"

        conn.execute(
            "INSERT INTO Orders (O_id, O_Name, O_Timestamp, C_Email, O_Status, O_Prescription_Path) "
            "VALUES (?, ?, datetime('now'), ?, ?, ?)",
            (order_id, customer_name, customer_email, initial_status, prescription_path)
        )
        for item in items:
            conn.execute(
                'INSERT INTO OrderItems '
                '(O_id, D_id, D_name, quantity, unit_price) '
                'VALUES (?, ?, ?, ?, ?)',
                (order_id, item["drug_id"], item["drug_name"],
                 item["quantity"], item["unit_price"])
            )
            # Decrement only if sufficient stock exists
            cur = conn.execute(
                'UPDATE Drugs SET D_Qty = D_Qty - ? '
                'WHERE D_id = ? AND D_Qty >= ?',
                (item["quantity"], item["drug_id"], item["quantity"])
            )
            if cur.rowcount == 0:
                raise ValueError(
                    f"Insufficient stock for drug '{item['drug_id']}'"
                )
        conn.commit()
        logger.info("Order placed: %s by %s (%s) with status %s", order_id, customer_name, customer_email, initial_status)
        return True
    except Exception as exc:
        conn.rollback()
        logger.error("order_place rolled back (%s): %s", order_id, exc)
        return False


def order_view_data(customer_email: str) -> List[Tuple]:
    """
    Return order rows for a customer email, newest first.
    Columns: (O_id, O_Timestamp, D_name, quantity, unit_price, O_Status, O_Prescription_Path, O_Rejection_Reason)
    """
    c = get_connection().cursor()
    c.execute('''
        SELECT o.O_id, o.O_Timestamp, oi.D_name, oi.quantity, oi.unit_price,
               o.O_Status, o.O_Prescription_Path, o.O_Rejection_Reason
          FROM Orders  o
          JOIN OrderItems oi ON o.O_id = oi.O_id
         WHERE o.C_Email = ?
         ORDER BY o.O_Timestamp DESC
    ''', (customer_email,))
    return c.fetchall()


def order_view_all_data() -> List[Tuple]:
    """
    Return all orders with items, newest first.
    Columns: (O_id, O_Name, O_Timestamp, D_name, quantity, unit_price, O_Status, O_Prescription_Path, O_Rejection_Reason)
    """
    c = get_connection().cursor()
    c.execute('''
        SELECT o.O_id, o.O_Name, o.O_Timestamp,
               oi.D_name, oi.quantity, oi.unit_price,
               o.O_Status, o.O_Prescription_Path, o.O_Rejection_Reason
          FROM Orders  o
          JOIN OrderItems oi ON o.O_id = oi.O_id
         ORDER BY o.O_Timestamp DESC
    ''')
    return c.fetchall()


def order_update_status(order_id: str, status: str, rejection_reason: Optional[str] = None) -> bool:
    """
    Update the status and optional rejection reason of an order.
    Returns True on success, False if no order was found or update failed.
    """
    conn = get_connection()
    try:
        cur = conn.execute(
            "UPDATE Orders SET O_Status = ?, O_Rejection_Reason = ? WHERE O_id = ?",
            (status, rejection_reason, order_id)
        )
        if cur.rowcount == 0:
            logger.warning("order_update_status: no order with id=%s", order_id)
            return False
        conn.commit()
        logger.info("Order status updated: %s ➔ %s", order_id, status)
        return True
    except Exception as exc:
        conn.rollback()
        logger.error("order_update_status failed: %s", exc)
        return False


def contraindications_check(categories: List[str]) -> List[dict]:
    """
    Check a list of drug categories for any mutual contraindications.
    Returns a list of warning dicts: [{"severity": str, "message": str}]
    """
    if len(categories) < 2:
        return []
    c = get_connection().cursor()
    warnings = []
    for i in range(len(categories)):
        for j in range(i + 1, len(categories)):
            cat_a, cat_b = categories[i], categories[j]
            c.execute(
                "SELECT Severity, Warning_Message FROM Contraindications "
                "WHERE (Category_A = ? AND Category_B = ?) OR (Category_A = ? AND Category_B = ?)",
                (cat_a, cat_b, cat_b, cat_a)
            )
            rows = c.fetchall()
            for r in rows:
                warnings.append({
                    "severity": r[0],
                    "message": r[1]
                })
    return warnings


def order_delete(order_id: str) -> bool:
    """Delete an order and its items via CASCADE. Returns False when not found."""
    conn = get_connection()
    try:
        cur = conn.execute('DELETE FROM Orders WHERE O_id = ?', (order_id,))
        if cur.rowcount == 0:
            logger.warning("order_delete: no order with id=%s", order_id)
            return False
        conn.commit()
        logger.info("Order deleted: %s", order_id)
        return True
    except Exception as exc:
        conn.rollback()
        logger.error("order_delete failed: %s", exc)
        return False
