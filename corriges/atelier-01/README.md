# Atelier 1 — Tests unitaires

`1 h 15` `Tests unitaires` `TDD` `Couverture` 

> **Corrigé**
>
>
> Cette page donne la solution complète. Comparez d'abord la **démarche**, puis le code.

## Le résultat à atteindre

| Mesure | Tests de départ | Corrigé |
|---|---|---|
| Nombre de tests | 3 | 36 |
| Couverture de branches de `pricing.py` | 58 % | 100 % |
| Score de mutation (`mutation_score.py`) | 12 % (5 mutants sur 40) | 88 % (35 sur 40) |
| Avec `MINISHOP_BUG=rounding` | 1 test échoue | 3 tests échouent |

Les 5 mutants survivants du corrigé sont de deux sortes. Quatre sont **équivalents** : ils modifient la
valeur initiale `0.00` d'un champ du devis, toujours recalculée ensuite, et aucun test ne peut les
distinguer. Le cinquième change les frais de livraison (`4.90` en `4.901`) : il survit parce que les tests
comparent le résultat à la constante `SHIPPING_FEE` au lieu de la valeur attendue `4.90`. Un test qui écrit
la valeur en clair le tuerait.

## La démarche

Le fichier se construit dans l'ordre du code testé : d'abord les fonctions élémentaires, puis celles
qui les assemblent.

1. **`money`** : l'arrondi au centime, avec des valeurs qui tombent exactement sur un demi-centime.
2. **`line_total`** : la remise volume de part et d'autre du seuil, puis toutes les quantités invalides.
3. **`coupon_discount`** : chaque coupon au seuil et juste en dessous, la casse, l'absence de coupon.
4. **`shipping_cost`** : le seuil de 50 €, le coupon `FREESHIP`, le panier vide.
5. **`quote`** : quelques scénarios complets, dont celui où la remise fait repasser sous le seuil de livraison.
6. **Le bug injecté** : la preuve que la suite le détecte.

## Les points clés

### Tester l'arrondi là où il se décide

```python
@pytest.mark.parametrize(
    "raw, expected",
    [
        ("0.125", "0.13"),
        ("0.124", "0.12"),
        ("2.005", "2.01"),
        (10, "10.00"),
        ("-0.125", "-0.13"),
    ],
)
def test_money_arrondi_commercial(raw, expected):
    assert money(raw) == D(expected)
```

Seules les valeurs qui tombent **exactement** sur un demi-centime distinguent l'arrondi commercial de
l'arrondi bancaire. `0.124` passerait avec les deux : ce sont `0.125`, `2.005` et `-0.125` qui
détectent le bug d'arrondi.

### Encadrer chaque seuil

```python
def test_remise_volume_a_partir_de_10():
    assert line_total(D("2.45"), 10) == D("23.28")  # 24.50 * 0.95 = 23.275 -> 23.28

def test_pas_de_remise_volume_a_9():
    assert line_total(D("2.45"), 9) == D("22.05")
```

Deux tests, un de chaque côté du seuil. Un `>` écrit à la place de `>=` ferait échouer le premier ;
c'est le seul moyen de le voir.

### Regrouper les valeurs invalides

```python
@pytest.mark.parametrize("qty", [0, -1, 100, "2", 2.0, True, None])
def test_quantite_invalide(qty):
    with pytest.raises(ValueError):
        line_total(D("10"), qty)
```

Sept cas en un test. `True` mérite sa place : en Python un booléen **est** un entier, et sans le
contrôle explicite du code il serait accepté comme une quantité de 1.

### Une table pour les coupons

```python
@pytest.mark.parametrize(
    "subtotal, coupon, expected",
    [
        ("20.00", "WELCOME10", "2.00"),  # seuil inclus
        ("19.99", "WELCOME10", "0.00"),  # sous le seuil
        ("30.00", "FIXED5", "5.00"),
        ("29.99", "FIXED5", "0.00"),
        ("100.00", "FREESHIP", "0.00"),  # FREESHIP n'est pas une remise sur le montant
        ("50.00", None, "0.00"),
        ("50.00", "", "0.00"),
        ("40.00", " welcome10 ", "4.00"),  # casse et espaces tolérés
    ],
)
def test_coupon_discount(subtotal, coupon, expected):
    assert coupon_discount(D(subtotal), coupon) == D(expected)
```

La table se lit comme la spécification. Le commentaire en bout de ligne dit **pourquoi** le cas existe.

### Le scénario que la couverture ne réclame pas

```python
def test_livraison_calculee_apres_remise():
    """52 € de sous-total -10 % = 46.80 € -> la livraison redevient payante."""
    q = quote([{"product_id": "hoodie", "qty": 1}, {"product_id": "sticker", "qty": 3}], "WELCOME10")
    assert q.subtotal == D("51.35")
    assert q.shipping == SHIPPING_FEE
```

Toutes les lignes du code sont déjà couvertes sans ce test. Il vérifie pourtant une règle métier que
rien d'autre ne garantit : la livraison se calcule **après** la remise. C'est l'exemple type du test
qu'on écrit en lisant la spécification, pas le rapport de couverture.

### Prouver que la suite attrape le bug

```python
def test_bug_arrondi_detecte(monkeypatch):
    """Démontre que la suite attrape le bug injecté MINISHOP_BUG=rounding."""
    monkeypatch.setenv("MINISHOP_BUG", "rounding")
    assert money("0.125") != D("0.13")
```

`monkeypatch.setenv` active la variable le temps du test et la retire ensuite. Lancée avec
`MINISHOP_BUG=rounding pytest -m unit`, la suite complète échoue sur trois cas de
`test_money_arrondi_commercial`.

## Le fichier complet

```python title="tests/unit/test_pricing.py"
"""Tests unitaires des règles de prix — SOLUTION Atelier 1."""

from decimal import Decimal

import pytest

from minishop.pricing import (
    SHIPPING_FEE,
    coupon_discount,
    line_total,
    money,
    quote,
    shipping_cost,
)

pytestmark = pytest.mark.unit
D = Decimal

# ---------- money ----------
@pytest.mark.parametrize(
    "raw, expected",
    [
        ("0.125", "0.13"),
        ("0.124", "0.12"),
        ("2.005", "2.01"),
        (10, "10.00"),
        ("-0.125", "-0.13"),
    ],
)
def test_money_arrondi_commercial(raw, expected):
    assert money(raw) == D(expected)

# ---------- line_total ----------
def test_line_total_sans_remise():
    assert line_total(D("12.50"), 2) == D("25.00")

def test_remise_volume_a_partir_de_10():
    assert line_total(D("2.45"), 10) == D("23.28")  # 24.50 * 0.95 = 23.275 -> 23.28

def test_pas_de_remise_volume_a_9():
    assert line_total(D("2.45"), 9) == D("22.05")

@pytest.mark.parametrize("qty", [0, -1, 100, "2", 2.0, True, None])
def test_quantite_invalide(qty):
    with pytest.raises(ValueError):
        line_total(D("10"), qty)

@pytest.mark.parametrize("qty", [1, 99])
def test_quantite_bornes_valides(qty):
    assert line_total(D("1.00"), qty) > 0

# ---------- coupons ----------
@pytest.mark.parametrize(
    "subtotal, coupon, expected",
    [
        ("20.00", "WELCOME10", "2.00"),  # seuil inclus
        ("19.99", "WELCOME10", "0.00"),  # sous le seuil
        ("30.00", "FIXED5", "5.00"),
        ("29.99", "FIXED5", "0.00"),
        ("100.00", "FREESHIP", "0.00"),  # FREESHIP n'est pas une remise sur le montant
        ("50.00", None, "0.00"),
        ("50.00", "", "0.00"),
        ("40.00", " welcome10 ", "4.00"),  # casse et espaces tolérés
    ],
)
def test_coupon_discount(subtotal, coupon, expected):
    assert coupon_discount(D(subtotal), coupon) == D(expected)

def test_coupon_inconnu():
    with pytest.raises(ValueError, match="Coupon inconnu"):
        coupon_discount(D("50"), "NOEL2026")

# ---------- livraison ----------
@pytest.mark.parametrize(
    "amount, coupon, empty, expected",
    [
        ("49.99", None, False, SHIPPING_FEE),
        ("50.00", None, False, D("0.00")),
        ("10.00", "FREESHIP", False, D("0.00")),
        ("0.00", None, True, D("0.00")),
    ],
)
def test_shipping_cost(amount, coupon, empty, expected):
    assert shipping_cost(D(amount), coupon, empty) == expected

# ---------- quote (intégration des règles) ----------
def test_quote_panier_vide():
    q = quote([])
    assert (q.total, q.shipping, q.discount) == (D("0.00"),) * 3

def test_quote_complet_avec_welcome10():
    q = quote([{"product_id": "mug", "qty": 2}], "WELCOME10")
    assert q.subtotal == D("25.00")
    assert q.discount == D("2.50")
    assert q.shipping == SHIPPING_FEE  # 22.50 < 50
    assert q.total == D("27.40")

def test_livraison_calculee_apres_remise():
    """52 € de sous-total -10 % = 46.80 € -> la livraison redevient payante."""
    q = quote([{"product_id": "hoodie", "qty": 1}, {"product_id": "sticker", "qty": 3}], "WELCOME10")
    assert q.subtotal == D("51.35")
    assert q.shipping == SHIPPING_FEE

def test_produit_inconnu():
    with pytest.raises(KeyError):
        quote([{"product_id": "licorne", "qty": 1}])

def test_as_dict_serialisable():
    d = quote([{"product_id": "book", "qty": 1}]).as_dict()
    assert d["total"] == "34.89" and d["lines"][0]["product_id"] == "book"

def test_bug_arrondi_detecte(monkeypatch):
    """Démontre que la suite attrape le bug injecté MINISHOP_BUG=rounding."""
    monkeypatch.setenv("MINISHOP_BUG", "rounding")
    assert money("0.125") != D("0.13")
```

> **Ce qui change d'un langage à l'autre**
>
>
> En Java et en C#, la quantité est typée `int` : les cas `"2"` et `True` n'existent pas, le
> compilateur les refuse. En JavaScript, `2` et `2.0` sont le même nombre : le cas devient `2.5`.
> Le typage statique supprime une classe entière de tests ; le typage dynamique les rend
> indispensables.

## Le cycle TDD : le coupon `STUDENT15`

> Coupon `STUDENT15` : -15 % sur le sous-total, sans minimum, **non cumulable** avec la remise volume
> (si une ligne a la remise volume, le coupon ne s'applique pas à cette ligne).

### Rouge : les tests d'abord

```python title="tests/unit/test_student15.py"
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
```

Lancés avant d'écrire le code, ils échouent tous avec `ValueError: Coupon inconnu : STUDENT15`.

Le troisième test est celui qui porte la règle : un panier mixte, où une seule ligne entre dans
l'assiette de la remise. Sans lui, une implémentation naïve (15 % de tout le sous-total) passerait.

On a vu les tests échouer **pour la bonne raison** : c'est le résultat attendu de l'étape rouge.
À ce stade, on commite : `test: règles du coupon STUDENT15`.

### Vert : le minimum pour passer

```diff
--- minishop/pricing.py (avant)
+++ minishop/pricing.py (après)
@@ -9,4 +9,5 @@
     * FIXED5    : -5 € si sous-total >= 30 €
     * FREESHIP  : livraison offerte
+    * STUDENT15 : -15 % sans minimum, hors lignes bénéficiant déjà de la remise volume
   Un seul coupon par panier. Coupon inconnu -> ValueError.
 - Livraison : 4,90 € ; offerte si le total après remise >= 50 €.
@@ -28,5 +29,6 @@
 BULK_RATE = Decimal("0.05")
 MAX_QTY = 99
-COUPONS = {"WELCOME10", "FIXED5", "FREESHIP"}
+STUDENT_RATE = Decimal("0.15")
+COUPONS = {"WELCOME10", "FIXED5", "FREESHIP", "STUDENT15"}
 
 
@@ -83,6 +85,9 @@
 
 
-def coupon_discount(subtotal: Decimal, coupon: str | None) -> Decimal:
-    """Montant de la remise apportée par le coupon (positif)."""
+def coupon_discount(subtotal: Decimal, coupon: str | None, eligible: Decimal | None = None) -> Decimal:
+    """Montant de la remise apportée par le coupon (positif).
+
+    `eligible` : part du sous-total sans remise volume (assiette de STUDENT15) ; par défaut, tout le sous-total.
+    """
     if coupon is None or coupon == "":
         return Decimal("0.00")
@@ -94,4 +99,6 @@
     if code == "FIXED5" and subtotal >= Decimal("30"):
         return Decimal("5.00")
+    if code == "STUDENT15":
+        return money((subtotal if eligible is None else eligible) * STUDENT_RATE)
     return Decimal("0.00")
 
@@ -115,5 +122,6 @@
         q.lines.append(Line(product.id, item["qty"], product.price, total))
     q.subtotal = money(sum((ln.total for ln in q.lines), Decimal("0")))
-    q.discount = coupon_discount(q.subtotal, coupon) if q.lines else Decimal("0.00")
+    eligible = sum((ln.total for ln in q.lines if ln.qty < BULK_QTY), Decimal("0"))
+    q.discount = coupon_discount(q.subtotal, coupon, eligible) if q.lines else Decimal("0.00")
     after = q.subtotal - q.discount
     q.shipping = shipping_cost(after, coupon, empty=not q.lines)
```

Cinq modifications, pas une de plus :

- le coupon rejoint l'ensemble `COUPONS` ;
- son taux devient une constante nommée ;
- `coupon_discount` reçoit un paramètre facultatif `eligible`, l'assiette de la remise ;
- la branche `STUDENT15` applique le taux à cette assiette ;
- `quote` calcule l'assiette : la somme des lignes qui n'ont **pas** la remise volume.

Le paramètre `eligible` est facultatif pour ne casser aucun appel existant : les 36 tests déjà écrits
passent sans modification. La suite compte alors 40 tests, avec 100 % de branches.

Les tests déjà écrits passent sans modification. On commite : `feat: coupon STUDENT15`.

### Remaniement

La suite est verte. C'est le moment d'améliorer la structure sans changer le comportement, par exemple
en extrayant le calcul de l'assiette dans une fonction nommée, ou en remplaçant la suite de conditions
par une table de règles. La suite est relancée après chaque petit pas.

## Ce qu'il fallait retenir

- Un **seuil** se teste des deux côtés.
- Un test **paramétré** remplace dix tests copiés-collés et se lit comme une table de décision.
- La **couverture** dit ce qui a été exécuté ; le **bug injecté** et le **score de mutation** disent
  ce qui a été vérifié.
- En **TDD**, l'historique Git montre les tests avant le code.

---

## Fichiers de cet atelier

Par rapport à la branche `python/depart` :

| | Fichier |
|---|---|
| ajouté | `corriges/atelier-01/pieces/student15/pricing.py` |
| ajouté | `corriges/atelier-01/pieces/student15/test_student15.py` |
| modifié | `tests/unit/test_pricing.py` |

### `corriges/atelier-01/pieces/student15/pricing.py`

````python
"""Règles de calcul du panier MiniShop.

Règles métier (voir specs/pricing.feature) :
- Prix exprimés en euros TTC, arrondis au centime (ROUND_HALF_UP).
- Quantité : entier entre 1 et 99, sinon ValueError.
- Remise volume : -5 % sur une ligne dès 10 unités du même produit.
- Coupons :
    * WELCOME10 : -10 % sur le sous-total si sous-total >= 20 €
    * FIXED5    : -5 € si sous-total >= 30 €
    * FREESHIP  : livraison offerte
    * STUDENT15 : -15 % sans minimum, hors lignes bénéficiant déjà de la remise volume
  Un seul coupon par panier. Coupon inconnu -> ValueError.
- Livraison : 4,90 € ; offerte si le total après remise >= 50 €.
- Panier vide : total 0, pas de frais de livraison.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from minishop.catalog import get_product

CENT = Decimal("0.01")
SHIPPING_FEE = Decimal("4.90")
FREE_SHIPPING_THRESHOLD = Decimal("50.00")
BULK_QTY = 10
BULK_RATE = Decimal("0.05")
MAX_QTY = 99
STUDENT_RATE = Decimal("0.15")
COUPONS = {"WELCOME10", "FIXED5", "FREESHIP", "STUDENT15"}


def money(value: Decimal | float | int | str) -> Decimal:
    """Arrondit un montant au centime (arrondi commercial)."""
    d = Decimal(str(value))
    # Bug injectable pour les démos de régression (MINISHOP_BUG=rounding)
    if os.getenv("MINISHOP_BUG") == "rounding":
        return d.quantize(CENT)  # ROUND_HALF_EVEN par défaut : 0.125 -> 0.12
    return d.quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass
class Line:
    product_id: str
    qty: int
    unit_price: Decimal
    total: Decimal


@dataclass
class Quote:
    lines: list[Line] = field(default_factory=list)
    subtotal: Decimal = Decimal("0.00")
    discount: Decimal = Decimal("0.00")
    shipping: Decimal = Decimal("0.00")
    total: Decimal = Decimal("0.00")
    coupon: str | None = None

    def as_dict(self) -> dict:
        return {
            "lines": [
                {"product_id": ln.product_id, "qty": ln.qty, "unit_price": str(ln.unit_price), "total": str(ln.total)}
                for ln in self.lines
            ],
            "subtotal": str(self.subtotal),
            "discount": str(self.discount),
            "shipping": str(self.shipping),
            "total": str(self.total),
            "coupon": self.coupon,
        }


def line_total(unit_price: Decimal, qty: int) -> Decimal:
    """Total d'une ligne, remise volume incluse."""
    if not isinstance(qty, int) or isinstance(qty, bool):
        raise ValueError("La quantité doit être un entier")
    if qty < 1 or qty > MAX_QTY:
        raise ValueError(f"Quantité hors limites (1..{MAX_QTY}) : {qty}")
    gross = unit_price * qty
    if qty >= BULK_QTY:
        gross = gross * (1 - BULK_RATE)
    return money(gross)


def coupon_discount(subtotal: Decimal, coupon: str | None, eligible: Decimal | None = None) -> Decimal:
    """Montant de la remise apportée par le coupon (positif).

    `eligible` : part du sous-total sans remise volume (assiette de STUDENT15) ; par défaut, tout le sous-total.
    """
    if coupon is None or coupon == "":
        return Decimal("0.00")
    code = coupon.strip().upper()
    if code not in COUPONS:
        raise ValueError(f"Coupon inconnu : {coupon}")
    if code == "WELCOME10" and subtotal >= Decimal("20"):
        return money(subtotal * Decimal("0.10"))
    if code == "FIXED5" and subtotal >= Decimal("30"):
        return Decimal("5.00")
    if code == "STUDENT15":
        return money((subtotal if eligible is None else eligible) * STUDENT_RATE)
    return Decimal("0.00")


def shipping_cost(amount_after_discount: Decimal, coupon: str | None, empty: bool) -> Decimal:
    if empty:
        return Decimal("0.00")
    if coupon and coupon.strip().upper() == "FREESHIP":
        return Decimal("0.00")
    if amount_after_discount >= FREE_SHIPPING_THRESHOLD:
        return Decimal("0.00")
    return SHIPPING_FEE


def quote(items: list[dict], coupon: str | None = None) -> Quote:
    """Calcule un devis pour une liste d'items {product_id, qty}."""
    q = Quote(coupon=coupon.strip().upper() if coupon else None)
    for item in items:
        product = get_product(item["product_id"])  # KeyError si inconnu
        total = line_total(product.price, item["qty"])
        q.lines.append(Line(product.id, item["qty"], product.price, total))
    q.subtotal = money(sum((ln.total for ln in q.lines), Decimal("0")))
    eligible = sum((ln.total for ln in q.lines if ln.qty < BULK_QTY), Decimal("0"))
    q.discount = coupon_discount(q.subtotal, coupon, eligible) if q.lines else Decimal("0.00")
    after = q.subtotal - q.discount
    q.shipping = shipping_cost(after, coupon, empty=not q.lines)
    q.total = money(after + q.shipping)
    return q
````

### `corriges/atelier-01/pieces/student15/test_student15.py`

````python
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
````

### `tests/unit/test_pricing.py`

Modification :

````diff
diff --git a/tests/unit/test_pricing.py b/tests/unit/test_pricing.py
index e3fd95b..9eb008b 100644
--- a/tests/unit/test_pricing.py
+++ b/tests/unit/test_pricing.py
@@ -1,36 +1,130 @@
-"""Tests unitaires des règles de prix — POINT DE DÉPART (Atelier 1).
-
-Complétez ce fichier : objectif >= 90 % de couverture sur minishop/pricing.py.
-"""
+"""Tests unitaires des règles de prix — SOLUTION Atelier 1."""
 
 from decimal import Decimal
 
 import pytest
 
-from minishop.pricing import line_total, money, quote
+from minishop.pricing import (
+    SHIPPING_FEE,
+    coupon_discount,
+    line_total,
+    money,
+    quote,
+    shipping_cost,
+)
 
 pytestmark = pytest.mark.unit
+D = Decimal
 
 
-def test_money_arrondi_commercial():
-    """0.125 s'arrondit à 0.13 (ROUND_HALF_UP), pas 0.12."""
-    assert money("0.125") == Decimal("0.13")
+# ---------- money ----------
+@pytest.mark.parametrize(
+    "raw, expected",
+    [
+        ("0.125", "0.13"),
+        ("0.124", "0.12"),
+        ("2.005", "2.01"),
+        (10, "10.00"),
+        ("-0.125", "-0.13"),
+    ],
+)
+def test_money_arrondi_commercial(raw, expected):
+    assert money(raw) == D(expected)
 
 
+# ---------- line_total ----------
 def test_line_total_sans_remise():
-    assert line_total(Decimal("12.50"), 2) == Decimal("25.00")
+    assert line_total(D("12.50"), 2) == D("25.00")
+
+
+def test_remise_volume_a_partir_de_10():
+    assert line_total(D("2.45"), 10) == D("23.28")  # 24.50 * 0.95 = 23.275 -> 23.28
+
+
+def test_pas_de_remise_volume_a_9():
+    assert line_total(D("2.45"), 9) == D("22.05")
+
+
+@pytest.mark.parametrize("qty", [0, -1, 100, "2", 2.0, True, None])
+def test_quantite_invalide(qty):
+    with pytest.raises(ValueError):
+        line_total(D("10"), qty)
+
+
+@pytest.mark.parametrize("qty", [1, 99])
+def test_quantite_bornes_valides(qty):
+    assert line_total(D("1.00"), qty) > 0
+
+
+# ---------- coupons ----------
+@pytest.mark.parametrize(
+    "subtotal, coupon, expected",
+    [
+        ("20.00", "WELCOME10", "2.00"),  # seuil inclus
+        ("19.99", "WELCOME10", "0.00"),  # sous le seuil
+        ("30.00", "FIXED5", "5.00"),
+        ("29.99", "FIXED5", "0.00"),
+        ("100.00", "FREESHIP", "0.00"),  # FREESHIP n'est pas une remise sur le montant
+        ("50.00", None, "0.00"),
+        ("50.00", "", "0.00"),
+        ("40.00", " welcome10 ", "4.00"),  # casse et espaces tolérés
+    ],
+)
+def test_coupon_discount(subtotal, coupon, expected):
+    assert coupon_discount(D(subtotal), coupon) == D(expected)
+
 
+def test_coupon_inconnu():
+    with pytest.raises(ValueError, match="Coupon inconnu"):
+        coupon_discount(D("50"), "NOEL2026")
 
+
+# ---------- livraison ----------
+@pytest.mark.parametrize(
+    "amount, coupon, empty, expected",
+    [
+        ("49.99", None, False, SHIPPING_FEE),
+        ("50.00", None, False, D("0.00")),
+        ("10.00", "FREESHIP", False, D("0.00")),
+        ("0.00", None, True, D("0.00")),
+    ],
+)
+def test_shipping_cost(amount, coupon, empty, expected):
+    assert shipping_cost(D(amount), coupon, empty) == expected
+
+
+# ---------- quote (intégration des règles) ----------
 def test_quote_panier_vide():
-    """Un panier vide coûte 0 € : pas de frais de livraison."""
     q = quote([])
-    assert q.total == Decimal("0.00")
-    assert q.shipping == Decimal("0.00")
+    assert (q.total, q.shipping, q.discount) == (D("0.00"),) * 3
+
+
+def test_quote_complet_avec_welcome10():
+    q = quote([{"product_id": "mug", "qty": 2}], "WELCOME10")
+    assert q.subtotal == D("25.00")
+    assert q.discount == D("2.50")
+    assert q.shipping == SHIPPING_FEE  # 22.50 < 50
+    assert q.total == D("27.40")
+
+
+def test_livraison_calculee_apres_remise():
+    """52 € de sous-total -10 % = 46.80 € -> la livraison redevient payante."""
+    q = quote([{"product_id": "hoodie", "qty": 1}, {"product_id": "sticker", "qty": 3}], "WELCOME10")
+    assert q.subtotal == D("51.35")
+    assert q.shipping == SHIPPING_FEE
+
+
+def test_produit_inconnu():
+    with pytest.raises(KeyError):
+        quote([{"product_id": "licorne", "qty": 1}])
+
+
+def test_as_dict_serialisable():
+    d = quote([{"product_id": "book", "qty": 1}]).as_dict()
+    assert d["total"] == "34.89" and d["lines"][0]["product_id"] == "book"
 
 
-# TODO Atelier 1 :
-#  - remise volume à partir de 10 unités (et pas à 9 !)
-#  - quantités invalides (0, 100, -1, "2", True) -> ValueError   (astuce : @pytest.mark.parametrize)
-#  - coupons WELCOME10 / FIXED5 / FREESHIP (seuils inclus/exclus), coupon inconnu, casse
-#  - livraison offerte à partir de 50 € APRÈS remise
-#  - produit inconnu -> KeyError
+def test_bug_arrondi_detecte(monkeypatch):
+    """Démontre que la suite attrape le bug injecté MINISHOP_BUG=rounding."""
+    monkeypatch.setenv("MINISHOP_BUG", "rounding")
+    assert money("0.125") != D("0.13")
````
