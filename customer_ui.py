"""
customer_ui.py — Customer-facing dashboard: medicine card grid, order placement.

Round-4 improvements:
  - Uses data.py (@st.cache_data) for drug reads
  - Updated drug tuple unpacking (10 columns: +category, supplier, prescription)
  - Category filter tabs above the card grid
  - Prescription badge on card (Rx Required)
  - Expired / out-of-stock / expiring-soon states
  - Order confirmation step before placing
  - CSV download of order history
"""

import os
import uuid
import logging
from datetime import date
from typing import Optional

import streamlit as st
import pandas as pd
from PIL import Image

from database import order_place
from data import get_customer_orders, invalidate_orders
from styles import (
    medicine_card_header, order_total_banner,
    alert_success, alert_danger, alert_warning,
    page_header, section_header,
)

logger      = logging.getLogger(__name__)
IMAGES_DIR  = "images"
COLS        = 3


def _save_uploaded_prescription(uploaded_file, order_id: str) -> str:
    import os
    rx_dir = os.path.join(IMAGES_DIR, "prescriptions")
    os.makedirs(rx_dir, exist_ok=True)
    ext = os.path.splitext(uploaded_file.name)[1]
    filename = f"{order_id.replace('#', '_')}_prescription{ext}"
    filepath = os.path.join(rx_dir, filename)
    with open(filepath, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return filepath


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_image(filename: Optional[str]):
    if not filename:
        return None
    try:
        return Image.open(os.path.join(IMAGES_DIR, filename))
    except Exception:
        return None


def _days_to_expiry(expdate_str: str) -> int:
    try:
        return (date.fromisoformat(str(expdate_str)) - date.today()).days
    except (ValueError, TypeError):
        return 9999


def _is_expired(expdate_str: str) -> bool:
    return _days_to_expiry(expdate_str) < 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def show_customer_dashboard(username: str, email: str) -> None:
    page_header(f"👋 Hello, {username}!", "Browse medicines and place your order below.")
    _order_history(email)
    st.divider()
    _medicine_catalog(username, email)


# ---------------------------------------------------------------------------
# Order history
# ---------------------------------------------------------------------------

def _order_history(email: str) -> None:
    section_header("📦", "Your Order History & Status")
    with st.expander("View past orders & progress", expanded=False):
        rows = get_customer_orders(email)
        if not rows:
            st.markdown("<p style='color:#64748B;font-size:0.875rem;padding:0.5rem 0;'>"
                        "You haven't placed any orders yet.</p>", unsafe_allow_html=True)
            return

        df = pd.DataFrame(rows, columns=[
            "Order ID", "Date & Time", "Drug", "Qty", "Unit Price (₹)",
            "Status", "Prescription Path", "Rejection Reason"
        ])
        df["Line Total (₹)"] = (df["Qty"] * df["Unit Price (₹)"]).round(2)

        st.download_button("⬇️ Download History (CSV)", data=df.to_csv(index=False).encode(),
                           file_name="my_orders.csv", mime="text/csv")
        st.write("")

        unique_orders = df["Order ID"].unique()
        for oid in unique_orders:
            order_items = df[df["Order ID"] == oid]
            first_row = order_items.iloc[0]
            status = first_row["Status"]
            timestamp = first_row["Date & Time"]
            rejection = first_row["Rejection Reason"]
            total_price = order_items["Line Total (₹)"].sum()

            status_colors = {
                "Pending Verification": ("rgba(217, 119, 6, 0.15)", "#D97706", "⏳"),
                "Preparing": ("rgba(37, 99, 235, 0.15)", "#2563EB", "📦"),
                "Dispatched": ("rgba(234, 88, 12, 0.15)", "#EA580C", "🚚"),
                "Delivered": ("rgba(22, 163, 74, 0.15)", "#16A34A", "✅"),
                "Cancelled": ("rgba(220, 38, 38, 0.15)", "#DC2626", "❌")
            }
            bg, fg, icon = status_colors.get(status, ("rgba(71, 85, 105, 0.15)", "#475569", "📋"))

            st.markdown(f"""
            <div style="
                background: var(--secondary-background-color);
                border-radius: 12px;
                padding: 1rem 1.25rem;
                margin-bottom: 0.75rem;
                border: 1px solid rgba(128, 128, 128, 0.15);
                display: flex;
                flex-wrap: wrap;
                justify-content: space-between;
                align-items: center;
                gap: 0.5rem;
            ">
                <div>
                    <span style="font-weight: 700; color: var(--text-color); font-size: 0.95rem;">Order {oid}</span>
                    <div style="font-size: 0.75rem; color: var(--text-color); opacity: 0.6; margin-top: 0.15rem;">
                        📅 {timestamp}
                    </div>
                </div>
                <div style="display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap;">
                    <span style="font-weight: 800; color: var(--text-color); font-size: 1rem;">₹ {total_price:,.2f}</span>
                    <span style="
                        background: {bg};
                        color: {fg};
                        font-weight: 700;
                        font-size: 0.74rem;
                        padding: 0.25rem 0.65rem;
                        border-radius: 20px;
                        display: inline-flex;
                        align-items: center;
                        gap: 0.25rem;
                    ">{icon} {status}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            with st.container():
                item_details = []
                for _, item in order_items.iterrows():
                    item_details.append(f"· {item['Drug']} × {item['Qty']} (₹ {item['Unit Price (₹)']:.2f} each)")
                st.markdown("\n".join(item_details))

                if status == "Cancelled" and rejection:
                    st.markdown(f"""
                    <div style="
                        background: rgba(220, 38, 38, 0.08);
                        border-left: 3px solid #DC2626;
                        padding: 0.5rem 0.75rem;
                        border-radius: 6px;
                        font-size: 0.8rem;
                        color: #DC2626;
                        margin-top: 0.4rem;
                        margin-bottom: 0.75rem;
                    ">
                        <strong>Reason for cancellation:</strong> {rejection}
                    </div>
                    """, unsafe_allow_html=True)
                st.write("")



# ---------------------------------------------------------------------------
# Medicine catalog
# ---------------------------------------------------------------------------

def show_customer_dashboard(username: str, email: str) -> None:
    page_header(f"👋 Hello, {username}!", "Browse medicines and place your order below.")
    _order_history(email)
    st.divider()
    _medicine_catalog(username, email)


def _medicine_catalog(username: str, email: str) -> None:
    from data import get_all_drugs, get_drug_categories
    section_header("🛒", "Available Medicines")

    drugs = get_all_drugs()
    # Columns: D_Name(0), D_ExpDate(1), D_Use(2), D_Qty(3), D_id(4),
    #          D_Price(5), D_Image(6), D_Category(7), D_Supplier(8), D_Prescription(9)

    if not drugs:
        alert_warning("No medicines available", "Inventory is currently empty. Check back later.")
        return

    # ── Search + Category filter ──────────────────────────────────────────
    f1, f2 = st.columns([2, 1])
    with f1:
        search = st.text_input("🔍  Search medicines", placeholder="e.g. Aspirin, Ibuprofen…")
    with f2:
        categories = ["All"] + sorted({d[7] for d in drugs if d[7]})
        cat_filter = st.selectbox("Category", categories)

    if search:
        drugs = [d for d in drugs
                 if search.lower() in d[0].lower() or search.lower() in (d[2] or "").lower()]
    if cat_filter != "All":
        drugs = [d for d in drugs if d[7] == cat_filter]

    if not drugs:
        st.info(f"No medicines match your filters. Try adjusting the search or category.")
        return

    quantities: dict = {}

    # ── Card grid ─────────────────────────────────────────────────────────
    for row_start in range(0, len(drugs), COLS):
        row_drugs = drugs[row_start: row_start + COLS]
        cols      = st.columns(COLS, gap="medium")

        for col, drug in zip(cols, row_drugs):
            (d_name, d_expiry, d_use, d_qty, d_id,
             d_price, d_image, d_category, d_supplier, d_prescription) = drug

            expired      = _is_expired(d_expiry)
            days_left    = _days_to_expiry(d_expiry)
            out_of_stock = int(d_qty or 0) == 0

            with col:
                if expired:
                    st.markdown(f"""
                    <div style="background:rgba(239, 68, 68, 0.1);border:2px solid #EF4444;border-radius:16px;
                                padding:1.25rem;margin-bottom:0.25rem;opacity:0.75;">
                        <div style="float:right;background:#EF4444;color:white;font-size:0.68rem;
                                    font-weight:700;padding:0.2rem 0.5rem;border-radius:20px;">EXPIRED</div>
                        <div style="font-size:1rem;font-weight:700;color:var(--text-color);margin-bottom:0.3rem;">
                            💊 {d_name}</div>
                        <div style="font-size:0.78rem;color:#EF4444;">Expired: {d_expiry}</div>
                    </div>""", unsafe_allow_html=True)
                    quantities[d_id] = 0
                    continue

                medicine_card_header(
                    name   = d_name,
                    use    = d_use,
                    price  = float(d_price),
                    expiry = str(d_expiry),
                    qty    = int(d_qty or 0),
                )

                # ── Badges row ─────────────────────────────────────────
                badges = ""
                if d_prescription and int(d_prescription):
                    badges += ("<span style='background:#FEF3C7;color:#92400E;font-size:0.72rem;"
                               "font-weight:700;padding:0.22rem 0.6rem;border-radius:20px;"
                               "border:1px solid #FDE68A;'>Rx Prescription</span> ")
                if d_category and d_category != "General":
                    badges += (f"<span style='background:#EFF6FF;color:#1D4ED8;font-size:0.72rem;"
                               f"font-weight:600;padding:0.22rem 0.6rem;border-radius:20px;"
                               f"border:1px solid #BFDBFE;'>{d_category}</span> ")
                if badges:
                    st.markdown(f"<div style='margin-bottom:0.4rem;display:flex;flex-wrap:wrap;gap:0.35rem;'>{badges}</div>",
                                unsafe_allow_html=True)

                if 0 <= days_left <= 30:
                    st.markdown(
                        f"<div style='background:#FEF3C7;border:1px solid #FDE68A;border-radius:8px;"
                        f"padding:0.3rem 0.7rem;font-size:0.75rem;font-weight:600;color:#92400E;"
                        f"margin-bottom:0.3rem;'>⏰ Expiring in {days_left} day{'s' if days_left != 1 else ''}</div>",
                        unsafe_allow_html=True)

                img = _load_image(d_image)
                if img:
                    st.image(img, use_container_width=True)

                max_qty = min(int(d_qty or 0), 20)
                if out_of_stock:
                    st.markdown("<div style='text-align:center;font-size:0.8rem;color:#EF4444;"
                                "font-weight:600;padding:0.5rem 0;'>❌ Out of stock</div>",
                                unsafe_allow_html=True)
                    quantities[d_id] = 0
                else:
                    quantities[d_id] = st.slider(
                        f"Qty — {d_name}", min_value=0, max_value=max_qty,
                        value=0, key=f"qty_{d_id}", label_visibility="collapsed")
                    if quantities[d_id] > 0:
                        subtotal = quantities[d_id] * float(d_price)
                        st.markdown(
                            f"<div style='text-align:center;font-size:0.78rem;color:#2563EB;"
                            f"font-weight:600;margin-top:0.2rem;'>"
                            f"{quantities[d_id]} × ₹{float(d_price):.2f} = ₹{subtotal:.2f}</div>",
                            unsafe_allow_html=True)
                    else:
                        st.markdown("<div style='text-align:center;font-size:0.75rem;"
                                    "color:#94A3B8;margin-top:0.2rem;'>Slide to select qty</div>",
                                    unsafe_allow_html=True)

        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    # ── Order total banner ─────────────────────────────────────────────────
    selected_drugs = [d for d in drugs if quantities.get(d[4], 0) > 0]
    if selected_drugs:
        total = sum(float(d[5]) * quantities[d[4]] for d in selected_drugs)
        order_total_banner(len(selected_drugs), total)

    # ── Confirmation step ──────────────────────────────────────────────────
    if "confirm_order" not in st.session_state:
        st.session_state.confirm_order = False

    _, btn_col, _ = st.columns([1, 2, 1])
    with btn_col:
        if not st.session_state.confirm_order:
            review = st.button(
                "🛒  Review Order" if selected_drugs else "Select medicines above",
                use_container_width=True, disabled=not bool(selected_drugs))
            if review and selected_drugs:
                st.session_state.confirm_order = True
                st.rerun()
        else:
            # ── Contraindication warnings ──
            categories = list({d[7] for d in selected_drugs if d[7]})
            from database import contraindications_check
            warnings = contraindications_check(categories)
            if warnings:
                for w in warnings:
                    alert_warning(
                        f"💊 Drug Interaction Alert ({w['severity']} Severity)",
                        w['message']
                    )

            # ── Prescription upload ──
            needs_prescription = any(int(d[9] or 0) == 1 for d in selected_drugs)
            uploaded_rx = None
            if needs_prescription:
                alert_warning(
                    "📋 Prescription Required",
                    "One or more items in your cart require a valid medical prescription. Please upload it below."
                )
                uploaded_rx = st.file_uploader(
                    "Upload Prescription (PDF, PNG, JPG, JPEG)",
                    type=["pdf", "png", "jpg", "jpeg"],
                    key="cart_rx_uploader"
                )

            grand_total = sum(float(d[5]) * quantities[d[4]] for d in selected_drugs)
            st.markdown("""<div style="background:var(--secondary-background-color);border:2px solid #2563EB;
                            border-radius:16px;padding:1.5rem;margin-top:0.5rem;">
                            <h4 style="margin:0 0 1rem;color:var(--text-color);">📋 Order Summary</h4>""",
                        unsafe_allow_html=True)
            for drug in selected_drugs:
                qty  = quantities[drug[4]]
                line = qty * float(drug[5])
                st.markdown(
                    f"<div style='display:flex;justify-content:space-between;"
                    f"font-size:0.875rem;color:var(--text-color);opacity:0.85;padding:0.3rem 0;'>"
                    f"<span>💊 {drug[0]} × {qty}</span>"
                    f"<span style='font-weight:600;'>₹ {line:.2f}</span></div>",
                    unsafe_allow_html=True)
            st.markdown(
                f"<div style='border-top:2px solid rgba(128, 128, 128, 0.15);margin-top:0.75rem;"
                f"padding-top:0.75rem;display:flex;justify-content:space-between;"
                f"font-size:1rem;font-weight:800;color:var(--text-color);'>"
                f"<span>Total</span><span>₹ {grand_total:,.2f}</span></div></div>",
                unsafe_allow_html=True)

            if needs_prescription and not uploaded_rx:
                st.info("⚠️ Please upload your prescription above to enable order confirmation.")

            confirm_disabled = needs_prescription and not uploaded_rx

            c_confirm, c_cancel = st.columns(2)
            with c_confirm:
                if st.button("✅  Confirm Order", use_container_width=True, type="primary", disabled=confirm_disabled):
                    order_id = f"{username}#{uuid.uuid4().hex[:8].upper()}"
                    items = [{"drug_id": d[4], "drug_name": d[0],
                              "quantity": quantities[d[4]], "unit_price": float(d[5])}
                             for d in selected_drugs]

                    # Save prescription if uploaded
                    rx_path = None
                    if needs_prescription and uploaded_rx:
                        rx_path = _save_uploaded_prescription(uploaded_rx, order_id)

                    success = order_place(email, order_id, items, rx_path)
                    st.session_state.confirm_order = False
                    if success:
                        invalidate_orders()
                        if rx_path:
                            alert_success("Order Placed! ⏳",
                                          f"**Order ID:** `{order_id}`  ·  **Total: ₹ {grand_total:,.2f}**  ·  "
                                          "Pending prescription verification by a pharmacist.")
                        else:
                            alert_success("Order Placed! 🎉",
                                          f"**Order ID:** `{order_id}`  ·  **Total: ₹ {grand_total:,.2f}**  ·  "
                                          "Your order is being prepared.")
                        st.balloons()
                    else:
                        alert_danger("Order Failed",
                                     "One or more items may be out of stock. Adjust quantities and try again.")
            with c_cancel:
                if st.button("✖  Cancel", use_container_width=True):
                    st.session_state.confirm_order = False
                    st.rerun()
