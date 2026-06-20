"""
main.py — Entry point for the Pharmacy Management System.

Round-2: create_all_tables() is guarded with st.session_state so it only
runs once per session, not on every Streamlit rerun.
"""

import logging

import streamlit as st

from database import create_all_tables, customer_add_data, customer_get_by_email
from auth import (
    authenticate_customer,
    authenticate_admin,
    hash_password,
    validate_email,
    validate_phone,
    validate_password_strength,
)
from admin_ui import show_admin_dashboard
from customer_ui import show_customer_dashboard

# ---------------------------------------------------------------------------
# Logging — replaces all bare print() calls
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Pharmacy Management System",
    page_icon="💊",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Session state helpers
# ---------------------------------------------------------------------------

def _init_session() -> None:
    """Initialise session state keys on first run."""
    defaults = {
        "logged_in": False,
        "user_type": None,      # "customer" | "admin"
        "username":  None,
        "email":     None,      # Unique key for database operations
        "tables_ok": False,     # guard so create_all_tables runs only once
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _logout() -> None:
    st.session_state.logged_in = False
    st.session_state.user_type = None
    st.session_state.username  = None
    st.session_state.email     = None


# ---------------------------------------------------------------------------
# Login form
# ---------------------------------------------------------------------------

def _show_login() -> None:
    st.sidebar.subheader("Customer Login")
    email    = st.sidebar.text_input("Email",    key="login_email")
    password = st.sidebar.text_input("Password", type="password", key="login_password")

    if st.sidebar.button("Login", key="btn_login"):
        if not email or not password:
            st.sidebar.warning("Please enter both email and password.")
            return
        if authenticate_customer(email.strip(), password):
            customer = customer_get_by_email(email.strip())
            st.session_state.logged_in = True
            st.session_state.user_type = "customer"
            st.session_state.username  = customer[0] if customer else email
            st.session_state.email     = email.strip()
            logger.info("Customer logged in: %s", email)
            st.rerun()
        else:
            st.sidebar.error("❌ Invalid email or password.")


# ---------------------------------------------------------------------------
# Sign-up form
# ---------------------------------------------------------------------------

def _show_signup() -> None:
    st.subheader("📝 Create a New Account")

    col1, col2 = st.columns(2)
    with col1:
        cust_name  = st.text_input("Full Name")
        cust_email = st.text_input("Email Address")
        cust_state = st.text_input("State")
    with col2:
        cust_number = st.text_input("Phone Number")
        cust_pass   = st.text_input("Password",         type="password", key="su_pass")
        cust_pass2  = st.text_input("Confirm Password", type="password", key="su_pass2")

    if st.button("Create Account", type="primary"):
        errors = []

        if not cust_name.strip():
            errors.append("Full name is required.")
        if not validate_email(cust_email):
            errors.append("Please enter a valid email address.")
        if not validate_phone(cust_number):
            errors.append("Please enter a valid phone number (7–15 digits).")
        
        is_strong, pw_errors = validate_password_strength(cust_pass)
        if not is_strong:
            errors.extend(pw_errors)
            
        if cust_pass != cust_pass2:
            errors.append("Passwords do not match.")

        if errors:
            for err in errors:
                st.warning(err)
            return

        hashed  = hash_password(cust_pass)
        success = customer_add_data(
            cust_name.strip(), hashed, cust_email.strip(),
            cust_state.strip(), cust_number.strip()
        )
        if success:
            st.success("✅ Account created! Head to **Login** to sign in.")
        else:
            st.error("❌ An account with that email address already exists.")


# ---------------------------------------------------------------------------
# Admin login
# ---------------------------------------------------------------------------

def _show_admin_login() -> None:
    st.sidebar.subheader("Admin Login")
    username = st.sidebar.text_input("Admin Username", key="admin_user")
    password = st.sidebar.text_input("Admin Password", type="password", key="admin_pass")

    if st.sidebar.button("Login as Admin", key="btn_admin_login"):
        if authenticate_admin(username, password):
            st.session_state.logged_in = True
            st.session_state.user_type = "admin"
            st.session_state.username  = username
            logger.info("Admin logged in.")
            st.rerun()
        else:
            st.sidebar.error("❌ Invalid admin credentials.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    _init_session()

    # Guard: run table creation only once per session, not on every rerun
    if not st.session_state.tables_ok:
        create_all_tables()
        st.session_state.tables_ok = True

    # ---- Logged-in state -------------------------------------------------------
    if st.session_state.logged_in:
        if st.sidebar.button("🚪 Logout"):
            _logout()
            st.rerun()

        if st.session_state.user_type == "admin":
            show_admin_dashboard()
        elif st.session_state.user_type == "customer":
            show_customer_dashboard(st.session_state.username, st.session_state.email)
        return

    # ---- Guest state -----------------------------------------------------------
    choice = st.sidebar.selectbox("Menu", ["Login", "Sign Up", "Admin"])

    if choice == "Login":
        _show_login()
    elif choice == "Sign Up":
        _show_signup()
    elif choice == "Admin":
        _show_admin_login()


if __name__ == "__main__":
    main()