"""
admin_ui.py — Admin dashboard: metric cards, inventory, customers, orders.

Round-2 UI upgrade:
  - metric_cards_row() at the top (total drugs, low stock, customers, revenue)
  - Custom alert banners via styles.py
  - Drug search with highlighted low-stock rows
  - Modern forms inside styled containers
  - Order delete section
"""

import logging
import streamlit as st
import pandas as pd

from database import (
    LOW_STOCK_THRESHOLD, get_connection,
    drug_add_data, drug_view_all_data, drug_update, drug_update_price,
    drug_delete, drug_get_low_stock,
    customer_view_all_data, customer_update, customer_delete,
    order_view_all_data, order_delete,
)
from styles import (
    metric_cards_row, alert_warning, alert_danger, alert_success,
    page_header, section_header, sidebar_section_label,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers — admin metrics
# ---------------------------------------------------------------------------

def _get_metrics() -> dict:
    conn = get_connection()
    c    = conn.cursor()

    c.execute("SELECT COUNT(*) FROM Drugs")
    total_drugs = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM Drugs WHERE D_Qty <= ?", (LOW_STOCK_THRESHOLD,))
    low_stock_count = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM Customers")
    total_customers = c.fetchone()[0]

    c.execute("SELECT COUNT(DISTINCT O_id) FROM Orders")
    total_orders = c.fetchone()[0]

    c.execute("SELECT COALESCE(SUM(quantity * unit_price), 0) FROM OrderItems")
    total_revenue = c.fetchone()[0]

    return {
        "total_drugs":     total_drugs,
        "low_stock_count": low_stock_count,
        "total_customers": total_customers,
        "total_orders":    total_orders,
        "total_revenue":   total_revenue,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def show_admin_dashboard() -> None:
    page_header("🏥 Pharmacy Dashboard", "Manage inventory, customers, and orders")

    # ── Metric cards ────────────────────────────────────────────────────────
    m = _get_metrics()
    metric_cards_row([
        {"icon": "💊", "value": m["total_drugs"],
         "label": "Total Drugs",     "color": "#2563EB", "bg": "#EFF6FF"},
        {"icon": "⚠️", "value": m["low_stock_count"],
         "label": "Low Stock",       "color": "#EF4444", "bg": "#FEF2F2"},
        {"icon": "👥", "value": m["total_customers"],
         "label": "Customers",       "color": "#7C3AED", "bg": "#F5F3FF"},
        {"icon": "📦", "value": m["total_orders"],
         "label": "Total Orders",    "color": "#0891B2", "bg": "#ECFEFF"},
        {"icon": "₹",  "value": f"{m['total_revenue']:,.0f}",
         "label": "Revenue (₹)",     "color": "#059669", "bg": "#ECFDF5"},
    ])

    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

    # ── Global low-stock alert ───────────────────────────────────────────────
    low = drug_get_low_stock()
    if low:
        names = ", ".join(f"**{r[0]}** ({r[2]} left)" for r in low)
        alert_danger(
            f"Low Stock Alert — {len(low)} drug(s) need restocking",
            names,
        )

    # ── Sidebar navigation ───────────────────────────────────────────────────
    sidebar_section_label("Navigation")
    section  = st.sidebar.selectbox("Section",  ["Drugs", "Customers", "Orders", "About"],
                                    label_visibility="collapsed")
    sidebar_section_label("Actions")
    action   = st.sidebar.selectbox("Action",   ["View", "Add", "Update", "Delete"],
                                    label_visibility="collapsed")

    if section == "Drugs":
        _drugs_section(action)
    elif section == "Customers":
        _customers_section(action)
    elif section == "Orders":
        _orders_section()
    elif section == "About":
        _about_section()


# ---------------------------------------------------------------------------
# Drugs
# ---------------------------------------------------------------------------

def _drugs_section(action: str) -> None:
    section_header("💊", "Drug Inventory")

    if action == "View":
        drugs = drug_view_all_data()
        if not drugs:
            alert_warning("No drugs yet", "Add your first drug using the sidebar → Add.")
            return

        df = pd.DataFrame(
            drugs,
            columns=["Name", "Expiry Date", "Use", "Qty", "ID", "Price (₹)", "Image"]
        )

        search = st.text_input("🔍  Search by name or ID", placeholder="e.g. Aspirin or #ASP")
        if search:
            mask = (
                df["Name"].str.contains(search, case=False, na=False) |
                df["ID"].str.contains(search, case=False, na=False)
            )
            df = df[mask]
            if df.empty:
                st.info(f"No drugs match **'{search}'**.")
                return

        col_table, col_stock = st.columns([2, 1])

        with col_table:
            st.markdown("##### 📋 All Drugs")

            # Highlight low-stock rows
            def _highlight(row):
                color = "background-color:#FEE2E2; color:#991B1B" \
                    if int(row["Qty"]) <= LOW_STOCK_THRESHOLD else ""
                return [color] * len(row)

            display_df = df.drop(columns=["Image"])
            st.dataframe(
                display_df.style.apply(_highlight, axis=1),
                use_container_width=True,
                hide_index=True,
            )

        with col_stock:
            st.markdown("##### 📊 Stock Summary")
            total   = int(df["Qty"].sum())
            low_cnt = int((df["Qty"].astype(int) <= LOW_STOCK_THRESHOLD).sum())
            st.metric("Total Units",  total)
            st.metric("Low Stock",    low_cnt, delta=f"-{low_cnt}" if low_cnt else None,
                      delta_color="inverse")
            avg_price = df["Price (₹)"].astype(float).mean()
            st.metric("Avg. Price ₹", f"{avg_price:.2f}")

    elif action == "Add":
        with st.form("form_add_drug"):
            st.markdown("##### ➕ Add New Drug")
            c1, c2 = st.columns(2)
            with c1:
                d_name   = st.text_input("Drug Name",   placeholder="e.g. Paracetamol")
                d_expiry = st.date_input("Expiry Date")
                d_use    = st.text_area("When to Use",  placeholder="Describe indication…", height=100)
            with c2:
                d_qty   = st.number_input("Quantity",       min_value=0, step=1)
                d_price = st.number_input("Price (₹)",      min_value=0.0, step=0.5, format="%.2f")
                d_id    = st.text_input("Drug ID",          placeholder="e.g. #D001")
                d_image = st.text_input("Image filename",   placeholder="e.g. aspirin.jpg (optional)")

            submitted = st.form_submit_button("Add Drug →", use_container_width=True)

        if submitted:
            if not d_name.strip() or not d_id.strip():
                st.warning("Drug Name and Drug ID are required.")
            else:
                ok = drug_add_data(
                    d_name.strip(), str(d_expiry), d_use.strip(),
                    int(d_qty), d_id.strip(), float(d_price),
                    d_image.strip() or None
                )
                if ok:
                    alert_success("Drug Added", f"**{d_name}** (ID: {d_id}) added to inventory.")
                else:
                    alert_danger("Failed", "Drug ID already exists. Choose a unique ID.")

    elif action == "Update":
        with st.form("form_update_drug"):
            st.markdown("##### ✏️ Update Drug")
            d_id    = st.text_input("Drug ID",              placeholder="#D001")
            d_use   = st.text_area("Updated Usage",         height=80)
            d_price = st.number_input("Updated Price (₹) — 0 to skip",
                                      min_value=0.0, step=0.5, format="%.2f")
            submitted = st.form_submit_button("Save Changes →", use_container_width=True)

        if submitted:
            if not d_id.strip():
                st.warning("Drug ID is required.")
            else:
                ok_use   = drug_update(d_id.strip(), d_use.strip())
                ok_price = drug_update_price(d_id.strip(), float(d_price)) if d_price > 0 else True
                if ok_use and ok_price:
                    alert_success("Updated", f"Drug **{d_id}** updated successfully.")
                else:
                    alert_danger("Not Found", f"No drug with ID **{d_id}** exists.")

    elif action == "Delete":
        with st.form("form_delete_drug"):
            st.markdown("##### 🗑️ Delete Drug")
            st.markdown(
                "<p style='color:#64748B; font-size:0.85rem;'>"
                "⚠️ This action is irreversible.</p>",
                unsafe_allow_html=True
            )
            d_id      = st.text_input("Drug ID to delete", placeholder="#D001")
            submitted = st.form_submit_button("Delete Drug", use_container_width=True)

        if submitted:
            if not d_id.strip():
                st.warning("Drug ID is required.")
            else:
                result = drug_delete(d_id.strip())
                # drug_delete returns bool or (bool, str) depending on version
                if isinstance(result, tuple):
                    ok, msg = result
                else:
                    ok, msg = result, ""
                if ok:
                    alert_success("Deleted", f"Drug **{d_id}** has been removed.")
                else:
                    alert_danger("Delete Failed", msg or f"Drug **{d_id}** not found.")


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------

def _customers_section(action: str) -> None:
    section_header("👥", "Customer Management")

    if action == "View":
        customers = customer_view_all_data()
        if not customers:
            alert_warning("No customers yet", "Customers will appear here once they register.")
            return
        df = pd.DataFrame(customers, columns=["Name", "Email", "State", "Phone"])
        st.markdown(f"**{len(df)} registered customer(s)**")
        st.dataframe(df, use_container_width=True, hide_index=True)

    elif action == "Update":
        with st.form("form_update_customer"):
            st.markdown("##### ✏️ Update Customer Phone")
            email  = st.text_input("Customer Email")
            number = st.text_input("New Phone Number")
            sub    = st.form_submit_button("Save →", use_container_width=True)
        if sub:
            if not email.strip() or not number.strip():
                st.warning("Both fields are required.")
            elif customer_update(email.strip(), number.strip()):
                alert_success("Updated", f"Phone updated for **{email}**.")
            else:
                alert_danger("Not Found", f"No customer with email **{email}**.")

    elif action == "Delete":
        with st.form("form_delete_customer"):
            st.markdown("##### 🗑️ Delete Customer")
            st.markdown(
                "<p style='color:#64748B; font-size:0.85rem;'>⚠️ This permanently removes the account.</p>",
                unsafe_allow_html=True
            )
            email = st.text_input("Customer Email")
            sub   = st.form_submit_button("Delete Customer", use_container_width=True)
        if sub:
            if not email.strip():
                st.warning("Email is required.")
            else:
                result = customer_delete(email.strip())
                if isinstance(result, tuple):
                    ok, msg = result
                else:
                    ok, msg = result, ""
                if ok:
                    alert_success("Deleted", f"Customer **{email}** removed.")
                else:
                    alert_danger("Failed", msg or f"No customer with email **{email}**.")


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

def _orders_section() -> None:
    section_header("📦", "All Orders")

    rows = order_view_all_data()
    if not rows:
        alert_warning("No orders yet", "Orders will appear here once customers place them.")
        return

    df = pd.DataFrame(
        rows,
        columns=["Order ID", "Customer", "Timestamp", "Drug", "Qty", "Unit Price (₹)"]
    )
    df["Line Total (₹)"] = (df["Qty"] * df["Unit Price (₹)"]).round(2)

    # ── Summary metrics ──────────────────────────────────────────────────────
    from styles import metric_cards_row as mcr
    mcr([
        {"icon": "📋", "value": df["Order ID"].nunique(),
         "label": "Total Orders",   "color": "#2563EB", "bg": "#EFF6FF"},
        {"icon": "👤", "value": df["Customer"].nunique(),
         "label": "Customers",      "color": "#7C3AED", "bg": "#F5F3FF"},
        {"icon": "₹",  "value": f"{df['Line Total (₹)'].sum():,.0f}",
         "label": "Total Revenue",  "color": "#059669", "bg": "#ECFDF5"},
    ])

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # ── Per-customer totals ──────────────────────────────────────────────────
    with st.expander("📊 Revenue by Customer"):
        summary = (
            df.groupby("Customer")["Line Total (₹)"]
            .sum().reset_index()
            .rename(columns={"Line Total (₹)": "Total Spent (₹)"})
            .sort_values("Total Spent (₹)", ascending=False)
        )
        st.dataframe(summary, use_container_width=True, hide_index=True)

    # ── Delete ───────────────────────────────────────────────────────────────
    st.divider()
    section_header("🗑️", "Delete Order")
    with st.form("form_delete_order"):
        order_id = st.text_input("Order ID", placeholder="e.g. alice#A1B2C3D4")
        sub      = st.form_submit_button("Delete Order", use_container_width=True)
    if sub:
        if not order_id.strip():
            st.warning("Order ID is required.")
        elif order_delete(order_id.strip()):
            alert_success("Deleted", f"Order **{order_id}** and its items removed.")
        else:
            alert_danger("Not Found", f"No order with ID **{order_id}**.")


# ---------------------------------------------------------------------------
# About
# ---------------------------------------------------------------------------

def _about_section() -> None:
    section_header("ℹ️", "About")
    st.markdown("""
    <div style="
        background:white; border-radius:16px; padding:2rem;
        border:1px solid #F1F5F9;
        box-shadow:0 1px 3px rgba(0,0,0,0.05),0 4px 16px rgba(0,0,0,0.06);
    ">
        <h3 style="margin:0 0 0.5rem; color:#1E293B;">Pharmacy Management System</h3>
        <p style="color:#64748B; font-size:0.9rem; margin:0 0 1.5rem;">
            Made by <strong>Himanshu Sharma</strong>
        </p>
        <table style="width:100%; border-collapse:collapse; font-size:0.875rem;">
            <tr style="border-bottom:1px solid #F1F5F9;">
                <td style="padding:0.6rem 0.5rem; color:#64748B; font-weight:600; width:35%;">Stack</td>
                <td style="padding:0.6rem 0.5rem; color:#1E293B;">Python · Streamlit · SQLite · Pandas</td>
            </tr>
            <tr style="border-bottom:1px solid #F1F5F9;">
                <td style="padding:0.6rem 0.5rem; color:#64748B; font-weight:600;">Security</td>
                <td style="padding:0.6rem 0.5rem; color:#1E293B;">PBKDF2-HMAC-SHA256 · env-var admin credentials</td>
            </tr>
            <tr style="border-bottom:1px solid #F1F5F9;">
                <td style="padding:0.6rem 0.5rem; color:#64748B; font-weight:600;">Schema</td>
                <td style="padding:0.6rem 0.5rem; color:#1E293B;">Normalised OrderItems · Atomic transactions · FK enforcement</td>
            </tr>
            <tr>
                <td style="padding:0.6rem 0.5rem; color:#64748B; font-weight:600;">Testing</td>
                <td style="padding:0.6rem 0.5rem; color:#1E293B;">62 pytest tests · In-memory SQLite · No Streamlit server required</td>
            </tr>
        </table>
    </div>
    """, unsafe_allow_html=True)
