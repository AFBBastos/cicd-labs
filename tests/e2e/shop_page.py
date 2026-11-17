"""Page Object de la boutique — SOLUTION Atelier 8 (partie A, étape 5).

Toute la connaissance de la page (localisateurs, enchaînement des clics) est ici.
Les tests ne parlent plus que le langage du métier : ajouter, appliquer un coupon,
lire le total, commander. Si un `data-testid` change, on corrige ce seul fichier.

Les méthodes qui lisent la page renvoient un localisateur et non une valeur : le test
garde ainsi les assertions « web-first » de Playwright (`expect(...)` réessaie jusqu'au
délai), sans aucun `sleep`.
"""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect


class ShopPage:
    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url

    # --- navigation -------------------------------------------------------
    def open(self) -> ShopPage:
        self.page.goto(self.base_url)
        # Le catalogue est chargé par un appel à /products : on attend qu'il soit affiché.
        expect(self.products).to_have_count(5)
        return self

    # --- actions ----------------------------------------------------------
    def add(self, product: str, qty: int = 1) -> ShopPage:
        """Ajoute `qty` fois le produit (identifiant du catalogue : mug, tshirt, book…)."""
        for _ in range(qty):
            self.page.get_by_test_id(f"add-{product}").click()
        return self

    def apply_coupon(self, code: str) -> ShopPage:
        """Saisit le code promo et demande le calcul du total."""
        self.page.get_by_label("Code promo").fill(code)
        return self.compute()

    def compute(self) -> ShopPage:
        self.page.get_by_role("button", name="Calculer le total").click()
        return self

    def order(self) -> ShopPage:
        self.order_button.click()
        return self

    # --- lecture de la page (localisateurs, à passer à expect) -------------
    @property
    def products(self) -> Locator:
        return self.page.get_by_test_id("products").locator("li")

    def cart_line(self, product: str) -> Locator:
        return self.page.get_by_test_id(f"cart-{product}")

    def total(self) -> Locator:
        return self.page.get_by_test_id("total")

    @property
    def error(self) -> Locator:
        return self.page.get_by_role("alert")

    @property
    def order_button(self) -> Locator:
        return self.page.get_by_role("button", name="Commander")

    @property
    def confirmation(self) -> Locator:
        return self.page.get_by_test_id("confirmation")
