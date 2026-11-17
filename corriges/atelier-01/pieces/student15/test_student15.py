"""Coupon STUDENT15 — SOLUTION du cycle TDD de l'Atelier 1 (étape 3).

Règle : -15 % sur le sous-total, sans minimum, non cumulable avec la remise volume
(une ligne qui bénéficie déjà de la remise volume est exclue de l'assiette du coupon).
"""

from decimal import Decimal

import pytest

from minishop.pricing import quote

pytestmark = pytest.mark.unit
D = Decimal


def test_student15_sans_minimum():
    """1 mug à 12,50 € : 15 % de remise, soit 1,88 € (1,875 arrondi au centime supérieur)."""
    q = quote([{"product_id": "mug", "qty": 1}], "STUDENT15")
    assert q.discount == D("1.88")
    assert q.total == D("15.52")  # 12.50 - 1.88 + 4.90 de livraison


def test_student15_non_cumulable_avec_la_remise_volume():
    """10 stickers ont déjà la remise volume : le coupon ne s'applique pas à cette ligne."""
    q = quote([{"product_id": "sticker", "qty": 10}], "STUDENT15")
    assert q.subtotal == D("23.28")
    assert q.discount == D("0.00")


def test_student15_panier_mixte():
    """Seule la ligne sans remise volume entre dans l'assiette : 15 % de 25,00 € = 3,75 €."""
    q = quote([{"product_id": "mug", "qty": 2}, {"product_id": "sticker", "qty": 10}], "STUDENT15")
    assert q.subtotal == D("48.28")
    assert q.discount == D("3.75")


def test_student15_casse_et_espaces():
    assert quote([{"product_id": "mug", "qty": 2}], " student15 ").discount == D("3.75")
