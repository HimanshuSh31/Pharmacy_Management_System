"""
tests/test_database.py — Unit tests for database.py CRUD operations.

All tests run against a fresh in-memory SQLite database (see conftest.py).
Key scenarios covered:
  - Happy-path insert / read / update / delete for all three entities
  - Duplicate primary-key rejection
  - rowcount=0 → False return for UPDATE/DELETE on non-existent IDs
  - Atomic order_place(): inventory decrements, full rollback on failure
  - Insufficient stock is rejected cleanly (no partial commit)
  - Low-stock query
"""

import pytest
from database import (
    # Customers
    customer_add_data, customer_view_all_data,
    customer_get_by_email, customer_get_password_hash,
    customer_update, customer_delete,
    # Drugs
    drug_add_data, drug_view_all_data,
    drug_update, drug_update_price, drug_delete,
    drug_decrement_qty, drug_get_low_stock,
    drug_update_details,
    LOW_STOCK_THRESHOLD,
    # Orders
    order_place, order_view_data, order_view_all_data, order_delete,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def alice():
    customer_add_data("Alice", "hash_alice", "alice@test.com", "CA", "1111111111")
    return "alice@test.com"


@pytest.fixture
def drug_aspirin():
    drug_add_data("Aspirin", "2026-01-01", "Pain relief", 100, "#ASP", 5.0)
    return "#ASP"


@pytest.fixture
def drug_ibuprofen():
    drug_add_data("Ibuprofen", "2027-06-01", "Anti-inflammatory", 50, "#IBU", 8.0)
    return "#IBU"


# ---------------------------------------------------------------------------
# Customer CRUD
# ---------------------------------------------------------------------------

class TestCustomerCRUD:
    def test_add_customer(self):
        assert customer_add_data(
            "Bob", "hash_bob", "bob@test.com", "NY", "2222222222"
        ) is True

    def test_add_duplicate_email_returns_false(self, alice):
        assert customer_add_data(
            "Alice2", "hash2", "alice@test.com", "TX", "3333333333"
        ) is False

    def test_view_excludes_password(self, alice):
        rows = customer_view_all_data()
        for row in rows:
            assert "hash_alice" not in row, "Password must not appear in view"

    def test_get_by_email(self, alice):
        row = customer_get_by_email("alice@test.com")
        assert row is not None
        assert row[0] == "Alice"

    def test_get_password_hash(self, alice):
        h = customer_get_password_hash("alice@test.com")
        assert h == "hash_alice"

    def test_get_nonexistent_returns_none(self):
        assert customer_get_by_email("ghost@test.com") is None
        assert customer_get_password_hash("ghost@test.com") is None

    def test_update_phone(self, alice):
        assert customer_update("alice@test.com", "9999999999") is True
        row = customer_get_by_email("alice@test.com")
        assert row[3] == "9999999999"

    def test_update_nonexistent_returns_false(self):
        assert customer_update("ghost@test.com", "000") is False

    def test_delete_customer(self, alice):
        success, msg = customer_delete(alice)
        assert success is True
        assert customer_get_by_email(alice) is None

    def test_delete_nonexistent_returns_false(self):
        success, msg = customer_delete("ghost@test.com")
        assert success is False


# ---------------------------------------------------------------------------
# Drug CRUD
# ---------------------------------------------------------------------------

class TestDrugCRUD:
    def test_add_drug(self):
        assert drug_add_data(
            "Paracetamol", "2026-12-01", "Fever", 200, "#PAR", 3.0
        ) is True

    def test_add_duplicate_id_returns_false(self, drug_aspirin):
        assert drug_add_data(
            "Aspirin2", "2026-01-01", "Pain", 50, "#ASP", 4.0
        ) is False

    def test_view_all_data(self, drug_aspirin):
        drugs = drug_view_all_data()
        ids = [d[4] for d in drugs]
        assert "#ASP" in ids

    def test_update_use(self, drug_aspirin):
        assert drug_update("#ASP", "Headache and fever") is True
        drugs = {d[4]: d for d in drug_view_all_data()}
        assert drugs["#ASP"][2] == "Headache and fever"

    def test_update_nonexistent_returns_false(self):
        assert drug_update("#MISSING", "Use") is False

    def test_update_price(self, drug_aspirin):
        assert drug_update_price("#ASP", 7.5) is True
        drugs = {d[4]: d for d in drug_view_all_data()}
        assert drugs["#ASP"][5] == pytest.approx(7.5)

    def test_update_price_nonexistent_returns_false(self):
        assert drug_update_price("#MISSING", 5.0) is False

    def test_delete_drug(self, drug_aspirin):
        success, msg = drug_delete(drug_aspirin)
        assert success is True
        drugs = {d[4]: d for d in drug_view_all_data()}
        assert drug_aspirin not in drugs

    def test_delete_nonexistent_returns_false(self):
        success, msg = drug_delete("#GHOST")
        assert success is False

    def test_decrement_qty(self, drug_aspirin):
        assert drug_decrement_qty("#ASP", 20) is True
        drugs = {d[4]: d for d in drug_view_all_data()}
        assert drugs["#ASP"][3] == 80  # 100 - 20

    def test_decrement_insufficient_stock_returns_false(self, drug_aspirin):
        assert drug_decrement_qty("#ASP", 999) is False
        # Stock must remain unchanged
        drugs = {d[4]: d for d in drug_view_all_data()}
        assert drugs["#ASP"][3] == 100

    def test_decrement_exact_stock_succeeds(self, drug_aspirin):
        assert drug_decrement_qty("#ASP", 100) is True
        drugs = {d[4]: d for d in drug_view_all_data()}
        assert drugs["#ASP"][3] == 0

    def test_low_stock_alert(self):
        drug_add_data("LowDrug", "2026-01-01", "Test", 3, "#LOW", 1.0)
        low = drug_get_low_stock(threshold=LOW_STOCK_THRESHOLD)
        names = [r[0] for r in low]
        assert "LowDrug" in names

    def test_healthy_stock_not_in_alert(self, drug_aspirin):
        low = drug_get_low_stock(threshold=LOW_STOCK_THRESHOLD)
        names = [r[0] for r in low]
        assert "Aspirin" not in names  # qty=100, threshold=10


# ---------------------------------------------------------------------------
# Order CRUD — atomic placement with inventory decrement
# ---------------------------------------------------------------------------

class TestOrderPlacement:
    def test_place_order_succeeds(self, alice, drug_aspirin):
        assert order_place(alice, "ORD-001", [
            {"drug_id": "#ASP", "drug_name": "Aspirin", "quantity": 5, "unit_price": 5.0}
        ]) is True

    def test_place_order_decrements_stock(self, alice, drug_aspirin):
        order_place(alice, "ORD-002", [
            {"drug_id": "#ASP", "drug_name": "Aspirin", "quantity": 10, "unit_price": 5.0}
        ])
        drugs = {d[4]: d for d in drug_view_all_data()}
        assert drugs["#ASP"][3] == 90  # 100 - 10

    def test_place_order_insufficient_stock_returns_false(self, alice, drug_aspirin):
        assert order_place(alice, "ORD-003", [
            {"drug_id": "#ASP", "drug_name": "Aspirin", "quantity": 999, "unit_price": 5.0}
        ]) is False

    def test_place_order_full_rollback_on_failure(self, alice, drug_aspirin, drug_ibuprofen):
        """
        If any item in the order fails (e.g. missing drug), the entire
        transaction must roll back — no stock should be decremented.
        """
        asp_before = [d for d in drug_view_all_data() if d[4] == "#ASP"][0][3]
        ibu_before = [d for d in drug_view_all_data() if d[4] == "#IBU"][0][3]

        result = order_place(alice, "ORD-004", [
            {"drug_id": "#ASP",     "drug_name": "Aspirin",   "quantity": 5,  "unit_price": 5.0},
            {"drug_id": "#MISSING", "drug_name": "GhostDrug", "quantity": 1,  "unit_price": 0.0},
        ])

        assert result is False

        asp_after = [d for d in drug_view_all_data() if d[4] == "#ASP"][0][3]
        ibu_after = [d for d in drug_view_all_data() if d[4] == "#IBU"][0][3]
        assert asp_after == asp_before, "Aspirin stock must not change after rollback"
        assert ibu_after == ibu_before, "Ibuprofen stock must not change after rollback"

    def test_place_multi_item_order(self, alice, drug_aspirin, drug_ibuprofen):
        assert order_place(alice, "ORD-005", [
            {"drug_id": "#ASP", "drug_name": "Aspirin",   "quantity": 3, "unit_price": 5.0},
            {"drug_id": "#IBU", "drug_name": "Ibuprofen", "quantity": 2, "unit_price": 8.0},
        ]) is True
        drugs = {d[4]: d for d in drug_view_all_data()}
        assert drugs["#ASP"][3] == 97   # 100 - 3
        assert drugs["#IBU"][3] == 48   # 50  - 2

    def test_duplicate_order_id_returns_false(self, alice, drug_aspirin):
        order_place(alice, "ORD-006", [
            {"drug_id": "#ASP", "drug_name": "Aspirin", "quantity": 1, "unit_price": 5.0}
        ])
        assert order_place(alice, "ORD-006", [
            {"drug_id": "#ASP", "drug_name": "Aspirin", "quantity": 1, "unit_price": 5.0}
        ]) is False


class TestOrderViews:
    def test_view_customer_orders(self, drug_aspirin):
        customer_add_data("Bob", "hash", "bob@test.com", "State", "111")
        order_place("bob@test.com", "ORD-BOB-1", [
            {"drug_id": "#ASP", "drug_name": "Aspirin", "quantity": 2, "unit_price": 5.0}
        ])
        rows = order_view_data("bob@test.com")
        assert len(rows) == 1
        assert rows[0][2] == "Aspirin"

    def test_view_only_own_orders(self, alice, drug_aspirin):
        customer_add_data("Charlie", "hash", "charlie@test.com", "State", "222")
        order_place(alice, "ORD-A1", [
            {"drug_id": "#ASP", "drug_name": "Aspirin", "quantity": 1, "unit_price": 5.0}
        ])
        order_place("charlie@test.com", "ORD-C1", [
            {"drug_id": "#ASP", "drug_name": "Aspirin", "quantity": 1, "unit_price": 5.0}
        ])
        alice_rows = order_view_data(alice)
        assert all(row[0].startswith("ORD-A") for row in alice_rows)

    def test_view_all_orders(self, alice, drug_aspirin, drug_ibuprofen):
        customer_add_data("Bob", "hash", "bob@test.com", "State", "111")
        order_place(alice, "ORD-ALL-1", [
            {"drug_id": "#ASP", "drug_name": "Aspirin", "quantity": 1, "unit_price": 5.0}
        ])
        order_place("bob@test.com", "ORD-ALL-2", [
            {"drug_id": "#IBU", "drug_name": "Ibuprofen", "quantity": 2, "unit_price": 8.0}
        ])
        rows = order_view_all_data()
        order_ids = {r[0] for r in rows}
        assert "ORD-ALL-1" in order_ids
        assert "ORD-ALL-2" in order_ids


class TestOrderDelete:
    def test_delete_order(self, alice, drug_aspirin):
        order_place(alice, "ORD-DEL-1", [
            {"drug_id": "#ASP", "drug_name": "Aspirin", "quantity": 1, "unit_price": 5.0}
        ])
        assert order_delete("ORD-DEL-1") is True
        rows = order_view_all_data()
        order_ids = [r[0] for r in rows]
        assert "ORD-DEL-1" not in order_ids

    def test_delete_nonexistent_order_returns_false(self):
        assert order_delete("ORD-GHOST") is False

    def test_delete_cascades_to_items(self, alice, drug_aspirin):
        """Deleting an order must also remove its OrderItems (CASCADE)."""
        order_place(alice, "ORD-CASCADE", [
            {"drug_id": "#ASP", "drug_name": "Aspirin", "quantity": 1, "unit_price": 5.0}
        ])
        order_delete("ORD-CASCADE")
        rows = order_view_all_data()
        assert all(r[0] != "ORD-CASCADE" for r in rows)


class TestDatabaseImprovements:
    def test_drug_update_details(self, drug_aspirin):
        assert drug_update_details(drug_aspirin, "New usage", 12.0, 50) is True
        drugs = {d[4]: d for d in drug_view_all_data()}
        # Columns: (Name, ExpDate, Use, Qty, id, Price, Image)
        assert drugs[drug_aspirin][2] == "New usage"
        assert drugs[drug_aspirin][3] == 150  # 100 + 50
        assert drugs[drug_aspirin][5] == 12.0

    def test_drug_delete_constraint_failure(self, alice, drug_aspirin):
        order_place(alice, "ORD-CONSTRAINT-D", [
            {"drug_id": drug_aspirin, "drug_name": "Aspirin", "quantity": 1, "unit_price": 5.0}
        ])
        success, msg = drug_delete(drug_aspirin)
        assert success is False
        assert "Cannot delete drug" in msg

    def test_customer_delete_constraint_failure(self, alice, drug_aspirin):
        order_place(alice, "ORD-CONSTRAINT-C", [
            {"drug_id": drug_aspirin, "drug_name": "Aspirin", "quantity": 1, "unit_price": 5.0}
        ])
        success, msg = customer_delete(alice)
        assert success is False
        assert "Cannot delete customer" in msg

