"""Tests pytest générés à partir de specs/pricing.feature (MiniShop - calcul de panier).

Prix déduits de la spécification (le catalogue n'est pas fourni) :
- mug : 12.50 €  (2 mugs = 25.00)
- sticker : 2.45 €  (10 stickers = 24.50 brut, 23.28 après remise volume)
- hoodie : 44.00 €  (1 hoodie + 1 mug = 56.50)
- book : 29.99 €  (book + sticker = 32.44)
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from minishop.pricing import coupon_discount, line_total, money, quote, shipping_cost

pytestmark = [pytest.mark.generated, pytest.mark.unit]


MUG = Decimal("12.50")
STICKER = Decimal("2.45")


@pytest.fixture(autouse=True)
def _env_propre(monkeypatch):
    """Garantit que le bug de régression d'arrondi n'est pas actif pendant les tests."""
    monkeypatch.delenv("MINISHOP_BUG", raising=False)


def _items(*pairs):
    """Construit la liste d'items attendue par quote()."""
    return [{"product_id": pid, "qty": qty} for pid, qty in pairs]


# ---------------------------------------------------------------------------
# Tests issus des scénarios de la spécification
# ---------------------------------------------------------------------------


def test_panier_vide():
    """Un panier vide a un total nul et aucuns frais de livraison."""
    q = quote([])
    assert q.total == Decimal("0.00")
    assert q.shipping == Decimal("0.00")


def test_achat_simple_avec_frais_de_livraison():
    """Deux mugs donnent un sous-total de 25.00 et des frais de livraison de 4.90."""
    q = quote(_items(("mug", 2)))
    assert q.subtotal == Decimal("25.00")
    assert q.shipping == Decimal("4.90")
    assert q.total == Decimal("29.90")


def test_livraison_offerte_a_partir_de_50_euros():
    """Un panier d'au moins 50 euros après remise bénéficie de la livraison offerte."""
    q = quote(_items(("hoodie", 1), ("mug", 1)))
    assert q.shipping == Decimal("0.00")
    assert q.total == Decimal("56.50")


def test_remise_volume_des_10_unites():
    """Dès 10 stickers, une remise volume de 5 % s'applique sur la ligne."""
    q = quote(_items(("sticker", 10)))
    assert q.subtotal == Decimal("23.28")


def test_coupon_de_bienvenue():
    """Le coupon WELCOME10 applique 10 % de remise si le sous-total est au moins 20 euros."""
    q = quote(_items(("mug", 2)), "WELCOME10")
    assert q.discount == Decimal("2.50")
    assert q.total == Decimal("27.40")


def test_coupon_de_bienvenue_sous_le_seuil():
    """Le coupon WELCOME10 n'accorde aucune remise si le sous-total est inférieur à 20 euros."""
    q = quote(_items(("mug", 1)), "WELCOME10")
    assert q.discount == Decimal("0.00")


def test_coupon_de_livraison_offerte():
    """Le coupon FREESHIP annule les frais de livraison."""
    q = quote(_items(("sticker", 1)), "FREESHIP")
    assert q.shipping == Decimal("0.00")
    assert q.total == Decimal("2.45")


def test_coupon_inconnu():
    """Un code coupon inconnu lève une erreur 'Coupon inconnu'."""
    with pytest.raises(ValueError, match="Coupon inconnu"):
        quote(_items(("mug", 1)), "NOEL2026")


def test_produit_inconnu():
    """Un produit absent du catalogue lève une erreur 'Produit inconnu'."""
    # DIVERGENCE SPEC/CODE : la spec attend une ValueError "Produit inconnu", alors que
    # quote() délègue à get_product() qui lève une KeyError (voir commentaire du code).
    with pytest.raises(ValueError, match="Produit inconnu"):
        quote(_items(("licorne", 1)))


def test_coupon_de_5_euros_a_partir_de_30_euros():
    """Le coupon FIXED5 retire 5 euros lorsque le sous-total atteint 30 euros."""
    q = quote(_items(("book", 1), ("sticker", 1)), "FIXED5")
    assert q.subtotal == Decimal("32.44")
    assert q.discount == Decimal("5.00")
    assert q.shipping == Decimal("4.90")
    assert q.total == Decimal("32.34")


def test_remise_volume_cumulee_avec_le_coupon_de_bienvenue():
    """La remise volume et le coupon WELCOME10 se cumulent sur le sous-total remisé."""
    q = quote(_items(("mug", 10)), "WELCOME10")
    assert q.subtotal == Decimal("118.75")
    assert q.discount == Decimal("11.88")
    assert q.shipping == Decimal("0.00")
    assert q.total == Decimal("106.87")


def test_quantite_nulle_refusee():
    """Une quantité nulle est refusée avec l'erreur 'Quantité hors limites'."""
    with pytest.raises(ValueError, match="Quantité hors limites"):
        quote(_items(("mug", 0)))


# ---------------------------------------------------------------------------
# Tests de cas limites (non cités par la spécification)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("qty", [1, 99], ids=["min", "max"])
def test_limite_quantites_bornes_acceptees(qty):
    """Les quantités 1 et 99 (bornes incluses) sont acceptées."""
    q = quote(_items(("mug", qty)))
    assert q.lines[0].qty == qty


@pytest.mark.parametrize("qty", [-1, 100], ids=["negative", "au_dessus_du_max"])
def test_limite_quantites_hors_bornes_refusees(qty):
    """Les quantités -1 et 100 (hors bornes) sont refusées."""
    with pytest.raises(ValueError, match="Quantité hors limites"):
        quote(_items(("mug", qty)))


@pytest.mark.parametrize("qty", [True, 2.0, "2"], ids=["bool", "float", "str"])
def test_limite_quantite_non_entiere_refusee(qty):
    """Une quantité qui n'est pas un entier strict est refusée."""
    with pytest.raises(ValueError, match="entier"):
        line_total(MUG, qty)


@pytest.mark.parametrize(
    ("qty", "expected"),
    [(9, Decimal("112.50")), (10, Decimal("118.75"))],
    ids=["sous_seuil_sans_remise", "seuil_avec_remise"],
)
def test_limite_remise_volume_seuil(qty, expected):
    """La remise volume s'applique exactement à partir de 10 unités, pas avant."""
    assert line_total(MUG, qty) == expected


def test_limite_arrondi_half_up_sur_ligne():
    """La remise volume sur 10 stickers (23.275) s'arrondit au centime supérieur."""
    assert line_total(STICKER, 10) == Decimal("23.28")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("0.125", "0.13"),
        ("0.124", "0.12"),
        ("2.675", "2.68"),
        ("-0.125", "-0.13"),
        ("1.005", "1.01"),
    ],
    ids=["demi_monte", "sous_demi", "demi_2_675", "demi_negatif", "demi_1_005"],
)
def test_limite_money_arrondi_commercial(value, expected):
    """money() arrondit au centime en ROUND_HALF_UP, y compris les demi-centimes."""
    assert money(value) == Decimal(expected)


@pytest.mark.parametrize(
    ("subtotal", "expected"),
    [
        (Decimal("20.00"), Decimal("2.00")),
        (Decimal("19.99"), Decimal("0.00")),
        (Decimal("100.00"), Decimal("10.00")),
    ],
    ids=["seuil_inclus", "juste_sous_seuil", "grand_montant"],
)
def test_limite_welcome10_seuil_de_20_euros(subtotal, expected):
    """WELCOME10 vaut 10 % si le sous-total est >= 20 (seuil inclus)."""
    assert coupon_discount(subtotal, "WELCOME10") == expected


@pytest.mark.parametrize(
    ("subtotal", "expected"),
    [
        (Decimal("30.00"), Decimal("5.00")),
        (Decimal("29.99"), Decimal("0.00")),
    ],
    ids=["seuil_inclus", "juste_sous_seuil"],
)
def test_limite_fixed5_seuil_de_30_euros(subtotal, expected):
    """FIXED5 accorde 5 euros si le sous-total est >= 30 (seuil inclus)."""
    assert coupon_discount(subtotal, "FIXED5") == expected


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (Decimal("50.00"), Decimal("0.00")),
        (Decimal("49.99"), Decimal("4.90")),
    ],
    ids=["seuil_inclus", "juste_sous_seuil"],
)
def test_limite_livraison_offerte_seuil_de_50_euros(amount, expected):
    """La livraison est offerte à partir de 50 euros (seuil inclus)."""
    assert shipping_cost(amount, None, False) == expected


def test_limite_livraison_nulle_panier_vide():
    """Sans lignes, shipping_cost renvoie 0 même si le montant est nul."""
    assert shipping_cost(Decimal("0.00"), None, True) == Decimal("0.00")


@pytest.mark.parametrize("coupon", ["welcome10", "  WeLcOmE10 "], ids=["minuscules", "casse_et_espaces"])
def test_limite_coupon_insensible_a_la_casse_et_aux_espaces(coupon):
    """Un code coupon est normalisé (casse et espaces) avant application."""
    q = quote(_items(("mug", 2)), coupon)
    assert q.coupon == "WELCOME10"
    assert q.discount == Decimal("2.50")


def test_limite_freeship_minuscules_avec_espaces():
    """FREESHIP en minuscules et avec espaces annule quand même les frais de livraison."""
    q = quote(_items(("mug", 1)), " freeship ")
    assert q.coupon == "FREESHIP"
    assert q.shipping == Decimal("0.00")


def test_limite_coupon_chaine_vide_ignoree():
    """Une chaîne vide comme coupon est ignorée, sans erreur."""
    q = quote(_items(("mug", 2)), "")
    assert q.coupon is None
    assert q.discount == Decimal("0.00")
    assert q.total == Decimal("29.90")


def test_limite_fixed5_non_applique_sous_seuil():
    """FIXED5 n'est pas appliqué sous 30 euros, les frais de livraison restent dus."""
    q = quote(_items(("mug", 1)), "FIXED5")
    assert q.discount == Decimal("0.00")
    assert q.shipping == Decimal("4.90")
    assert q.total == Decimal("17.40")


@pytest.mark.parametrize("coupon", ["WELCOME10", "FIXED5"], ids=["welcome10", "fixed5"])
def test_limite_seuil_livraison_evalue_apres_remise(coupon):
    """Le seuil de livraison gratuite se vérifie après remise : 50 euros bruts deviennent 45 euros."""
    q = quote(_items(("mug", 4)), coupon)
    assert q.subtotal == Decimal("50.00")
    assert q.discount == Decimal("5.00")
    assert q.shipping == Decimal("4.90")
    assert q.total == Decimal("49.90")


def test_limite_panier_vide_avec_coupon_reste_a_zero():
    """Un panier vide avec un coupon valide reste à un total nul sans livraison."""
    q = quote([], "FREESHIP")
    assert q.coupon == "FREESHIP"
    assert q.discount == Decimal("0.00")
    assert q.shipping == Decimal("0.00")
    assert q.total == Decimal("0.00")


def test_limite_as_dict_montants_en_texte_decimal():
    """as_dict() expose les montants sous forme de chaînes décimales exactes."""
    d = quote(_items(("mug", 2)), "WELCOME10").as_dict()
    assert d["subtotal"] == "25.00"
    assert d["discount"] == "2.50"
    assert d["shipping"] == "4.90"
    assert d["total"] == "27.40"
    assert d["coupon"] == "WELCOME10"
