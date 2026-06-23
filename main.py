"""
main.py — Entry point: routing, session state, authentication screens.

Round-3 improvements:
  - python-dotenv auto-loading (.env file)
  - validate_password_strength() called on signup
  - Login rate limiting: lock after 5 failed attempts for 5 minutes
  - Session timeout: auto-logout after 60 minutes of inactivity
  - Customer profile sidebar section
  - Streamlit Cloud secrets fallback (st.secrets → env vars)
  - Demo data seeding on first startup
"""

import logging
import time
import os
from datetime import datetime, timedelta

# Auto-load .env before any other imports read env vars
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass   # python-dotenv not installed — env vars must be set in shell

import streamlit as st

# Inject Streamlit Cloud secrets into os.environ so auth.py picks them up
# (Streamlit Cloud exposes secrets via st.secrets; locally we use .env)
try:
    for _key in ("PHARMACY_ADMIN_USER", "PHARMACY_ADMIN_PASS",
                 "SMTP_HOST", "SMTP_PORT", "SMTP_USER",
                 "SMTP_PASS", "ALERT_EMAIL", "LOG_LEVEL"):
        if _key in st.secrets and _key not in os.environ:
            os.environ[_key] = str(st.secrets[_key])
except Exception:
    pass   # st.secrets not available (local dev without secrets.toml)

from database import create_all_tables, customer_get_by_email, customer_update
from auth import (
    authenticate_customer, authenticate_admin,
    hash_password, validate_email, validate_phone,
    validate_password_strength,
)
from database import customer_add_data
from demo_data import seed_demo_data
from admin_ui import show_admin_dashboard
from customer_ui import show_customer_dashboard
from styles import inject_css, sidebar_logo

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_LOGIN_ATTEMPTS  = 5
LOCKOUT_MINUTES     = 5
SESSION_TIMEOUT_MIN = 60      # auto-logout after 60 minutes idle

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="PharmaSystem",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

def _init_session() -> None:
    defaults = {
        "logged_in":      False,
        "user_type":      None,      # "customer" | "admin"
        "username":       None,
        "email":          None,
        "tables_ok":      False,
        "last_active":    None,      # timestamp of last activity
        # Rate limiting: {email: {"count": int, "locked_until": float}}
        "login_attempts": {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _logout() -> None:
    for k in ("logged_in", "user_type", "username", "email", "last_active"):
        st.session_state[k] = None
    st.session_state.logged_in = False


def _touch_activity() -> None:
    """Update last-active timestamp on every render."""
    st.session_state.last_active = time.time()


def _check_session_timeout() -> bool:
    """Return True and log out if the session has been idle too long."""
    last = st.session_state.get("last_active")
    if last and (time.time() - last) > SESSION_TIMEOUT_MIN * 60:
        _logout()
        st.warning(f"⏱️ Session expired after {SESSION_TIMEOUT_MIN} minutes of inactivity. Please log in again.")
        return True
    return False


# ---------------------------------------------------------------------------
# Rate limiting helpers
# ---------------------------------------------------------------------------

def _is_locked(email: str) -> tuple:
    """Return (is_locked, seconds_remaining)."""
    record = st.session_state.login_attempts.get(email)
    if not record:
        return False, 0
    locked_until = record.get("locked_until", 0)
    if locked_until and time.time() < locked_until:
        remaining = int(locked_until - time.time())
        return True, remaining
    return False, 0


def _record_failed_attempt(email: str) -> int:
    """Record a failed attempt. Returns current attempt count."""
    attempts = st.session_state.login_attempts
    if email not in attempts:
        attempts[email] = {"count": 0, "locked_until": 0}
    attempts[email]["count"] += 1
    count = attempts[email]["count"]
    if count >= MAX_LOGIN_ATTEMPTS:
        attempts[email]["locked_until"] = time.time() + LOCKOUT_MINUTES * 60
    return count


def _clear_attempts(email: str) -> None:
    st.session_state.login_attempts.pop(email, None)


# ---------------------------------------------------------------------------
# Auth screens
# ---------------------------------------------------------------------------

def _auth_page() -> None:
    inject_css()

    _, mid, _ = st.columns([1, 1.6, 1])
    with mid:
        st.markdown("""
        <div style="text-align:center; padding:2rem 0 1.5rem;">
            <div style="font-size:3.5rem; margin-bottom:0.5rem;">💊</div>
            <h1 style="font-size:1.85rem; font-weight:800; color:var(--text-color);
                       margin:0; letter-spacing:-0.02em;">PharmaSystem</h1>
            <p style="font-size:0.875rem; color:var(--text-color); opacity:0.7; margin:0.3rem 0 0;">
                Your trusted pharmacy management platform
            </p>
        </div>
        """, unsafe_allow_html=True)

        tab_login, tab_signup, tab_admin = st.tabs(
            ["🔑  Customer Login", "📝  Sign Up", "🛡️  Admin"]
        )

        # ── Customer Login ───────────────────────────────────────────────
        with tab_login:
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            with st.form("form_login"):
                st.markdown("### Welcome back")
                email    = st.text_input("Email address", placeholder="you@example.com")
                password = st.text_input("Password", type="password", placeholder="••••••••")
                submit   = st.form_submit_button("Login →", use_container_width=True)

            if submit:
                email = email.strip()
                locked, remaining = _is_locked(email)
                if locked:
                    mins, secs = divmod(remaining, 60)
                    st.error(f"🔒 Too many failed attempts. Try again in {mins}m {secs}s.")
                elif not email or not password:
                    st.warning("Please enter your email and password.")
                elif authenticate_customer(email, password):
                    _clear_attempts(email)
                    customer = customer_get_by_email(email)
                    st.session_state.logged_in   = True
                    st.session_state.user_type   = "customer"
                    st.session_state.username    = customer[0] if customer else email
                    st.session_state.email       = email
                    st.session_state.last_active = time.time()
                    logger.info("Customer login: %s", email)
                    st.rerun()
                else:
                    count = _record_failed_attempt(email)
                    remaining_attempts = MAX_LOGIN_ATTEMPTS - count
                    if remaining_attempts > 0:
                        st.error(f"❌ Invalid email or password. {remaining_attempts} attempt(s) remaining.")
                    else:
                        st.error(f"🔒 Account locked for {LOCKOUT_MINUTES} minutes after too many failed attempts.")

        # ── Sign Up ──────────────────────────────────────────────────────
        with tab_signup:
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            with st.form("form_signup"):
                st.markdown("### Create your account")
                col_a, col_b = st.columns(2)
                with col_a:
                    su_name  = st.text_input("Full name",     placeholder="Jane Smith")
                    su_email = st.text_input("Email address", placeholder="jane@example.com")
                    su_state = st.text_input("State",         placeholder="Maharashtra")
                with col_b:
                    su_phone  = st.text_input("Phone number",     placeholder="+91 98765 43210")
                    su_pass   = st.text_input("Password",         type="password",
                                              placeholder="Min 6 chars, 1 uppercase, 1 digit")
                    su_pass2  = st.text_input("Confirm password", type="password",
                                              placeholder="Repeat password")
                create = st.form_submit_button("Create Account →", use_container_width=True)

            if create:
                errs = []
                if not su_name.strip():
                    errs.append("Full name is required.")
                if not validate_email(su_email):
                    errs.append("Enter a valid email address.")
                if not validate_phone(su_phone):
                    errs.append("Enter a valid phone number (7–15 digits).")
                if su_pass != su_pass2:
                    errs.append("Passwords do not match.")

                # Password strength check
                strong, strength_errors = validate_password_strength(su_pass)
                if not strong:
                    errs.extend(strength_errors)

                if errs:
                    for e in errs:
                        st.warning(e)
                elif customer_add_data(
                    su_name.strip(), hash_password(su_pass),
                    su_email.strip(), su_state.strip(), su_phone.strip()
                ):
                    st.success("✅ Account created! Switch to the **Login** tab to sign in.")
                else:
                    st.error("An account with that email already exists.")

            # ── Password strength hint ───────────────────────────────────
            st.markdown("""
            <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:10px;
                        padding:0.75rem 1rem; font-size:0.78rem; color:#475569; margin-top:0.5rem;">
                <strong>Password requirements:</strong> min 6 characters ·
                at least 1 uppercase · 1 lowercase · 1 digit
            </div>
            """, unsafe_allow_html=True)

        # ── Admin Login ──────────────────────────────────────────────────
        with tab_admin:
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            with st.form("form_admin"):
                st.markdown("### Admin access")
                adm_user = st.text_input("Admin username", placeholder="admin")
                adm_pass = st.text_input("Admin password", type="password", placeholder="••••••••")
                adm_sub  = st.form_submit_button("Login as Admin →", use_container_width=True)

            if adm_sub:
                if authenticate_admin(adm_user, adm_pass):
                    st.session_state.logged_in   = True
                    st.session_state.user_type   = "admin"
                    st.session_state.username    = adm_user
                    st.session_state.last_active = time.time()
                    logger.info("Admin login: %s", adm_user)
                    st.rerun()
                else:
                    st.error("❌ Invalid admin credentials.")

        st.markdown("""
        <p style="text-align:center; font-size:0.75rem; color:#94A3B8; margin-top:2rem;">
            Made by Himanshu Sharma &nbsp;·&nbsp; Pharmacy Management System
        </p>
        """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Customer profile sidebar
# ---------------------------------------------------------------------------

def _show_customer_profile_sidebar() -> None:
    from styles import sidebar_section_label
    sidebar_section_label("My Account")

    customer = customer_get_by_email(st.session_state.email or "")
    if not customer:
        return

    name, email, state, phone = customer
    st.sidebar.markdown(f"""
    <div style="padding:0.75rem 0.25rem; font-size:0.82rem;">
        <div style="font-weight:700; color:#E2E8F0; margin-bottom:0.2rem;">👤 {name}</div>
        <div style="color:#64748B; margin-bottom:0.1rem;">✉️ {email}</div>
        <div style="color:#64748B; margin-bottom:0.1rem;">📍 {state}</div>
        <div style="color:#64748B;">📞 {phone}</div>
    </div>
    """, unsafe_allow_html=True)

    with st.sidebar.expander("✏️ Update Phone"):
        new_phone = st.text_input("New phone number", key="sidebar_phone",
                                   placeholder="+91 98765 43210")
        if st.button("Save", key="sidebar_save_phone"):
            if validate_phone(new_phone):
                if customer_update(email, new_phone.strip()):
                    st.success("Phone updated!")
                    st.rerun()
                else:
                    st.error("Update failed.")
            else:
                st.warning("Enter a valid phone number.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    _init_session()

    if not st.session_state.tables_ok:
        create_all_tables()
        seed_demo_data()          # no-op if DB already has data
        st.session_state.tables_ok = True

    if st.session_state.logged_in:
        # Session timeout check
        if _check_session_timeout():
            st.rerun()
            return

        _touch_activity()
        inject_css()

        if st.session_state.user_type == "admin":
            sidebar_logo("Admin Portal")
        else:
            sidebar_logo("Customer Portal")
            _show_customer_profile_sidebar()

        from styles import sidebar_section_label
        sidebar_section_label("Session")
        if st.sidebar.button("🚪  Logout", use_container_width=True):
            _logout()
            st.rerun()

        if st.session_state.user_type == "admin":
            show_admin_dashboard()
        elif st.session_state.user_type == "customer":
            show_customer_dashboard(
                st.session_state.username,
                st.session_state.email or st.session_state.username,
            )
        return

    _auth_page()


if __name__ == "__main__":
    main()