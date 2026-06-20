"""
customer_ui.py — Customer-facing UI for the Pharmacy Management System.

Round-2 improvements:
  - uuid4 for order IDs — zero collision probability
  - order_place() used for atomic order placement + inventory decrement
  - Drug prices displayed; running order total shown before confirming
  - Images loaded from D_Image column (drug-specific), not sort-index guessing
  - Order history shows normalised rows from OrderItems join
"""

import os
import uuid
import logging
from typing import Optional

import streamlit as st
import pandas as pd
from PIL import Image

from database import drug_view_all_data, order_view_data, order_place

logger = logging.getLogger(__name__)

_IMAGES_DIR = "images"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_drug_image(filename: Optional[str]):
    """
    Open a PIL Image given a *filename* inside images/.
    Returns None on any error (missing file, bad format, etc.).
    """
    if not filename:
        return None
    path = os.path.join(_IMAGES_DIR, filename)
    try:
        return Image.open(path)
    except Exception as exc:
        logger.warning("Could not open image '%s': %s", path, exc)
        return None


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def show_customer_dashboard(username: str, email: str) -> None:
    st.title("💊 Welcome to Pharmacy Store")
    st.markdown(f"Hello, **{username}**! 👋")
    st.divider()

    _show_order_history(email)
    st.divider()
    _show_drug_catalog(username, email)


# ---------------------------------------------------------------------------
# Order history
# ---------------------------------------------------------------------------

def _show_order_history(email: str) -> None:
    st.subheader("📦 Your Order History")
    rows = order_view_data(email)

    with st.expander("View past orders"):
        if not rows:
            st.info("You haven't placed any orders yet.")
            return

        df = pd.DataFrame(
            rows,
            columns=["Order ID", "Date & Time", "Drug", "Qty", "Unit Price (₹)"]
        )
        df["Line Total (₹)"] = df["Qty"] * df["Unit Price (₹)"]
        st.dataframe(df, use_container_width=True)

        # Per-order totals
        totals = (
            df.groupby("Order ID")["Line Total (₹)"]
            .sum()
            .reset_index()
            .rename(columns={"Line Total (₹)": "Order Total (₹)"})
        )
        st.caption("**Order totals:**")
        st.dataframe(totals, use_container_width=True)


# ---------------------------------------------------------------------------
# Drug catalogue — dynamic loop, prices shown, uuid4 order IDs
# ---------------------------------------------------------------------------

def _show_drug_catalog(username: str, email: str) -> None:
    st.subheader("🛒 Available Medicines")

    drugs = drug_view_all_data()
    # Columns: (D_Name, D_ExpDate, D_Use, D_Qty, D_id, D_Price, D_Image)
    if not drugs:
        st.warning("No medicines are available in the inventory at the moment.")
        return

    quantities: dict[str, int] = {}

    for i, drug in enumerate(drugs):
        d_name, d_expdate, d_use, d_qty, d_id, d_price, d_image = drug

        with st.container():
            col_img, col_info = st.columns([1, 3])

            # ---- Image — loaded from the D_Image column (drug-specific) ----
            with col_img:
                img = _load_drug_image(d_image)
                if img:
                    st.image(img, width=130)
                else:
                    st.markdown("💊", unsafe_allow_html=False)

            # ---- Drug info --------------------------------------------------
            with col_info:
                st.markdown(f"### {d_name}")

                col_price, col_exp, col_stock = st.columns(3)
                col_price.metric("Price", f"₹ {float(d_price):.2f}")
                col_exp.caption(f"⏳ Expires: {d_expdate}")
                col_stock.caption(f"📦 In stock: {d_qty}")

                st.info(f"📌 **When to use:** {d_use}")

                if d_qty <= 0:
                    st.error("❌ Out of stock")
                    quantities[d_id] = 0
                else:
                    try:
                        max_qty = min(int(d_qty), 10)
                    except (ValueError, TypeError):
                        max_qty = 5

                    quantities[d_id] = st.slider(
                        "Quantity",
                        min_value=0,
                        max_value=max_qty,
                        value=0,
                        key=f"qty_{d_id}_{i}",
                    )

        st.divider()

    # ---- Running order total -----------------------------------------------
    selected_drugs = [
        drug for drug in drugs if quantities.get(drug[4], 0) > 0
    ]
    if selected_drugs:
        total = sum(
            float(drug[5]) * quantities[drug[4]] for drug in selected_drugs
        )
        st.info(
            f"🛒 **{len(selected_drugs)} item(s) selected** — "
            f"Estimated total: **₹ {total:.2f}**"
        )

    # ---- Place Order button ------------------------------------------------
    if st.button("🛒 Place Order", type="primary"):
        if not selected_drugs:
            st.warning("Please select at least one medicine before ordering.")
            return

        order_id = f"{username.replace(' ', '')}#{uuid.uuid4().hex[:8].upper()}"
        items = [
            {
                "drug_id":    drug[4],
                "drug_name":  drug[0],
                "quantity":   quantities[drug[4]],
                "unit_price": float(drug[5]),
            }
            for drug in selected_drugs
        ]

        success = order_place(email, order_id, items)
        if success:
            grand_total = sum(
                it["quantity"] * it["unit_price"] for it in items
            )
            st.success(
                f"✅ Order placed!  \n"
                f"**Order ID:** `{order_id}`  \n"
                f"**Total: ₹ {grand_total:.2f}**"
            )
            st.balloons()
            st.rerun()
        else:
            st.error(
                "❌ Order failed — one or more items may be out of stock. "
                "Please adjust your quantities and try again."
            )
