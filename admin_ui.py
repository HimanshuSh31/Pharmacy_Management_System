"""
admin_ui.py — Admin dashboard: metrics, inventory, customers, orders.

Round-4 improvements:
  - All reads via data.py (@st.cache_data) + cache invalidation after writes
  - Drug categories (D_Category) + supplier + prescription flag
  - Update Drug: expiry, category, supplier, prescription, add stock
  - Bulk CSV drug import with template download
  - Paginated drug list (20 per page)
  - Low-stock email alert button (via notifier.py)
  - Category filter in inventory view
  - Expiry row colours (expired=red, ≤30 days=orange, low stock=yellow)
  - CSV export on all three tables
"""

import io
import logging
import os
from datetime import date

import streamlit as st
import pandas as pd

from database import (
    LOW_STOCK_THRESHOLD,
    drug_add_data, drug_update_details, drug_update_expiry,
    drug_delete, drug_bulk_import,
    customer_update, customer_delete,
    order_delete,
)
from data import (
    get_all_drugs, get_low_stock_drugs, get_drug_categories,
    get_all_customers, get_all_orders,
    invalidate_drugs, invalidate_customers, invalidate_orders,
)
from data import get_all_drugs
from notifier import is_smtp_configured, send_low_stock_alert
from styles import (
    metric_cards_row, alert_warning, alert_danger, alert_success,
    page_header, section_header, sidebar_section_label,
)
from database import get_connection

logger    = logging.getLogger(__name__)
IMAGE_DIR = "images"
PAGE_SIZE = 20


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_metrics() -> dict:
    conn = get_connection()
    c    = conn.cursor()
    c.execute("SELECT COUNT(*) FROM Drugs");                                        total_drugs     = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM Drugs WHERE D_Qty <= ?", (LOW_STOCK_THRESHOLD,)); low_stock_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM Customers");                                    total_customers = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT O_id) FROM Orders");                           total_orders    = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(quantity * unit_price), 0) FROM OrderItems");   total_revenue   = c.fetchone()[0]
    return dict(total_drugs=total_drugs, low_stock_count=low_stock_count,
                total_customers=total_customers, total_orders=total_orders,
                total_revenue=total_revenue)


def _save_uploaded_image(uploaded_file) -> str:
    os.makedirs(IMAGE_DIR, exist_ok=True)
    filepath = os.path.join(IMAGE_DIR, uploaded_file.name)
    with open(filepath, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return uploaded_file.name


def _is_expired(expdate_str: str) -> bool:
    try:
        return date.fromisoformat(str(expdate_str)) < date.today()
    except (ValueError, TypeError):
        return False


def _days_to_expiry(expdate_str: str) -> int:
    try:
        return (date.fromisoformat(str(expdate_str)) - date.today()).days
    except (ValueError, TypeError):
        return 9999


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def show_admin_dashboard() -> None:
    page_header("🏥 Pharmacy Dashboard", "Manage inventory, customers, and orders")

    m = _get_metrics()
    metric_cards_row([
        {"icon": "💊", "value": m["total_drugs"],             "label": "Total Drugs",    "color": "#2563EB", "bg": "#EFF6FF"},
        {"icon": "⚠️", "value": m["low_stock_count"],         "label": "Low Stock",      "color": "#EF4444", "bg": "#FEF2F2"},
        {"icon": "👥", "value": m["total_customers"],         "label": "Customers",      "color": "#7C3AED", "bg": "#F5F3FF"},
        {"icon": "📦", "value": m["total_orders"],            "label": "Total Orders",   "color": "#0891B2", "bg": "#ECFEFF"},
        {"icon": "₹",  "value": f"{m['total_revenue']:,.0f}", "label": "Revenue (₹)",    "color": "#059669", "bg": "#ECFDF5"},
    ])

    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

    low = get_low_stock_drugs()
    if low:
        names = ", ".join(f"**{r[0]}** ({r[2]} left)" for r in low)
        col_alert, col_btn = st.columns([3, 1])
        with col_alert:
            alert_danger(f"Low Stock Alert — {len(low)} drug(s) need restocking", names)
        with col_btn:
            st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
            if st.button("📧 Email Alert", use_container_width=True,
                         help="Send low-stock email (requires SMTP config in .env)"):
                if is_smtp_configured():
                    ok, msg = send_low_stock_alert(low)
                    if ok:
                        alert_success("Email Sent", msg)
                    else:
                        alert_danger("Email Failed", msg)
                else:
                    alert_warning(
                        "SMTP Not Configured",
                        "Set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, ALERT_EMAIL in your .env file."
                    )

    sidebar_section_label("Navigation")
    section = st.sidebar.selectbox("Section", ["Drugs", "Customers", "Orders", "About"],
                                   label_visibility="collapsed")
    sidebar_section_label("Actions")
    action  = st.sidebar.selectbox("Action", ["View", "Add", "Update", "Delete", "Import"],
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

DRUG_COLS = ["Name", "Expiry Date", "Use", "Qty", "ID",
             "Price (₹)", "Image", "Category", "Supplier", "Rx Required"]


def _drugs_section(action: str) -> None:
    section_header("💊", "Drug Inventory")

    if action == "View":
        drugs = get_all_drugs()
        if not drugs:
            alert_warning("No drugs yet", "Add your first drug using the sidebar → Add.")
            return

        df = pd.DataFrame(drugs, columns=DRUG_COLS)

        # ── Filters row ──────────────────────────────────────────────────────
        f1, f2 = st.columns([2, 1])
        with f1:
            search = st.text_input("🔍  Search by name or ID", placeholder="e.g. Aspirin or #ASP")
        with f2:
            categories = ["All"] + sorted(df["Category"].dropna().unique().tolist())
            cat_filter = st.selectbox("Category", categories, label_visibility="visible")

        if search:
            mask = (df["Name"].str.contains(search, case=False, na=False) |
                    df["ID"].str.contains(search, case=False, na=False))
            df = df[mask]
        if cat_filter != "All":
            df = df[df["Category"] == cat_filter]

        if df.empty:
            st.info("No drugs match the current filters.")
            return

        # ── Pagination ───────────────────────────────────────────────────────
        total_pages = max(1, (len(df) + PAGE_SIZE - 1) // PAGE_SIZE)
        page = 1
        if total_pages > 1:
            page = st.number_input("Page", min_value=1, max_value=total_pages,
                                   value=1, step=1,
                                   help=f"{len(df)} drugs · {PAGE_SIZE} per page")
            st.markdown(f"<small style='color:#64748B;'>Page {page} of {total_pages} &nbsp;·&nbsp; {len(df)} result(s)</small>",
                        unsafe_allow_html=True)
        page_df = df.iloc[(page - 1) * PAGE_SIZE: page * PAGE_SIZE]

        col_table, col_stock = st.columns([2, 1])
        with col_table:
            st.markdown("##### 📋 Drug List")

            def _highlight(row):
                if _is_expired(row["Expiry Date"]):
                    return ["background-color:#FEE2E2; color:#991B1B"] * len(row)
                if int(row["Qty"]) <= LOW_STOCK_THRESHOLD:
                    return ["background-color:#FEF9C3; color:#854D0E"] * len(row)
                if _days_to_expiry(row["Expiry Date"]) <= 30:
                    return ["background-color:#FEF3C7; color:#92400E"] * len(row)
                return [""] * len(row)

            display_df = page_df.drop(columns=["Image"])
            st.dataframe(display_df.style.apply(_highlight, axis=1),
                         use_container_width=True, hide_index=True)
            st.markdown("""
            <div style="display:flex;gap:1rem;font-size:0.73rem;color:#64748B;margin-top:0.3rem;">
                <span>🔴 Expired</span><span>🟡 Low stock (≤10)</span><span>🟠 Expiring ≤30 days</span>
            </div>""", unsafe_allow_html=True)

        with col_stock:
            st.markdown("##### 📊 Summary")
            total     = int(df["Qty"].sum())
            low_cnt   = int((df["Qty"].astype(int) <= LOW_STOCK_THRESHOLD).sum())
            exp_cnt   = int(df["Expiry Date"].apply(_is_expired).sum())
            rx_cnt    = int((df["Rx Required"].astype(int) > 0).sum())
            avg_price = df["Price (₹)"].astype(float).mean()
            st.metric("Total Units",      total)
            st.metric("Low Stock",        low_cnt, delta=f"-{low_cnt}" if low_cnt else None, delta_color="inverse")
            st.metric("Expired",          exp_cnt, delta=f"-{exp_cnt}" if exp_cnt else None, delta_color="inverse")
            st.metric("Prescription Only", rx_cnt)
            st.metric("Avg. Price ₹",     f"{avg_price:.2f}")

        full_display = df.drop(columns=["Image"])
        st.download_button("⬇️ Export All to CSV",
                           data=full_display.to_csv(index=False).encode(),
                           file_name="drugs_export.csv", mime="text/csv")

    elif action == "Add":
        categories = get_drug_categories() or ["General"]
        with st.form("form_add_drug"):
            st.markdown("##### ➕ Add New Drug")
            c1, c2 = st.columns(2)
            with c1:
                d_name   = st.text_input("Drug Name",   placeholder="e.g. Paracetamol 500mg")
                d_expiry = st.date_input("Expiry Date")
                d_use    = st.text_area("When to Use",  placeholder="Indication / instructions…", height=90)
                d_supplier = st.text_input("Supplier",  placeholder="e.g. Sun Pharma")
            with c2:
                d_qty    = st.number_input("Quantity",      min_value=0, step=1)
                d_price  = st.number_input("Price (₹)",     min_value=0.0, step=0.5, format="%.2f")
                d_id     = st.text_input("Drug ID",         placeholder="e.g. #D001")
                d_cat    = st.text_input("Category",        placeholder="e.g. Antibiotic, Vitamin…",
                                         value="General")
                d_rx     = st.checkbox("Prescription required?")
            d_image_file = st.file_uploader("Drug Image (optional)",
                                            type=["jpg","jpeg","png","webp"])
            submitted = st.form_submit_button("Add Drug →", use_container_width=True)

        if submitted:
            if not d_name.strip() or not d_id.strip():
                st.warning("Drug Name and Drug ID are required.")
            else:
                filename = _save_uploaded_image(d_image_file) if d_image_file else None
                ok = drug_add_data(
                    d_name.strip(), str(d_expiry), d_use.strip(),
                    int(d_qty), d_id.strip(), float(d_price), filename,
                    d_cat.strip() or "General", d_supplier.strip(), int(d_rx)
                )
                if ok:
                    invalidate_drugs()
                    alert_success("Drug Added", f"**{d_name}** (ID: {d_id}) added to inventory.")
                else:
                    alert_danger("Failed", "Drug ID already exists. Choose a unique ID.")

    elif action == "Update":
        with st.form("form_update_drug"):
            st.markdown("##### ✏️ Update Drug")
            d_id  = st.text_input("Drug ID", placeholder="#D001")
            c1, c2 = st.columns(2)
            with c1:
                d_use      = st.text_area("Updated Usage",          height=70, placeholder="Leave blank to keep existing")
                d_price    = st.number_input("Updated Price (₹) — 0 to skip",
                                             min_value=0.0, step=0.5, format="%.2f")
                d_add_qty  = st.number_input("Add Stock Units — 0 to skip",
                                             min_value=0, step=1)
            with c2:
                update_expiry = st.checkbox("Update expiry date?")
                d_expiry      = st.date_input("New Expiry Date", disabled=not update_expiry)
                d_cat         = st.text_input("Category — blank to keep existing",
                                              placeholder="e.g. Antibiotic")
                d_supplier    = st.text_input("Supplier — blank to keep existing")
                rx_options    = {"No change": -1, "Not required": 0, "Required": 1}
                rx_choice     = st.selectbox("Prescription", list(rx_options.keys()))
            submitted = st.form_submit_button("Save Changes →", use_container_width=True)

        if submitted:
            if not d_id.strip():
                st.warning("Drug ID is required.")
            else:
                ok = drug_update_details(
                    d_id.strip(),
                    d_use.strip(), float(d_price), int(d_add_qty),
                    expdate      = str(d_expiry) if update_expiry else "",
                    category     = d_cat.strip(),
                    supplier     = d_supplier.strip(),
                    prescription = rx_options[rx_choice],
                )
                if ok:
                    invalidate_drugs()
                    msg = f"Drug **{d_id}** updated."
                    if d_add_qty > 0:
                        msg += f" Added **{d_add_qty}** units to stock."
                    alert_success("Updated", msg)
                else:
                    alert_danger("Not Found", f"No drug with ID **{d_id}** exists.")

    elif action == "Delete":
        with st.form("form_delete_drug"):
            st.markdown("##### 🗑️ Delete Drug")
            st.markdown("<p style='color:#64748B;font-size:0.85rem;'>⚠️ Irreversible — blocked if drug has existing orders.</p>",
                        unsafe_allow_html=True)
            d_id      = st.text_input("Drug ID to delete", placeholder="#D001")
            submitted = st.form_submit_button("Delete Drug", use_container_width=True)

        if submitted:
            if not d_id.strip():
                st.warning("Drug ID is required.")
            else:
                ok, msg = drug_delete(d_id.strip())
                if ok:
                    invalidate_drugs()
                    alert_success("Deleted", f"Drug **{d_id}** removed.")
                else:
                    alert_danger("Delete Failed", msg)

    elif action == "Import":
        section_header("📥", "Bulk CSV Import")

        # ── Template download ────────────────────────────────────────────
        template_csv = (
            "id,name,expdate,use,qty,price,category,supplier,prescription,image\n"
            "#D001,Paracetamol 500mg,2026-12-31,For fever and pain,100,12.50,Pain Relief,Sun Pharma,0,\n"
            "#D002,Amoxicillin 250mg,2027-06-30,Antibiotic for infections,50,45.00,Antibiotic,Cipla,1,\n"
        )
        st.download_button("⬇️ Download CSV Template",
                           data=template_csv.encode(), file_name="drug_import_template.csv",
                           mime="text/csv")

        st.markdown("""
        <div style="background:var(--background-color);border:1px solid rgba(128, 128, 128, 0.2);border-radius:10px;
                    padding:0.9rem 1rem;font-size:0.8rem;color:var(--text-color);opacity:0.85;margin:0.75rem 0;">
            <strong>Required columns:</strong> id · name · expdate (YYYY-MM-DD) · use · qty · price<br>
            <strong>Optional columns:</strong> category · supplier · prescription (0/1) · image
        </div>
        """, unsafe_allow_html=True)

        uploaded = st.file_uploader("Upload CSV file", type=["csv"])
        if uploaded:
            try:
                df_import = pd.read_csv(uploaded, dtype=str).fillna("")
                st.markdown(f"**Preview — {len(df_import)} row(s):**")
                st.dataframe(df_import.head(10), use_container_width=True, hide_index=True)

                if st.button("✅ Import All Rows", use_container_width=True):
                    records = df_import.to_dict(orient="records")
                    ok_count, fail_count = drug_bulk_import(records)
                    invalidate_drugs()
                    if ok_count:
                        alert_success("Import Complete",
                                      f"**{ok_count}** drug(s) imported · **{fail_count}** skipped (duplicate IDs).")
                    else:
                        alert_danger("Import Failed",
                                     f"All {fail_count} row(s) failed — check for duplicate IDs or missing required fields.")
            except Exception as exc:
                alert_danger("CSV Error", str(exc))


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------

def _customers_section(action: str) -> None:
    section_header("👥", "Customer Management")

    if action == "View":
        customers = get_all_customers()
        if not customers:
            alert_warning("No customers yet", "Customers appear here after registration.")
            return
        df = pd.DataFrame(customers, columns=["Name", "Email", "State", "Phone"])
        search = st.text_input("🔍  Search by name or email")
        if search:
            mask = (df["Name"].str.contains(search, case=False, na=False) |
                    df["Email"].str.contains(search, case=False, na=False))
            df = df[mask]
            if df.empty:
                st.info(f"No customers match **'{search}'**.")
                return
        st.markdown(f"**{len(df)} customer(s)**")
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("⬇️ Export to CSV", data=df.to_csv(index=False).encode(),
                           file_name="customers_export.csv", mime="text/csv")

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
                invalidate_customers()
                alert_success("Updated", f"Phone updated for **{email}**.")
            else:
                alert_danger("Not Found", f"No customer with email **{email}**.")

    elif action == "Delete":
        with st.form("form_delete_customer"):
            st.markdown("##### 🗑️ Delete Customer")
            email = st.text_input("Customer Email")
            sub   = st.form_submit_button("Delete Customer", use_container_width=True)
        if sub:
            if not email.strip():
                st.warning("Email is required.")
            else:
                ok, msg = customer_delete(email.strip())
                if ok:
                    invalidate_customers()
                    alert_success("Deleted", f"Customer **{email}** removed.")
                else:
                    alert_danger("Failed", msg)


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

def _orders_section() -> None:
    section_header("📦", "All Orders")

    rows = get_all_orders()
    if not rows:
        alert_warning("No orders yet", "Orders appear here once customers place them.")
        return

    df = pd.DataFrame(rows, columns=["Order ID", "Customer", "Timestamp", "Drug", "Qty", "Unit Price (₹)"])
    df["Line Total (₹)"] = (df["Qty"] * df["Unit Price (₹)"]).round(2)

    metric_cards_row([
        {"icon": "📋", "value": df["Order ID"].nunique(),           "label": "Total Orders",  "color": "#2563EB", "bg": "#EFF6FF"},
        {"icon": "👤", "value": df["Customer"].nunique(),           "label": "Customers",     "color": "#7C3AED", "bg": "#F5F3FF"},
        {"icon": "₹",  "value": f"{df['Line Total (₹)'].sum():,.0f}", "label": "Revenue",   "color": "#059669", "bg": "#ECFDF5"},
    ])
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    search = st.text_input("🔍  Search by customer or order ID")
    if search:
        mask = (df["Customer"].str.contains(search, case=False, na=False) |
                df["Order ID"].str.contains(search, case=False, na=False))
        df = df[mask]
        if df.empty:
            st.info(f"No orders match **'{search}'**.")

    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button("⬇️ Export to CSV", data=df.to_csv(index=False).encode(),
                       file_name="orders_export.csv", mime="text/csv")

    with st.expander("📊 Revenue by Customer"):
        summary = (df.groupby("Customer")["Line Total (₹)"]
                   .sum().reset_index()
                   .rename(columns={"Line Total (₹)": "Total Spent (₹)"})
                   .sort_values("Total Spent (₹)", ascending=False))
        st.dataframe(summary, use_container_width=True, hide_index=True)

    st.divider()
    section_header("🗑️", "Delete Order")
    with st.form("form_delete_order"):
        order_id = st.text_input("Order ID", placeholder="e.g. alice#A1B2C3D4")
        sub      = st.form_submit_button("Delete Order", use_container_width=True)
    if sub:
        if not order_id.strip():
            st.warning("Order ID is required.")
        elif order_delete(order_id.strip()):
            invalidate_orders()
            alert_success("Deleted", f"Order **{order_id}** removed.")
        else:
            alert_danger("Not Found", f"No order with ID **{order_id}**.")


# ---------------------------------------------------------------------------
# About
# ---------------------------------------------------------------------------

def _about_section() -> None:
    section_header("ℹ️", "About")
    st.markdown("""
    <div style="background:var(--secondary-background-color);border-radius:16px;padding:2rem;
                border:1px solid rgba(128, 128, 128, 0.15);
                box-shadow:0 1px 3px rgba(0,0,0,0.05),0 4px 16px rgba(0,0,0,0.06);">
        <h3 style="margin:0 0 0.5rem;color:var(--text-color);">Pharmacy Management System</h3>
        <p style="color:var(--text-color);opacity:0.7;font-size:0.9rem;margin:0 0 1.5rem;">Made by <strong>Himanshu Sharma</strong></p>
        <table style="width:100%;border-collapse:collapse;font-size:0.875rem;">
            <tr style="border-bottom:1px solid rgba(128, 128, 128, 0.15);">
                <td style="padding:0.6rem 0.5rem;color:var(--text-color);opacity:0.7;font-weight:600;width:35%;">Stack</td>
                <td style="padding:0.6rem 0.5rem;color:var(--text-color);">Python · Streamlit · SQLite · Pandas</td>
            </tr>
            <tr style="border-bottom:1px solid rgba(128, 128, 128, 0.15);">
                <td style="padding:0.6rem 0.5rem;color:var(--text-color);opacity:0.7;font-weight:600;">Security</td>
                <td style="padding:0.6rem 0.5rem;color:var(--text-color);">PBKDF2-HMAC-SHA256 · env-var admin credentials · rate limiting</td>
            </tr>
            <tr style="border-bottom:1px solid rgba(128, 128, 128, 0.15);">
                <td style="padding:0.6rem 0.5rem;color:var(--text-color);opacity:0.7;font-weight:600;">Schema</td>
                <td style="padding:0.6rem 0.5rem;color:var(--text-color);">Normalised OrderItems · Atomic transactions · FK enforcement</td>
            </tr>
            <tr style="border-bottom:1px solid rgba(128, 128, 128, 0.15);">
                <td style="padding:0.6rem 0.5rem;color:var(--text-color);opacity:0.7;font-weight:600;">Caching</td>
                <td style="padding:0.6rem 0.5rem;color:var(--text-color);">@st.cache_data (30–120 s TTL) with write-through invalidation</td>
            </tr>
            <tr>
                <td style="padding:0.6rem 0.5rem;color:var(--text-color);opacity:0.7;font-weight:600;">Testing</td>
                <td style="padding:0.6rem 0.5rem;color:var(--text-color);">73 pytest tests · GitHub Actions CI on every push</td>
            </tr>
        </table>
    </div>
    """, unsafe_allow_html=True)
