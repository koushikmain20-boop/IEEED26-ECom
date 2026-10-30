def add_item(client, customer_id, product_id, quantity):
    return client.post(
        f"/cart/{customer_id}/items",
        json={
            "product_id": product_id,
            "quantity": quantity
        }
    )


def checkout(client, customer_id, key, payment_token="tok", discount_code=None):
    body = {
        "customer_id": customer_id,
        "payment_token": payment_token
    }

    if discount_code is not None:
        body["discount_code"] = discount_code

    return client.post(
        "/checkout",
        headers={"Idempotency-Key": key},
        json=body
    )


def test_checkout(seeded):
    add_response = add_item(seeded, "alex", 1, 2)
    assert add_response.status_code == 200

    response = checkout(seeded, "alex", "order-alex-1")

    assert response.status_code == 200
    assert response.json()["total_minor"] == 2598


def test_declined_payment_does_not_create_order(seeded):
    add_response = add_item(seeded, "alex", 1, 1)
    assert add_response.status_code == 200

    response = checkout(
        seeded, "alex", "decline-1", payment_token="decline"
    )

    assert response.status_code == 402


def test_checkout_requires_key(seeded):
    add_item(seeded, "alex", 1, 1)

    response = seeded.post(
        "/checkout",
        json={"customer_id": "alex", "payment_token": "tok"}
    )

    assert response.status_code == 400


def test_checkout_rejects_overlong_key(seeded):
    add_item(seeded, "alex", 1, 1)

    response = checkout(seeded, "alex", "k" * 121)

    assert response.status_code == 400


def test_checkout_requires_non_empty_cart(seeded):
    response = checkout(seeded, "nobody", "empty-cart-1")

    assert response.status_code == 400


def test_checkout_clears_cart(seeded):
    add_item(seeded, "alex", 1, 1)

    response = checkout(seeded, "alex", "clear-1")

    assert response.status_code == 200
    assert seeded.get("/cart/alex").json()["items"] == []


def test_checkout_decrements_inventory_once(seeded):
    add_item(seeded, "alex", 1, 2)

    response = checkout(seeded, "alex", "inventory-1")

    assert response.status_code == 200
    assert seeded.get("/products/1").json()["inventory"] == 18


def test_declined_payment_leaves_cart_and_inventory_intact(seeded):
    add_item(seeded, "alex", 1, 1)

    response = checkout(
        seeded, "alex", "decline-2", payment_token="decline"
    )

    assert response.status_code == 402
    assert seeded.get("/cart/alex").json()["items"][0]["quantity"] == 1
    assert seeded.get("/products/1").json()["inventory"] == 20

    retry_response = checkout(seeded, "alex", "decline-2")

    assert retry_response.status_code == 200


def test_insufficient_inventory_is_rejected(seeded):
    add_item(seeded, "alex", 1, 21)

    response = checkout(seeded, "alex", "too-many-1")

    assert response.status_code == 409
    assert seeded.get("/products/1").json()["inventory"] == 20
    assert seeded.get("/orders").json() == []


def test_welcome_discount_applies_at_checkout(seeded):
    add_item(seeded, "alex", 1, 2)

    response = checkout(
        seeded, "alex", "discount-1", discount_code="WELCOME10"
    )

    assert response.status_code == 200
    assert response.json()["discount_minor"] == 259
    assert response.json()["total_minor"] == 2339


def test_multi_item_totals(seeded):
    add_item(seeded, "alex", 1, 2)
    add_item(seeded, "alex", 2, 1)

    response = checkout(seeded, "alex", "multi-1")

    assert response.status_code == 200
    assert response.json()["subtotal_minor"] == 4497
    assert response.json()["total_minor"] == 4497


def test_order_lines_snapshot_purchase_details(seeded):
    add_item(seeded, "alex", 1, 2)

    response = checkout(seeded, "alex", "snapshot-1")

    assert response.status_code == 200

    order = response.json()

    assert order["items"] == [
        {
            "sku": "NST-COFFEE",
            "name": "Northstar Coffee",
            "quantity": 2,
            "unit_price_minor": 1299,
        }
    ]
