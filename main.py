"""
main.py — Entry point: routing, session state, and authentication screens.

UI: Beautiful centered auth card with tabs for Login / Sign Up / Admin.
"""

import logging
import streamlit as st

from database import create_all_tables, customer_get_by_email
from auth import (
    authenticate_customer, authenticate_admin,
    hash_password, validate_email, validate_phone,
)
from database import customer_add_data
from admin_ui import show_admin_dashboard
from customer_ui import show_customer_dashboard
from styles import inject_css, sidebar_logo

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

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
        "logged_in": False,
        "user_type": None,      # "customer" | "admin"
        "username":  None,
        "email":     None,
        "tables_ok": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _logout() -> None:
    for k in ("logged_in", "user_type", "username", "email"):
        st.session_state[k] = None
    st.session_state.logged_in = False


# ---------------------------------------------------------------------------
# Auth screens
# ---------------------------------------------------------------------------

def _auth_page() -> None:
    inject_css()

    # Centered narrow column
    _, mid, _ = st.columns([1, 1.6, 1])
    with mid:
        # ── Logo / branding ─────────────────────────────────────────────
        st.markdown("""
        <div style="text-align:center; padding:2rem 0 1.5rem;">
            <div style="font-size:3.5rem; margin-bottom:0.5rem;">💊</div>
            <h1 style="font-size:1.85rem; font-weight:800; color:#1E293B;
                       margin:0; letter-spacing:-0.02em;">PharmaSystem</h1>
            <p style="font-size:0.875rem; color:#64748B; margin:0.3rem 0 0;">
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
                if not email or not password:
                    st.warning("Please enter your email and password.")
                elif authenticate_customer(email.strip(), password):
                    customer = customer_get_by_email(email.strip())
                    st.session_state.logged_in = True
                    st.session_state.user_type = "customer"
                    st.session_state.username  = customer[0] if customer else email
                    st.session_state.email     = email.strip()
                    logger.info("Customer login: %s", email)
                    st.rerun()
                else:
                    st.error("❌ Invalid email or password.")

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
                    su_pass   = st.text_input("Password",         type="password", placeholder="Min 6 chars")
                    su_pass2  = st.text_input("Confirm password", type="password", placeholder="Repeat password")
                create = st.form_submit_button("Create Account →", use_container_width=True)

            if create:
                errs = []
                if not su_name.strip():
                    errs.append("Full name is required.")
                if not validate_email(su_email):
                    errs.append("Enter a valid email address.")
                if not validate_phone(su_phone):
                    errs.append("Enter a valid phone number (7–15 digits).")
                if len(su_pass) < 6:
                    errs.append("Password must be at least 6 characters.")
                if su_pass != su_pass2:
                    errs.append("Passwords do not match.")

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
                    st.session_state.logged_in = True
                    st.session_state.user_type = "admin"
                    st.session_state.username  = adm_user
                    logger.info("Admin login: %s", adm_user)
                    st.rerun()
                else:
                    st.error("❌ Invalid admin credentials.")

        # Footer
        st.markdown("""
        <p style="text-align:center; font-size:0.75rem; color:#94A3B8; margin-top:2rem;">
            Made by Himanshu Sharma &nbsp;·&nbsp; Pharmacy Management System
        </p>
        """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    _init_session()

    if not st.session_state.tables_ok:
        create_all_tables()
        st.session_state.tables_ok = True

    if st.session_state.logged_in:
        inject_css()

        if st.session_state.user_type == "admin":
            sidebar_logo("Admin Portal")
        else:
            sidebar_logo("Customer Portal")

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