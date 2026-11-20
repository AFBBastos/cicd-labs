"""Tests d'API — POINT DE DÉPART (Atelier 1, puis Atelier 9)."""

from decimal import Decimal
import os
import httpx
import pytest

pytestmark = pytest.mark.api


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_liste_produits(client):
    r = client.get("/products")
    assert r.status_code == 200
    assert {"mug", "tshirt"} <= {p["id"] for p in r.json()}

# ----------------------------------------------------------------------
# Atelier 9 : /products/{id} (200, 404), /cart/quote (200, 404, 422), /orders (201, 422), GET /orders/{id}
# ----------------------------------------------------------------------

def _expected_quote(client, items: list[dict], coupon: str | None = None) -> dict:
    """Calcule le total attendu à partir du catalogue et des règles de pricing."""
    subtotal = Decimal("0.00")
    lines = []
    for item in items:
        prod = client.get(f"/products/{item['product_id']}").json()
        unit = Decimal(prod["price"])
        qty = item["qty"]
        gross = unit * qty
        if qty >= 10:
            gross = gross * Decimal("0.95")
        line_total = gross.quantize(Decimal("0.01"))
        subtotal += line_total
        lines.append((qty, unit, line_total))

    subtotal = subtotal.quantize(Decimal("0.01"))
    discount = Decimal("0.00")
    code = coupon.strip().upper() if coupon else None
    if code == "WELCOME10" and subtotal >= Decimal("20.00"):
        discount = (subtotal * Decimal("0.10")).quantize(Decimal("0.01"))
    elif code == "FIXED5" and subtotal >= Decimal("30.00"):
        discount = Decimal("5.00")

    after = subtotal - discount
    if not items:
        shipping = Decimal("0.00")
    elif code == "FREESHIP" or after >= Decimal("50.00"):
        shipping = Decimal("0.00")
    else:
        shipping = Decimal("4.90")

    total = (after + shipping).quantize(Decimal("0.01"))
    return {
        "subtotal": f"{subtotal:.2f}",
        "discount": f"{discount:.2f}",
        "shipping": f"{shipping:.2f}",
        "total": f"{total:.2f}",
    }


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_liste_produits(client):
    r = client.get("/products")
    assert r.status_code == 200
    assert {"mug", "tshirt"} <= {p["id"] for p in r.json()}


def test_product_by_id_200(client):
    r = client.get("/products/mug")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == "mug"
    assert "price" in data
    assert "stock" in data


def test_product_by_id_404(client):
    r = client.get("/products/produit-inexistant")
    assert r.status_code == 404


def test_cart_quote_200_verifies_total(client):
    items = [{"product_id": "mug", "qty": 2}]
    r = client.post("/cart/quote", json={"items": items, "coupon": "WELCOME10"})
    assert r.status_code == 200
    body = r.json()
    expected = _expected_quote(client, items, coupon="WELCOME10")
    assert body["subtotal"] == expected["subtotal"]
    assert body["discount"] == expected["discount"]
    assert body["shipping"] == expected["shipping"]
    assert body["total"] == expected["total"]


def test_cart_quote_404_unknown_product(client):
    r = client.post("/cart/quote", json={"items": [{"product_id": "unknown-sku", "qty": 1}]})
    assert r.status_code == 404


@pytest.mark.parametrize(
    "payload",
    [
        {"items": [{"product_id": "mug", "qty": 0}]},
        {"items": [{"product_id": "mug", "qty": 100}]},
        {"items": [{"product_id": "mug", "qty": 1}], "coupon": "INCONNU"},
        {"items": "pas-une-liste"},
        {"items": [{"product_id": "mug", "qty": "abc"}]},
    ],
)
def test_cart_quote_422_invalid_inputs(client, payload):
    r = client.post("/cart/quote", json=payload)
    assert r.status_code == 422


def test_create_and_get_order_201(client):
    payload = {"items": [{"product_id": "tshirt", "qty": 1}]}
    create_resp = client.post("/orders", json=payload)
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert "id" in created
    order_id = created["id"]

    get_resp = client.get(f"/orders/{order_id}")
    assert get_resp.status_code == 200
    assert get_resp.json() == created


def test_create_order_422_empty_cart(client):
    r = client.post("/orders", json={"items": []})
    assert r.status_code == 422


def test_get_order_404_not_found(client):
    r = client.get("/orders/commande-inexistante")
    assert r.status_code == 404


def test_metrics_exposes_http_requests_total(client):
    client.get("/health")
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "minishop_http_requests_total" in r.text


@pytest.mark.skipif(
    os.getenv("TEST_LIVE_SERVER") != "1",
    reason="Activer avec TEST_LIVE_SERVER=1 pour tester contre l'application réelle (app_url)",
)
def test_live_server_health_and_products(app_url):
    with httpx.Client(base_url=app_url, timeout=5.0) as http:
        r_health = http.get("/health")
        assert r_health.status_code == 200
        assert r_health.json()["status"] == "ok"

        r_products = http.get("/products")
        assert r_products.status_code == 200
        assert len(r_products.json()) >= 2

#----------------------------------------------------------------------
# Atelier 9 — Partie B : tests de contrat API
#----------------------------------------------------------------------

import pytest

pytestmark = pytest.mark.api


def test_openapi_public_routes_present(client):
    schema = client.get("/openapi.json").json()
    paths = schema.get("paths", {})

    expected_routes = {
        "/health": "get",
        "/products": "get",
        "/products/{product_id}": "get",
        "/cart/quote": "post",
        "/orders": "post",
        "/orders/{order_id}": "get",
    }

    for route, method in expected_routes.items():
        assert route in paths, f"Route manquante dans OpenAPI : {route}"
        assert method in paths[route], f"Méthode {method.upper()} manquante sur {route}"


def test_response_field_types_contract(client):
    schema = client.get("/openapi.json").json()
    assert "paths" in schema
    _components = schema.get("components", {}).get("schemas", {})
    assert isinstance(_components, dict)

    # 1. Contrat sur /products/{product_id}
    prod = client.get("/products/mug").json()
    assert set(prod.keys()) >= {"id", "name", "price", "stock"}
    assert isinstance(prod["id"], str)
    assert isinstance(prod["name"], str)
    assert isinstance(prod["price"], str)
    assert isinstance(prod["stock"], int)

    # 2. Contrat sur /cart/quote
    quote_resp = client.post("/cart/quote", json={"items": [{"product_id": "mug", "qty": 1}]}).json()
    assert set(quote_resp.keys()) >= {"lines", "subtotal", "discount", "shipping", "total", "coupon"}
    assert isinstance(quote_resp["lines"], list)
    assert isinstance(quote_resp["subtotal"], str)
    assert isinstance(quote_resp["discount"], str)
    assert isinstance(quote_resp["shipping"], str)
    assert isinstance(quote_resp["total"], str)
    assert quote_resp["coupon"] is None or isinstance(quote_resp["coupon"], str)

    # 3. Contrat sur /orders et GET /orders/{order_id}
    order = client.post("/orders", json={"items": [{"product_id": "mug", "qty": 1}]}).json()
    assert set(order.keys()) >= {"id", "lines", "subtotal", "discount", "shipping", "total"}
    assert isinstance(order["id"], str)
    assert isinstance(order["total"], str)