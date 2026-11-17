"""Tests E2E Playwright — SOLUTION Atelier 8."""

import re

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


@pytest.fixture
def shop(page: Page, app_url):
    page.goto(app_url)
    expect(page.get_by_test_id("products").locator("li")).to_have_count(5)
    return page


def test_page_accueil(shop: Page):
    expect(shop).to_have_title(re.compile("MiniShop"))
    expect(shop.get_by_test_id("order-btn")).to_be_disabled()


def test_parcours_achat_avec_coupon(shop: Page):
    shop.get_by_test_id("add-mug").click()
    shop.get_by_test_id("add-mug").click()
    expect(shop.get_by_test_id("cart-mug")).to_have_text(re.compile("× 2"))
    shop.get_by_test_id("coupon").fill("WELCOME10")
    shop.get_by_test_id("quote-btn").click()
    expect(shop.get_by_test_id("total")).to_have_text("27.40")
    shop.get_by_test_id("order-btn").click()
    expect(shop.get_by_test_id("confirmation")).to_have_text(re.compile(r"^Commande [0-9a-f]{12} confirmée$"))


def test_coupon_invalide_affiche_erreur(shop: Page):
    shop.get_by_test_id("add-tshirt").click()
    shop.get_by_test_id("coupon").fill("NOEL")
    shop.get_by_test_id("quote-btn").click()
    expect(shop.get_by_role("alert")).to_contain_text("Coupon inconnu")


def test_commander_desactive_tant_que_le_panier_est_vide(shop: Page):
    expect(shop.get_by_test_id("order-btn")).to_be_disabled()
    shop.get_by_test_id("add-mug").click()
    expect(shop.get_by_test_id("order-btn")).to_be_enabled()
