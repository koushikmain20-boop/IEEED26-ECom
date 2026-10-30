def test_add_and_read_cart(seeded):
    response = seeded.post(
        "/cart/alex/items",
        json={"product_id": 1, "quantity": 2}
    )

    assert response.status_code == 200
    assert response.json()["subtotal_minor"] == 2598

    cart_response = seeded.get("/cart/alex")

    assert cart_response.status_code == 200
    assert cart_response.json()["items"][0]["quantity"] == 2


def test_empty_cart_is_available(seeded):
    response = seeded.get("/cart/new-customer")

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_repeat_add_increments_existing_line(seeded):
    first_response = seeded.post(
        "/cart/alex/items",
        json={"product_id": 1, "quantity": 2}
    )
    assert first_response.status_code == 200

    second_response = seeded.post(
        "/cart/alex/items",
        json={"product_id": 1, "quantity": 1}
    )
    assert second_response.status_code == 200

    cart_response = seeded.get("/cart/alex")
    assert cart_response.status_code == 200

    cart = cart_response.json()

    assert len(cart["items"]) == 1
    assert cart["items"][0]["quantity"] == 3
    assert cart["subtotal_minor"] == 3897


def test_item_quantity_is_limited_per_request(seeded):
    response = seeded.post(
        "/cart/alex/items",
        json={"product_id": 1, "quantity": 100}
    )

    assert response.status_code == 422
