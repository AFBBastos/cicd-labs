"""Tests E2E Playwright avec Page Object — SOLUTION Atelier 8 (partie A, étape 5).

Mêmes parcours que `test_parcours_achat.py`, réécrits avec la classe `ShopPage`
(fichier `shop_page.py`, dans le même dossier).
"""

import re

import pytest
from playwright.sync_api import Page, expect
from shop_page import ShopPage

pytestmark = pytest.mark.e2e


@pytest.fixture
def shop(page: Page, app_url) -> ShopPage:
    return ShopPage(page, app_url).open()


def test_page_accueil(shop: ShopPage):
    expect(shop.page).to_have_title(re.compile("MiniShop"))
    expect(shop.products).to_have_count(5)


def test_parcours_achat_avec_coupon(shop: ShopPage):
    shop.add("mug", qty=2)
    expect(shop.cart_line("mug")).to_have_text(re.compile("× 2"))
    shop.apply_coupon("WELCOME10")
    expect(shop.total()).to_have_text("27.40")
    shop.order()
    expect(shop.confirmation).to_have_text(re.compile(r"^Commande [0-9a-f]{12} confirmée$"))


def test_coupon_invalide_affiche_erreur(shop: ShopPage):
    shop.add("tshirt").apply_coupon("NOEL")
    expect(shop.error).to_contain_text("Coupon inconnu")
    expect(shop.total()).to_be_hidden()


def test_commander_desactive_tant_que_le_panier_est_vide(shop: ShopPage):
    expect(shop.order_button).to_be_disabled()
    shop.add("mug")
    expect(shop.order_button).to_be_enabled()
