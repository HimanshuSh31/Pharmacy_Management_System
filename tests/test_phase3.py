import pytest
import database
from database import (
    order_place,
    order_view_data,
    order_view_all_data,
    order_update_status,
    contraindications_check,
    customer_add_data,
    drug_add_data
)

@pytest.fixture
def setup_test_data():
    # Add a customer
    customer_add_data("Alice", "hash123", "alice@test.com", "State", "1234567890")
    # Add a prescription-required drug and a general drug
    drug_add_data(
        name="Amoxicillin", expdate="2027-01-01", use="Infection",
        qty=100, drug_id="#AMX", price=15.0, image=None,
        category="Antibiotic", supplier="Sandoz", prescription=1
    )
    drug_add_data(
        name="Multivitamins", expdate="2028-01-01", use="Daily supplement",
        qty=200, drug_id="#MTV", price=8.0, image=None,
        category="Supplement", supplier="Nature's Way", prescription=0
    )
    drug_add_data(
        name="Aspirin", expdate="2027-12-31", use="Pain relief",
        qty=150, drug_id="#ASP", price=5.0, image=None,
        category="Pain Relief", supplier="Bayer", prescription=0
    )

def test_new_columns_in_orders_table():
    """Verify that O_Status, O_Prescription_Path, and O_Rejection_Reason exist in Orders table."""
    conn = database.get_connection()
    c = conn.cursor()
    c.execute("PRAGMA table_info(Orders)")
    cols = {row[1] for row in c.fetchall()}
    assert "O_Status" in cols
    assert "O_Prescription_Path" in cols
    assert "O_Rejection_Reason" in cols

def test_seeding_contraindications():
    """Verify that default contraindications are seeded successfully during create_all_tables."""
    conn = database.get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM Contraindications")
    count = c.fetchone()[0]
    assert count == 3  # Seeded with 3 category combinations

def test_contraindications_check():
    """Verify that contraindications_check correctly identifies conflicting categories."""
    # Antibiotic + Supplement should trigger warning
    warnings = contraindications_check(["Antibiotic", "Supplement"])
    assert len(warnings) == 1
    assert warnings[0]["severity"] == "High"
    assert "antibiotics" in warnings[0]["message"].lower()

    # Pain Relief + Antihistamine should trigger warning
    warnings = contraindications_check(["Antihistamine", "Pain Relief"])
    assert len(warnings) == 1
    assert warnings[0]["severity"] == "Medium"

    # Non-conflicting categories should return no warnings
    warnings = contraindications_check(["Cardiovascular", "Antibiotic"])
    assert len(warnings) == 0

    # Less than two categories should return no warnings
    assert len(contraindications_check(["Antibiotic"])) == 0
    assert len(contraindications_check([])) == 0

def test_order_place_status_without_prescription_drug(setup_test_data):
    """Verify that an order without prescription drugs starts with 'Preparing' status."""
    order_id = "ORD-TEST-1"
    items = [
        {"drug_id": "#MTV", "drug_name": "Multivitamins", "quantity": 2, "unit_price": 8.0}
    ]
    success = order_place("alice@test.com", order_id, items)
    assert success is True

    # View order details
    rows = order_view_data("alice@test.com")
    assert len(rows) == 1
    # Column index 5 is O_Status
    assert rows[0][5] == "Preparing"
    assert rows[0][6] is None  # O_Prescription_Path

def test_order_place_status_with_prescription_drug(setup_test_data):
    """Verify that an order with a prescription drug starts with 'Pending Verification' status."""
    order_id = "ORD-TEST-2"
    items = [
        {"drug_id": "#AMX", "drug_name": "Amoxicillin", "quantity": 1, "unit_price": 15.0}
    ]
    rx_path = "images/prescriptions/ORD-TEST-2_prescription.png"
    success = order_place("alice@test.com", order_id, items, rx_path)
    assert success is True

    rows = order_view_data("alice@test.com")
    assert len(rows) == 1
    assert rows[0][5] == "Pending Verification"
    assert rows[0][6] == rx_path
    assert rows[0][7] is None  # O_Rejection_Reason

def test_order_status_transitions(setup_test_data):
    """Verify that admin can transition order statuses and set rejection reasons."""
    order_id = "ORD-TRANS"
    items = [
        {"drug_id": "#MTV", "drug_name": "Multivitamins", "quantity": 1, "unit_price": 8.0}
    ]
    order_place("alice@test.com", order_id, items)

    # Transition to 'Dispatched'
    assert order_update_status(order_id, "Dispatched") is True
    rows = order_view_data("alice@test.com")
    assert rows[0][5] == "Dispatched"

    # Reject/Cancel order with reason
    assert order_update_status(order_id, "Cancelled", "Prescription name does not match patient") is True
    rows = order_view_data("alice@test.com")
    assert rows[0][5] == "Cancelled"
    assert rows[0][7] == "Prescription name does not match patient"
