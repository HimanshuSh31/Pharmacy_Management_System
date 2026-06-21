"""
customer_ui.py — Customer-facing dashboard: medicine card grid, order placement.

UI upgrade:
  - 3-column medicine card grid with styled card header (HTML) + native slider
  - Real-time order total banner
  - Order history with per-order totals in expander
  - uuid4 order IDs
  - Atomic order_place() with full rollback on stock failure
"""

import os
import uuid
import logging
from typing import Optional

import streamlit as st
import pandas as pd
from PIL import Image

from database import drug_view_all_data, order_view_data, order_place
from styles import (
    medicine_card_header, order_total_banner,
    alert_success, alert_danger, alert_warning,
    page_header, section_header,
)

logger      = logging.getLogger(__name__)
IMAGES_DIR  = "images"
COLS        = 3           # medicine cards per row


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_image(filename: Optional[str]):
    if not filename:
        return None
    path = os.path.join(IMAGES_DIR, filename)
    try:
        return Image.open(path)
    except Exception:
        return None


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
    section_header("📦", "Your Order History")

    with st.expander("View past orders", expanded=False):
        rows = order_view_data(email)
        if not rows:
            st.markdown(
                "<p style='color:#64748B; font-size:0.875rem; padding:0.5rem 0;'>"
                "You haven't placed any orders yet.</p>",
                unsafe_allow_html=True,
            )
            return

        df = pd.DataFrame(
            rows,
            columns=["Order ID", "Date & Time", "Drug", "Qty", "Unit Price (₹)"]
        )
        df["Line Total (₹)"] = (df["Qty"] * df["Unit Price (₹)"]).round(2)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Per-order total
        totals = (
            df.groupby("Order ID")["Line Total (₹)"]
            .sum().reset_index()
            .rename(columns={"Line Total (₹)": "Order Total (₹)"})
            .sort_values("Order Total (₹)", ascending=False)
        )
        st.markdown("**Order totals:**")
        st.dataframe(totals, use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Medicine catalog — card grid
# ---------------------------------------------------------------------------

def _medicine_catalog(username: str, email: str) -> None:
    section_header("🛒", "Available Medicines")

    drugs = drug_view_all_data()
    # (D_Name, D_ExpDate, D_Use, D_Qty, D_id, D_Price, D_Image)

    if not drugs:
        alert_warning("No medicines available",
                      "The inventory is currently empty. Please check back later.")
        return

    quantities: dict[str, int] = {}

    # ── Card grid ────────────────────────────────────────────────────────────
    for row_start in range(0, len(drugs), COLS):
        row_drugs = drugs[row_start: row_start + COLS]
        cols      = st.columns(COLS, gap="medium")

        for col, drug in zip(cols, row_drugs):
            d_name, d_expiry, d_use, d_qty, d_id, d_price, d_image = drug
            with col:
                # ── Visual card header (HTML) ────────────────────────────
                medicine_card_header(
                    name   = d_name,
                    use    = d_use,
                    price  = float(d_price),
                    expiry = str(d_expiry),
                    qty    = int(d_qty) if d_qty else 0,
                )

                # ── Drug image (if available) ────────────────────────────
                img = _load_image(d_image)
                if img:
                    st.image(img, use_container_width=True)

                # ── Native quantity slider ───────────────────────────────
                max_qty = min(int(d_qty or 0), 20)
                quantities[d_id] = st.slider(
                    label     = f"Qty — {d_name}",
                    min_value = 0,
                    max_value = max(max_qty, 1),
                    value     = 0,
                    key       = f"qty_{d_id}",
                    label_visibility = "collapsed",
                )

                # Show selected quantity below slider
                if quantities[d_id] > 0:
                    subtotal = quantities[d_id] * float(d_price)
                    st.markdown(
                        f"<div style='text-align:center; font-size:0.78rem; "
                        f"color:#2563EB; font-weight:600; margin-top:0.2rem;'>"
                        f"{quantities[d_id]} × ₹{float(d_price):.2f}"
                        f" = ₹{subtotal:.2f}</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        "<div style='text-align:center; font-size:0.75rem; "
                        "color:#94A3B8; margin-top:0.2rem;'>Slide to select qty</div>",
                        unsafe_allow_html=True,
                    )

        # Spacer between rows
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    # ── Order total banner ───────────────────────────────────────────────────
    selected_drugs = [d for d in drugs if quantities.get(d[4], 0) > 0]

    if selected_drugs:
        total = sum(float(d[5]) * quantities[d[4]] for d in selected_drugs)
        order_total_banner(len(selected_drugs), total)

    # ── Place Order button ───────────────────────────────────────────────────
    _, btn_col, _ = st.columns([1, 2, 1])
    with btn_col:
        place = st.button(
            "🛒  Place Order" if selected_drugs else "Select medicines above",
            use_container_width=True,
            disabled=not bool(selected_drugs),
        )

    if place:
        if not selected_drugs:
            st.warning("Please select at least one medicine.")
            return

        order_id = f"{username}#{uuid.uuid4().hex[:8].upper()}"
        items = [
            {
                "drug_id":    d[4],
                "drug_name":  d[0],
                "quantity":   quantities[d[4]],
                "unit_price": float(d[5]),
            }
            for d in selected_drugs
        ]

        success = order_place(email, order_id, items)
        if success:
            grand_total = sum(it["quantity"] * it["unit_price"] for it in items)
            alert_success(
                "Order Placed Successfully! 🎉",
                f"**Order ID:** `{order_id}`  ·  **Total: ₹ {grand_total:,.2f}**  ·  "
                f"{len(items)} item(s) dispatched.",
            )
            st.balloons()
        else:
            alert_danger(
                "Order Failed",
                "One or more items may be out of stock. "
                "Adjust quantities and try again.",
            )
