# Atelier 3 — Générer des tests avec un LLM : corrigé

**Durée : 2 h 30** (lundi fin d'après-midi + mardi 9 h 00 - 11 h 00) · Module 2

**Objectif.** Transformer une spécification Gherkin en tests pytest exécutables, d'abord avec le moteur
déterministe, puis avec un LLM, et juger le résultat avec deux mesures : la couverture et le score de mutation.

**Comment lire ce corrigé.** Les mesures offline, de couverture et de mutation ont été exécutées dans
une copie du dépôt stagiaires (Python 3.13.5). Les générations par LLM ont été lancées le 17/11/2026 par
la session principale, avec l'accord du formateur, sur la spécification enrichie à 12 scénarios ; les
fichiers produits ont ensuite été réexécutés pour ce corrigé (tests, couverture, mutation).
**Chaque ligne LLM est un seul essai : les chiffres varient d'un lancement à l'autre**, comme le montrent
les deux essais du prompt fourni (29 puis 35 tests). La mesure faite lundi par le formateur (31 tests en
35 s) est gardée comme point de comparaison distinct : elle portait sur la spécification d'origine, à
9 scénarios.

**Le fichier `tests/generated/test_pricing_ai.py` livré en solution contient volontairement un test
faux** (`test_produit_inconnu`, en échec). C'est la sortie brute du premier essai du prompt fourni,
non retouchée : elle sert de support au tri « bug ou hallucination » de l'étape 3. Ne pas la corriger.

Fichiers de solution : `formateur/solutions/atelier-03/`

| Fichier | Rôle |
|---|---|
| `specs/pricing.feature` | Spécification enrichie des 3 scénarios de l'étape 1 (12 scénarios) |
| `specs/pricing-etendue.feature` | Variante de démonstration à 16 scénarios (voir étape 5) |
| `tests/generated/test_pricing_offline.py` | Sortie du moteur offline pour les 12 scénarios |
| `tests/generated/test_pricing_ai.py` | Sortie brute de Claude Haiku, prompt fourni, essai 1 : 29 tests dont 1 faux, laissé tel quel |
| `ai_tools/prompts/generate_tests.spec-seule.md` | Variante de prompt « sans le code source » |
| `ai_tools/prompts/generate_tests.few-shot.md` | Variante de prompt « + exemple de test parfait » |
| `ai_tools/generate_tests.temperature-0.8.diff` | Modification d'une ligne pour la variante « température 0.8 » (fournisseurs autres que Claude) |
| `docs/strategie-de-test.md` | Stratégie de test avec la section 3 rédigée |

## Le résultat à atteindre

Mesures sur `minishop/pricing.py` (73 instructions, 24 branches, 40 mutants). La colonne « Couverture »
est le pourcentage affiché par `pytest --cov=minishop.pricing --cov-branch` (lignes et branches combinées).

| Suite de tests | Tests exécutés | Tests en échec | Couverture | Score de mutation |
|---|---|---|---|---|
| Tests de départ (`tests/unit`) | 3 | 0 | 58 % | 5/40 = 12 % |
| Offline, spécification d'origine (9 scénarios) | 9 | 0 | 91 % | 24/40 = 60 % |
| **Offline, spécification enrichie (12 scénarios)** | 12 | 0 | 95 % | 27/40 = 68 % |
| Tests de départ + offline 12 scénarios | 15 | 0 | 95 % | 28/40 = 70 % |
| Offline, spécification étendue (16 scénarios, démonstration) | 16 | 0 | 95 % | 34/40 = 85 % |
| Solution de l'Atelier 1 (tests manuels) | 36 | 0 | 100 % | 35/40 = 88 % |
| Solution de l'Atelier 1 + offline 12 scénarios | 48 | 0 | 100 % | 36/40 = 90 % |
| **LLM Claude Haiku, prompt fourni, 12 scénarios (essai 1)** | 44 (29 fonctions, dont 17 `test_limite_*`) | 1 | 98 % | 36/40 = 90 % (test faux écarté) |
| LLM Claude Haiku, prompt fourni, 12 scénarios (essai 2) | 52 (35 fonctions, dont 23 `test_limite_*`) | 1 | 98 % | 36/40 = 90 % (test faux écarté) |
| LLM Claude Sonnet, prompt fourni, 12 scénarios | 63 (34 fonctions, dont 22 `test_limite_*`) | 0 | 100 % | 36/40 = 90 % |
| Pour comparaison : mesure du formateur, lundi (Claude Haiku, **9 scénarios**) | 31 fonctions, dont 22 `test_limite_*` | 0 | non relevée | non relevé |

Lignes LLM : un seul essai par ligne. `mutation_score.py` refuse de calculer quand un test échoue : le
score est donné après avoir écarté le test faux (`--deselect`).

Ce que le tableau montre :

- Douze tests générés depuis la spécification font passer le score de mutation de 12 % à 68 % en une
  seconde de génération. C'est l'argument en faveur de la génération.
- Ils restent 20 points sous les tests écrits à la main de l'Atelier 1 (88 %), alors que la couverture
  n'est qu'à 5 points d'écart (95 % contre 100 %). C'est l'argument pour ne pas se fier à la couverture.
- Entre 12 et 16 scénarios, la couverture ne bouge pas (95 %) et le score de mutation gagne 17 points :
  les scénarios ajoutés visent des **bornes**, pas des lignes.
- Le LLM atteint 90 % en une quarantaine de secondes, soit le niveau des tests manuels (88 %) et au-dessus
  du plafond du moteur offline (85 %), parce qu'il appelle `coupon_discount`, `line_total` et
  `shipping_cost` directement. Mais les deux essais Haiku contiennent chacun **un test faux** :
  le gain n'existe qu'après relecture.

Durées observées : génération offline 1 s ; génération par LLM 27 à 41 s ; une analyse de mutation 45 s
(40 mutants, une exécution de pytest par mutant).

## Étape 1 — La spécification (15 min)

`specs/pricing.feature` contient 9 scénarios. L'en-tête du fichier donne la grammaire que le moteur
offline sait lire ; tout ajout doit la respecter (voir l'étape 2 pour ce qui arrive sinon).

Les 3 scénarios ajoutés (fichier complet : `formateur/solutions/atelier-03/specs/pricing.feature`) :

```gherkin
  Scénario: Coupon de 5 euros à partir de 30 euros
    Étant donné un panier avec 1 "book" et 1 "sticker"
    Quand j'applique le coupon "FIXED5"
    Et je calcule le total
    Alors le sous-total vaut 32.44
    Et la remise vaut 5.00
    Et la livraison vaut 4.90
    Et le total vaut 32.34

  Scénario: Remise volume cumulée avec le coupon de bienvenue
    Étant donné un panier avec 10 "mug"
    Quand j'applique le coupon "WELCOME10"
    Et je calcule le total
    Alors le sous-total vaut 118.75
    Et la remise vaut 11.88
    Et la livraison vaut 0.00
    Et le total vaut 106.87

  Scénario: Quantité nulle refusée
    Étant donné un panier avec 0 "mug"
    Quand je calcule le total
    Alors une erreur "Quantité hors limites" est levée
```

Les montants se calculent à la main, à partir des règles, **pas en lançant le code** :

| Scénario | Calcul |
|---|---|
| FIXED5 | 29.99 + 2.45 = 32.44 ≥ 30 → remise 5.00 ; 27.44 < 50 → livraison 4.90 ; total 32.34 |
| Volume + WELCOME10 | 10 × 12.50 = 125.00, -5 % = 118.75 ; 10 % de 118.75 = 11.875 → 11.88 ; 106.87 ≥ 50 → livraison offerte |
| Quantité 0 | hors de l'intervalle 1..99 → `ValueError`, message « Quantité hors limites (1..99) : 0 » |

**Le seuil exact de FIXED5 est hors de portée de la spécification.** L'énoncé demande un coupon FIXED5
« sur un panier d'au moins 30 € » (une version antérieure disait « FIXED5 au seuil », ce qui était
irréalisable). Aucun panier du catalogue n'a en effet un sous-total d'exactement
30.00 € (ni d'exactement 20.00 €, le seuil de WELCOME10). Vérifié par énumération de tous les paniers
de 0 à 12 unités de chacun des cinq produits : le seul seuil atteignable est 50.00 € (4 mugs). Un stagiaire qui
cherche « le panier à 30 € pile » ne le trouvera pas. La spécification, qui ne connaît que des paniers,
ne peut donc pas exprimer le cas « seuil inclus » de FIXED5 ; un test unitaire qui appelle
`coupon_discount(Decimal("30.00"), "FIXED5")` le peut (c'est ce que fait la solution de l'Atelier 1).
Le scénario retenu ici se place juste au-dessus du seuil ; son symétrique juste en dessous est
`1 "book"` avec FIXED5 (remise 0.00, total 34.89, vérifié).

## Étape 2 — Moteur déterministe : la référence (15 min)

```bash
LLM_PROVIDER=offline python ai_tools/generate_tests.py specs/pricing.feature \
    --out tests/generated/test_pricing_offline.py
```

Sortie obtenue :

```text
[+] 12 tests écrits dans tests/generated/test_pricing_offline.py (moteur : offline)
............                                                             [100%]
12 passed in 0.04s

[+] Tous les tests générés passent
```

Avec la spécification d'origine, la même commande écrit 9 tests.

Extrait du fichier produit (complet : `formateur/solutions/atelier-03/tests/generated/test_pricing_offline.py`) :

```python
pytestmark = [pytest.mark.generated, pytest.mark.unit]


def test_coupon_de_5_euros_a_partir_de_30_euros():
    """Coupon de 5 euros à partir de 30 euros"""
    q = quote([{"product_id": "book", "qty": 1}, {"product_id": "sticker", "qty": 1}], "FIXED5")
    assert q.subtotal == Decimal("32.44")
    assert q.discount == Decimal("5.00")
    assert q.shipping == Decimal("4.90")
    assert q.total == Decimal("32.34")


def test_quantite_nulle_refusee():
    """Quantité nulle refusée"""
    with pytest.raises(ValueError, match="Quantité hors limites"):
        quote([{"product_id": "mug", "qty": 0}], None)
```

Ce qu'il faut faire lire aux stagiaires :

- **Un scénario = une fonction.** Le nom vient du titre du scénario (accents retirés), la docstring aussi.
- **Un `Alors` = un `assert`.** Le moteur n'ajoute rien : un scénario qui ne vérifie que la remise
  produit un test qui ne vérifie que la remise.
- **Il n'appelle que `quote`.** Les fonctions `money`, `line_total`, `coupon_discount` et `shipping_cost`
  ne sont testées qu'à travers elle.
- **Le type d'exception est deviné** à partir du message : `KeyError` si le message contient « Produit »,
  `ValueError` sinon.
- **Le fichier est exécuté tout de suite** par `generate_tests.py` (garde-fou) et le code de retour vaut 1
  si un test échoue.

### La limite : il ne traduit que la grammaire prévue

Démonstration à faire au vidéoprojecteur, avec un fichier de deux scénarios : le premier utilise une
tournure absente de la grammaire, le second contient une attente fausse.

```gherkin
  Scénario: Total plafonné
    Étant donné un panier avec 2 "mug"
    Quand je calcule le total
    Alors le total est inférieur à 30 euros

  Scénario: Attente fausse dans la spécification
    Étant donné un panier avec 2 "mug"
    Quand je calcule le total
    Alors le total vaut 29.00
```

Résultat obtenu :

```python
def test_total_plafonne():
    """Total plafonné"""
    q = quote([{"product_id": "mug", "qty": 2}], None)
```

```text
[!] ligne 6 non reconnue par le moteur offline, ignorée : Alors le total est inférieur à 30 euros
[!] scénario « Total plafonné » : aucune vérification reconnue, le test généré n'aura pas d'assertion
[+] 2 tests écrits dans tests/generated/test_demo.py (moteur : offline)
E       AssertionError: assert Decimal('29.90') == Decimal('29.00')
1 failed, 1 passed
[!] Des tests générés échouent : à analyser (bug ou hallucination ?)
```

- La ligne `Alors le total est inférieur à 30 euros` est ignorée : le test n'a aucun `assert` et il est
  vert. C'est exactement le « test qui couvre sans rien vérifier » de l'étape 5. Le moteur le signale
  désormais par deux avertissements sur la sortie d'erreur (avant correction de l'outil, la ligne était
  ignorée en silence) ; le test sans assertion est tout de même écrit, et le code de retour n'en dépend pas.
- Le second test échoue, et l'application a raison : c'est la **spécification** qui est fausse. Un test
  généré en échec a donc trois causes possibles, pas deux : bug de l'application, hallucination du
  modèle, ou erreur dans la spécification.

Réponse à retenir : le moteur offline est reproductible, gratuit et ne peut rien inventer ; en
contrepartie il n'imagine aucun cas limite et sa qualité est exactement celle de la spécification.
Il sert de référence pour juger le LLM.

## Étape 3 — Moteur LLM (30 min)

```bash
export LLM_PROVIDER=anthropic         # + ANTHROPIC_API_KEY
python ai_tools/generate_tests.py specs/pricing.feature \
    --source minishop/pricing.py --out tests/generated/test_pricing_ai.py
```

Extrait de la sortie obtenue avec Claude Haiku (essai 1, 41 s) :

```text
[+] 29 tests écrits dans tests/generated/test_pricing_ai.py (moteur : anthropic)
FAILED tests/generated/test_pricing_ai.py::test_produit_inconnu - KeyError: 'Produi...
1 failed, 43 passed
[!] Des tests générés échouent : à analyser (bug ou hallucination ?)
```

Le fichier complet est livré tel quel : `formateur/solutions/atelier-03/tests/generated/test_pricing_ai.py`.

**Si la première ligne dit `(moteur : offline)`, aucun LLM n'a répondu** : le fichier contient alors les
12 tests de l'étape 2. Message obtenu sans clé :

```text
[!] LLM indisponible (Variable ANTHROPIC_API_KEY (ou LLM_API_KEY) manquante pour anthropic) -> repli sur le moteur offline
[+] 12 tests écrits dans tests/generated/test_pricing_ai.py (moteur : offline)
```

### Ce que contient le prompt

`ai_tools/prompts/generate_tests.md` est le message système. Le message utilisateur est assemblé par
`render_llm` : la spécification, puis le code source, puis « Génère le fichier de tests complet. »
(7 467 caractères avec `pricing.py`, contre 3 261 sans code source). Chaque règle du prompt répond à un
défaut connu des tests générés :

| Règle | Défaut qu'elle prévient |
|---|---|
| 1. Un test par scénario, nommé d'après lui | Scénarios oubliés, traçabilité perdue |
| 2. Cas limites préfixés `test_limite_` | Impossible de distinguer ce qui vient de la spec de ce que le modèle a déduit |
| 3. `parametrize` | Dix fonctions copiées-collées |
| 4. `Decimal`, jamais `float` | Comparaisons de montants fausses |
| 5. N'invente aucune fonction | Hallucination d'API |
| 6. `pytestmark = [generated, unit]` | Tests générés impossibles à isoler |
| 7. Docstring d'une ligne | Tests illisibles en revue |
| 8. Commentaire `# DIVERGENCE SPEC/CODE` | Le modèle « corrige » silencieusement la spec d'après le code |

La dernière ligne (« Réponds UNIQUEMENT avec un bloc python ») sert à l'extraction : `extract_code`
prend le premier bloc de code de la réponse. Le fichier est ensuite compilé ; s'il ne compile pas, il
est écrit dans `test_pricing_ai.rejected.txt` et la commande renvoie 2.

### Réponses aux questions

**Combien de tests ? Combien de `test_limite_*` ?**

| Essai (prompt fourni, 12 scénarios) | Fonctions `test_*` | dont `test_limite_*` | Cas exécutés par pytest | Durée |
|---|---|---|---|---|
| Claude Haiku, essai 1 | 29 | 17 | 44 | 41 s |
| Claude Haiku, essai 2 | 35 | 23 | 52 | 33 s |
| Pour comparaison : formateur, lundi, **9 scénarios** | 31 | 22 | non relevé | 35 s |

Dans les deux essais, 12 fonctions correspondent aux 12 scénarios ; toutes les autres sont des cas
limites que la spécification ne mentionnait pas. Un seul essai par ligne : le même prompt, le même
modèle et la même spécification donnent 29 puis 35 fonctions. Pour compter dans le fichier d'un stagiaire :

```bash
grep -c "^def test_" tests/generated/test_pricing_ai.py
grep -c "^def test_limite_" tests/generated/test_pricing_ai.py
pytest tests/generated/test_pricing_ai.py -q     # un parametrize compte pour plusieurs cas exécutés
```

Les deux nombres ne coïncident pas : `grep` compte les fonctions, pytest compte les cas (un test
paramétré de 5 lignes vaut 5). Demandez aux stagiaires de dire lequel ils reportent.

Ce que le modèle a ajouté de lui-même dans l'essai 1, à faire repérer dans le fichier livré : les bornes
1 et 99 acceptées, -1 et 100 refusées ; les quantités `True`, `2.0`, `"2"` ; les seuils de 20 €, 30 € et
50 € testés **inclus et juste en dessous** par appel direct de `coupon_discount` et `shipping_cost` (ce
que la spécification ne peut pas exprimer, voir l'étape 1) ; l'arrondi sur cinq demi-centimes ; la casse
et les espaces des coupons ; le seuil de livraison évalué après remise ; `as_dict`.

**Des tests échouent-ils ? Bug de l'appli ou hallucination ?**
Oui. Sur les six fichiers générés pour ce corrigé (deux essais du prompt fourni et les variantes de
l'étape 4), quatre contiennent au moins un test en échec, cinq échecs au total. **Aucun n'est un bug de
l'application** : les cinq sont des erreurs du modèle, de trois natures différentes.

#### Les tests en échec, un par un

**1. `test_produit_inconnu` — une contrainte inventée dans la spécification.** Présent dans trois
fichiers sur six (prompt fourni essai 1, few-shot, `LLM_EFFORT=low`). Extrait de l'essai 1 :

```python
def test_produit_inconnu():
    """Un produit absent du catalogue lève une erreur 'Produit inconnu'."""
    # DIVERGENCE SPEC/CODE : la spec attend une ValueError "Produit inconnu", alors que
    # quote() délègue à get_product() qui lève une KeyError (voir commentaire du code).
    with pytest.raises(ValueError, match="Produit inconnu"):
        quote(_items(("licorne", 1)))
```

```text
FAILED tests/generated/test_pricing_ai.py::test_produit_inconnu - KeyError: 'Produi...
```

La spécification dit seulement « une erreur "Produit inconnu" est levée », sans préciser de type. Le
modèle a supposé que la spec voulait une `ValueError`, constaté que le code lève une `KeyError`, puis
appliqué la règle 8 du prompt (« en cas de contradiction, écris le test selon la spécification »).
Il n'y a pas de divergence : c'est une hallucination sur la **spécification**, rendue possible par une
règle du prompt. Décision : le test est faux, on corrige le type attendu en `KeyError` après avoir relu
la spec. Les autres fichiers s'en sortent autrement, ce qui mérite aussi une lecture :

| Fichier | Ce que le modèle a écrit | Résultat |
|---|---|---|
| Prompt fourni essai 1, few-shot, effort low | `pytest.raises(ValueError, match="Produit inconnu")` | échec |
| Prompt fourni essai 2, spec seule | `pytest.raises(Exception, match=…)` | passe, mais accepte n'importe quelle exception |
| Sonnet | `pytest.raises((KeyError, ValueError), match="Produit inconnu")` | passe |

**2. `test_limite_remise_volume_bornes[11-…]` — une erreur de calcul** (prompt fourni, essai 2) :

```python
        (10, Decimal("23.28")),  # seuil exact de la remise volume
        (11, Decimal("26.5")),  # 11 * 2.45 * 0.95 = 25.5725 -> 25.57 (voir assertion ci-dessous)
    ],
)
def test_limite_remise_volume_bornes(qty, attendu):
    """La remise volume de 5 % commence exactement à 10 unités."""
    if qty == 11:
        attendu = Decimal("25.57")
    assert line_total(Decimal("2.45"), qty) == attendu
```

Le modèle a écrit une première valeur fausse (26.5), s'en est aperçu, et l'a « corrigée » dans le corps
du test par une seconde valeur fausse : 11 × 2.45 = 26.95, × 0.95 = 25.6025, soit **25.60**, ce que
renvoie le code. Le commentaire de calcul est faux lui aussi. Décision : erreur du modèle ; le test se
corrige en refaisant le calcul à la main, pas en recopiant la sortie du code.

**3. `test_limite_fixed5_seuil_30_euros[items1-5.00]` — une borne mal placée** (few-shot) :

```python
        ([{"product_id": "sticker", "qty": 2}], "0.00"),  # 4.90 < 30 : FIXED5 inactif
        ([{"product_id": "book", "qty": 1}], "5.00"),  # 30.00 : seuil inclus
```

Un livre coûte 29.99 €, pas 30.00 € : le panier est sous le seuil et le code a raison de renvoyer 0.00.
C'est le piège de l'étape 1 (aucun panier ne vaut 30.00 € pile), dans lequel le modèle est tombé.

Grille de tri à donner, illustrée par ces cas :

| Symptôme | Cause probable | Décision |
|---|---|---|
| `ImportError`, `AttributeError`, `TypeError: unexpected keyword` | Fonction ou paramètre inventé (non observé ici) | Hallucination : supprimer le test |
| Montant attendu faux (cas 2) | Le modèle a mal fait l'arithmétique | Refaire le calcul à la main, corriger la valeur attendue |
| Borne mal placée (cas 3) | Le modèle a confondu 29.99 et 30.00 | Corriger ou supprimer le cas |
| Exception d'un autre type, avec `# DIVERGENCE SPEC/CODE` (cas 1) | Le modèle a prêté à la spec une exigence qu'elle n'a pas | Relire la spec : ici pas de divergence, le test est faux |
| Le calcul à la main donne tort au code | Bug de l'application (non observé ici) | Ticket, et le test est gardé |

La règle à faire énoncer : **on ne « répare » jamais un test rouge en recopiant la valeur renvoyée par
le code**, et un commentaire `DIVERGENCE` rédigé avec aplomb n'est pas une preuve.

Deux défauts qui ne font échouer aucun test, trouvés à la relecture :

- **Le bug d'arrondi neutralisé.** Les deux essais du prompt fourni et le fichier Sonnet contiennent
  une fixture `autouse` qui retire la variable `MINISHOP_BUG` avant chaque test. Conséquence mesurée :
  `MINISHOP_BUG=rounding pytest` donne exactement le même résultat qu'en temps normal. Ces fichiers
  ne peuvent pas détecter le bug injectable par ce moyen, alors même qu'ils testent l'arrondi sur des
  demi-centimes et tuent le mutant correspondant.
- **Des assertions affaiblies** : `pytest.raises(Exception, …)` dans l'essai 2 (voir le tableau ci-dessus).

**Le modèle a-t-il inventé une fonction ou un paramètre ?**
Non, dans aucun des six fichiers. Vérification : tout ce que le fichier importe doit exister dans
`minishop/pricing.py`.

```bash
grep -n "^from\|^import" tests/generated/test_pricing_ai.py
```

```text
from minishop.pricing import coupon_discount, line_total, money, quote, shipping_cost
```

Les noms légitimes sont `quote`, `money`, `line_total`, `coupon_discount`, `shipping_cost`, `Quote`,
`Line` et les constantes du module. Les six fichiers n'importent que des noms de cette liste, et tous
leurs tests s'exécutent sans `ImportError`, `AttributeError` ni `TypeError`. La règle 5 du prompt a
tenu ; ce sont les **valeurs attendues** qui sont fausses, pas l'API.

## Étape 4 — Prompt engineering (30 min)

Le générateur lit toujours `ai_tools/prompts/generate_tests.md` : il n'existe pas d'option pour désigner un
autre fichier, et l'énoncé le dit. Une variante s'essaie donc en remplaçant ce fichier, après l'avoir sauvegardé.

```bash
cp ai_tools/prompts/generate_tests.md /tmp/prompt-fourni.md        # sauvegarde

# pour chaque variante : installer le prompt, générer en chronométrant, mesurer
time python ai_tools/generate_tests.py specs/pricing.feature \
    --source minishop/pricing.py --out tests/generated/test_pricing_ai.py
pytest tests/generated/test_pricing_ai.py --cov=minishop.pricing --cov-branch -q

cp /tmp/prompt-fourni.md ai_tools/prompts/generate_tests.md        # retour au prompt fourni
```

Colonnes du tableau : « Nb tests » et « Tests en échec » se lisent sur la dernière ligne de pytest,
« Couverture » sur la ligne `minishop/pricing.py`, « Temps » sur la ligne `real` de `time`.

### Les variantes

| Variante | Comment la produire |
|---|---|
| Prompt fourni | Rien à changer |
| Sans le code source | `cp formateur/solutions/atelier-03/ai_tools/prompts/generate_tests.spec-seule.md ai_tools/prompts/generate_tests.md`, puis `--source vide.py` où `vide.py` est un fichier vide (`: > vide.py`) |
| + exemple few-shot | `cp formateur/solutions/atelier-03/ai_tools/prompts/generate_tests.few-shot.md ai_tools/prompts/generate_tests.md` |
| Effort de raisonnement réduit | `LLM_EFFORT=low python ai_tools/generate_tests.py …` (`medium` par défaut) ; `LLM_EFFORT=high` a aussi été essayé |
| Autre modèle | `LLM_MODEL=claude-sonnet-5-5 python ai_tools/generate_tests.py …` |

**Sans le code source.** `--source` est obligatoire et vaut `minishop/pricing.py` par défaut : pour ne pas
envoyer le code, on lui passe un fichier vide. La variante de prompt remplace les règles qui parlent du
code : la règle 5 donne la seule signature utilisable (`quote(items, coupon=None)` et les quatre champs
du résultat) et la règle 8 demande de ne pas inventer de montant quand la spec est muette
(commentaire `# SPEC MUETTE`). Sans cette signature, le modèle ne peut que deviner l'API.

**Few-shot.** La variante ajoute au prompt fourni un test modèle, paramétré, dont chaque cas porte un
commentaire de calcul :

```python
@pytest.mark.parametrize(
    "qty, attendu",
    [
        (9, "22.05"),  # sous le seuil : 9 x 2.45, pas de remise
        (10, "23.28"),  # seuil inclus : 24.50 x 0.95 = 23.275 -> 23.28
    ],
)
def test_limite_remise_volume_de_part_et_d_autre_du_seuil(qty, attendu):
    """La remise volume de 5 % s'applique à partir de 10 unités, pas à 9."""
    q = quote([{"product_id": "sticker", "qty": qty}])
    assert q.subtotal == Decimal(attendu)
```

Cet exemple a été exécuté : ses deux cas passent.

> **Pourquoi `LLM_EFFORT` et non la température.** L'énoncé proposait à l'origine une ligne
> « Température 0.8 au lieu de 0.2 ». Avec `LLM_PROVIDER=anthropic`, `ai_tools/llm.py` n'envoie pas de
> température (`_chat_anthropic` ne transmet pas le paramètre : la profondeur de raisonnement se règle
> avec `effort`). L'énoncé a donc été corrigé : la ligne porte maintenant sur `LLM_EFFORT=low`.
> Pour un groupe qui utilise `mistral`, `ollama` ou `openai`, la température reste essayable en appliquant
> `formateur/solutions/atelier-03/ai_tools/generate_tests.temperature-0.8.diff`
> (une ligne : `chat(system, user, temperature=0.8)` dans `render_llm`). Aucune mesure de température
> n'a été faite.

### Le tableau

Spécification à 12 scénarios, un seul essai par ligne : les chiffres varient d'un lancement à l'autre
(comparer les deux premières lignes Haiku). « Nb tests » donne les cas exécutés par pytest et, entre
parenthèses, le nombre de fonctions `test_*` et de `test_limite_*`. La colonne « Mutation » est ajoutée
à celles de l'énoncé ; elle est calculée après avoir écarté les tests en échec.

| Variante | Nb tests | Tests en échec | Couverture branches | Temps | Mutation |
|---|---|---|---|---|---|
| Référence offline, 12 scénarios | 12 (12 ; 0) | 0 | 95 % | 1 s | 27/40 = 68 % |
| Prompt fourni, Haiku, essai 1 | 44 (29 ; 17) | 1 | 98 % | 41 s | 36/40 = 90 % |
| Prompt fourni, Haiku, essai 2 | 52 (35 ; 23) | 1 | 98 % | 33 s | 36/40 = 90 % |
| Sans le code source (spec seule), Haiku | 25 (20 ; 8) | 0 | 95 % | 28 s | 31/40 = 78 % |
| + exemple de test « parfait » (few-shot), Haiku | 40 (26 ; 14) | 2 | 98 % | 37 s | 33/40 = 82 % |
| Effort de raisonnement réduit (`LLM_EFFORT=low` au lieu de `medium`), Haiku | 43 (32 ; 20) | 1 | 98 % | 27 s | 35/40 = 88 % |
| Hors énoncé : `LLM_EFFORT=high`, Haiku | **échec de la génération** : réponse tronquée, repli offline (12 tests) | — | — | 64 s | — |
| Autre modèle (`LLM_MODEL=claude-sonnet-5-5`) | 63 (34 ; 22) | 0 | 100 % | 36 s | 36/40 = 90 % |
| Pour comparaison : formateur, lundi, Haiku, **9 scénarios** | 31 fonctions, dont 22 `test_limite_*` | 0 | non relevée | 35 s | non relevé |

### Le cas `LLM_EFFORT=high` : tronqué, puis replié sur l'offline

```text
[!] LLM indisponible (Réponse tronquée : limite de 16000 jetons atteinte (augmentez LLM_MAX_TOKENS ou passez LLM_EFFORT=low)) -> repli sur le moteur offline
[+] 12 tests écrits dans tests/generated/test_pricing_ai.py (moteur : offline)
```

Avec un effort élevé, le raisonnement du modèle a consommé le plafond de 16 000 jetons (`LLM_MAX_TOKENS`,
raisonnement compris) avant la fin de la réponse. `llm.py` lève alors `LLMError` et `generate_tests.py`
se replie sur le moteur offline : 64 s d'attente, 12 tests, **code de retour 0**. Un stagiaire qui ne lit
que « 12 passed » croit avoir mesuré la variante. C'est l'exemple réel du repli silencieux : la seule
trace est dans le log. L'essai n'a pas été refait avec un `LLM_MAX_TOKENS` plus élevé.

### Ce qui a été observé

À lire avec la réserve d'un seul essai par variante : ces écarts sont du même ordre que ceux qui
séparent deux essais du même prompt (29 et 35 fonctions).

- **Sans le code source** : c'est la variante la plus pauvre et la plus prudente. 8 `test_limite_*`
  contre 17 à 23, un seul import (`quote`), et un score de mutation de 78 %, 12 points sous le prompt
  fourni. La couverture retombe à 95 %, celle du moteur offline. Le modèle a déduit les prix des
  scénarios et a signalé ce qu'il ne pouvait pas savoir par quatre commentaires `# SPEC MUETTE`
  (seuil de WELCOME10, borne supérieure des quantités…). Aucun test en échec : la consigne « n'invente
  pas de montant » a été suivie. Il a aussi établi seul qu'aucun panier ne totalise 30.00 €, et a
  écrit pour ce cas un test dont le corps est `pass` : un test vert qui ne vérifie rien, à faire
  trouver aux stagiaires. Les mutants qui survivent en plus sont ceux de la borne 99 et du mode
  d'arrondi, deux informations absentes de la spécification.
- **Few-shot** : la forme a bien été imitée (des commentaires de calcul en bout de ligne, absents de
  l'essai 1 du prompt fourni), et le modèle a **recopié l'exemple**, nom compris
  (`test_limite_remise_volume_de_part_et_d_autre_du_seuil`). Mais c'est la variante qui produit le
  plus de tests faux (2) et le score de mutation le plus bas des variantes avec code source (82 %).
  Un exemple améliore le style, pas l'exactitude.
- **`LLM_EFFORT`** : en `low`, la génération est la plus rapide (27 s) pour un résultat voisin du réglage
  par défaut (88 % contre 90 %, un test faux dans les deux cas). En `high`, la génération échoue
  (voir ci-dessus). Sur cette tâche, augmenter l'effort n'a rien apporté.
- **Autre modèle** : Sonnet est le seul fichier sans test en échec et le seul à 100 % de couverture,
  pour une durée comparable (36 s). Son score de mutation est pourtant le même que celui de Haiku
  après retrait du test faux (90 %) : les 4 mutants restants sont les mutants équivalents, le plafond
  est atteint. La différence entre les deux modèles tient donc au travail de relecture, pas au score.
- **Dispersion** : entre les deux essais du prompt fourni, le nombre de fonctions passe de 29 à 35 et
  le test faux n'est pas le même. Faire lancer deux fois le prompt fourni avant toute comparaison.

Non observé : un fichier qui ne compile pas (dans ce cas, `generate_tests.py` écrit un fichier
`.rejected.txt` et s'arrête avec le code 2).

## Étape 5 — Évaluer la qualité des tests générés (30 min)

### Couverture

```bash
pytest tests/generated --cov=minishop.pricing --cov-branch
```

```text
Name                  Stmts   Miss Branch BrPart  Cover   Missing
-----------------------------------------------------------------
minishop/pricing.py      73      3     24      2    95%   38, 60, 76
12 passed in 0.09s
```

Les trois lignes manquantes : la branche du bug injectable (l. 38), `Quote.as_dict` (l. 60, utilisée par
l'API) et le refus d'une quantité qui n'est pas un entier (l. 76).

### Mutation

```bash
python ai_tools/mutation_score.py minishop/pricing.py tests/generated
python ai_tools/mutation_score.py minishop/pricing.py tests/unit
```

Fin de la sortie pour `tests/generated` (12 scénarios) :

```text
Score de mutation : 27/40 = 68%
Mutants survivants (= cas non vérifiés par vos tests) :
  - l.29 : 99 -> 100
  - l.26 : '50.00' -> '50.001'
  - l.37 : Eq -> NotEq
  - l.104 : GtE -> Gt
  - l.53 : '0.00' -> '0.001'
  - l.54 : '0.00' -> '0.001'
  - l.55 : '0.00' -> '0.001'
  - l.56 : '0.00' -> '0.001'
  - l.77 : Gt -> GtE
  - l.92 : GtE -> Gt
  - l.94 : GtE -> Gt
  - l.88 : '0.00' -> '0.001'
  - l.117 : '0.00' -> '0.001'
```

Lecture des 13 survivants, à faire avec `minishop/pricing.py` ouvert à côté :

| Mutants | Ce que les tests ne vérifient pas | Scénario qui les tue |
|---|---|---|
| l.29 `99 -> 100`, l.77 `Gt -> GtE` | La quantité maximale | 99 acceptés, 100 refusés |
| l.26 `50.00 -> 50.001`, l.104 `GtE -> Gt`, l.88 | La livraison à 50.00 € exactement | 4 mugs : sous-total 50.00, livraison 0.00 |
| l.37 `Eq -> NotEq` | Le mode d'arrondi (ce mutant active le bug d'arrondi en permanence) | 10 livres : 299.90 × 0.95 = 284.905 → 284.91 |
| l.117 | La remise d'un panier vide | `Et la remise vaut 0.00` dans « Panier vide » |
| l.92 `GtE -> Gt`, l.94 `GtE -> Gt` | Les seuils 20 € et 30 € inclus | Aucun : ces montants sont inatteignables avec le catalogue (étape 1) |
| l.53 à l.56 | Rien : valeurs initiales toujours recalculées | Aucun : mutants équivalents |

La colonne de droite a été vérifiée : `formateur/solutions/atelier-03/specs/pricing-etendue.feature`
ajoute ces quatre scénarios et cette assertion aux 12 précédents. Résultat : 16 tests, couverture
inchangée à 95 %, score de mutation **34/40 = 85 %**. Les 6 survivants sont les 4 mutants équivalents
et les 2 seuils inatteignables. Le moteur offline, limité à `quote` et au catalogue, plafonne donc à
85 % sur ce module ; les tests manuels de l'Atelier 1 atteignent 88 % parce qu'ils appellent
`coupon_discount` directement.

Autre mesure sur ces mêmes fichiers, avec le bug d'arrondi activé :

| Suite | `MINISHOP_BUG=rounding pytest …` |
|---|---|
| Offline, 12 scénarios | 12 passed : le bug n'est **pas** détecté |
| Offline, 16 scénarios | 1 failed (`test_arrondi_commercial_du_demi_centime` : 284.90 au lieu de 284.91) |
| LLM Haiku, prompt fourni (essais 1 et 2), LLM Sonnet | résultat identique à l'exécution normale : le bug n'est **pas** détecté (fixture qui retire `MINISHOP_BUG`, voir l'étape 3) |
| LLM Haiku, few-shot et `LLM_EFFORT=low` | 2 et 3 échecs supplémentaires : le bug est détecté |

Les deux scénarios d'arrondi de la spécification de 12 (23.275 et 11.875) ne distinguent pas l'arrondi
commercial de l'arrondi bancaire : le chiffre qui précède le 5 est impair, les deux modes arrondissent
vers le haut. Il faut un demi-centime précédé d'un chiffre pair (284.905). Une suite à 95 % de
couverture laisse donc passer le seul bug connu de l'application.

### Comparaison demandée : manuels, offline, LLM

| Approche | Tests exécutés | Couverture | Score de mutation |
|---|---|---|---|
| Tests de départ (avant l'Atelier 1) | 3 | 58 % | 5/40 = 12 % |
| Offline, 12 scénarios | 12 | 95 % | 27/40 = 68 % |
| Tests manuels (solution de l'Atelier 1) | 36 | 100 % | 35/40 = 88 % |
| LLM Haiku, prompt fourni, essai 1 (test faux écarté) | 43 | 98 % | 36/40 = 90 % |
| LLM Sonnet, prompt fourni | 63 | 100 % | 36/40 = 90 % |

Chaque analyse dure environ 45 s. Lignes LLM : un seul essai, chiffres variables d'un lancement à l'autre.

Lecture : le LLM fait légèrement mieux que les tests manuels (36 mutants tués contre 35) et nettement
mieux que le moteur offline (27). Les 4 survivants du LLM sont les mutants équivalents (l.53 à l.56) :
36/40 est le maximum atteignable sur ce module. Le mutant que le LLM tue et que les tests manuels
laissent passer est l.25 `'4.90' -> '4.901'`, pour la raison expliquée ci-dessous. Ce résultat ne vaut
qu'**après relecture** : tel que généré, le fichier Haiku contient un test en échec, et
`mutation_score.py` refuse de le mesurer (« Les tests échouent déjà sur le code non muté »). Pour
écarter le test faux le temps de la mesure :

```bash
PYTEST_ADDOPTS="--deselect tests/generated/test_pricing_ai.py::test_produit_inconnu" \
    python ai_tools/mutation_score.py minishop/pricing.py tests/generated
```

Tests manuels et tests offline se complètent aussi : la solution de l'Atelier 1 et les 12 tests générés réunis obtiennent
36/40 = 90 %. Le mutant gagné est l.25 `'4.90' -> '4.901'` : les tests manuels comparent la livraison à
la constante `SHIPPING_FEE`, qui mute avec le code, alors que les tests générés la comparent à la
valeur littérale `4.90` issue de la spécification.

Pour mesurer le score du fichier LLM seul, il doit être seul dans le dossier passé à l'outil :

```bash
mkdir -p /tmp/gen-llm && mv tests/generated/test_pricing_offline.py /tmp/gen-llm/
python ai_tools/mutation_score.py minishop/pricing.py tests/generated
```

Deux précautions d'emploi de `mutation_score.py`, constatées à l'exécution :

- La suite passée en argument doit être verte sur le code non muté, sinon l'outil s'arrête
  (« Les tests échouent déjà sur le code non muté », code 2). C'est le cas si on lui donne `tests`
  en entier, puisque les tests e2e exigent une application lancée. Le message indique maintenant ces
  deux causes (cible trop large, test généré faux) et la commande `PYTEST_ADDOPTS="--deselect …"`.
- L'outil réécrit `minishop/pricing.py` pendant l'analyse et le restaure à la fin, y compris après une
  interruption (vérifié avec un signal d'interruption en cours d'analyse). Ne pas modifier ce fichier
  pendant les 45 s.

## Étape 6 — Règles d'équipe (20 min)

Solution : `formateur/solutions/atelier-03/docs/strategie-de-test.md`, section 3 (les autres sections
sont celles du modèle ; elles se complètent à l'Atelier 12). Les règles, résumées :

1. Marqueur `generated` et dossier `tests/generated/` : les tests générés restent isolables.
2. Relecture humaine avant fusion ; le relecteur vérifie la valeur attendue contre la spécification.
3. Pas de test sans `assert`.
4. Le score de mutation ne baisse pas ; seuil visé ≥ 80 %.
5. Un test rouge ne se corrige jamais en recopiant la valeur du code : bug, spec fausse ou hallucination.
6. Ni secret ni donnée client dans un prompt.
7. Fournisseur, modèle et clé choisis par l'équipe ; code confidentiel : modèle local ou offline.
8. Le prompt est du code : modifié par PR, avec le tableau de comparaison.
9. Dans la pipeline, la génération informe et ne bloque pas.

Et deux paragraphes : **responsabilité** (un test fusionné appartient à l'équipe, l'auteur de la PR et
son relecteur en répondent) et **régénération** (un fichier offline ne se retouche pas à la main ; un
test LLM retouché rejoint `tests/unit/`).

Chaque règle est rattachée à quelque chose que les stagiaires ont vu dans l'atelier : la règle 3 au test
sans `assert` de l'étape 2, la règle 4 à l'écart couverture / mutation de l'étape 5, la règle 5 à la
grille de tri de l'étape 3. Une règle que l'équipe ne sait pas vérifier ne sera pas appliquée :
la colonne « Comment elle est vérifiée » est ce qu'il faut exiger des groupes.

## Critères de réussite

| Critère | État dans ce corrigé |
|---|---|
| Un fichier de tests généré par LLM, relu, qui passe | Généré et relu : 44 tests, 43 verts et 1 faux identifié (`test_produit_inconnu`). Le fichier livré est la sortie brute ; il passe une fois ce test corrigé en `KeyError` ou écarté |
| Le tableau de comparaison des prompts rempli | Rempli (un essai par ligne), plus une ligne hors énoncé `LLM_EFFORT=high` |
| Score de mutation mesuré pour au moins 2 approches | Démontré pour quatre : départ 12 %, offline 68 %, manuels 88 %, LLM 90 % |
| Section « règles IA » rédigée | Livrée : `formateur/solutions/atelier-03/docs/strategie-de-test.md` |

## Points d'animation

**Erreurs fréquentes**

- **Croire avoir utilisé le LLM alors que le moteur offline a répondu.** Clé absente, mal exportée, quota
  atteint ou réponse tronquée (cas réel de `LLM_EFFORT=high`) : la commande reste verte. Faire lire la
  première ligne : `(moteur : anthropic)`.
- **Faire confiance à un commentaire `# DIVERGENCE SPEC/CODE`.** Il apparaît dans quatre fichiers sur
  six, toujours sur `test_produit_inconnu`, et ne décrit jamais une vraie divergence ; dans trois
  d'entre eux le test est faux. Faire rouvrir la spécification.
- **« Corriger » le test rouge en remplaçant la valeur attendue par celle du code.** Pour 25.60 le
  résultat serait juste, mais par hasard : exiger le calcul.
- **Scénario hors grammaire** à l'étape 1 (« est inférieur à », « doit être égal à ») : test généré sans
  `assert`, vert. L'outil affiche maintenant un avertissement `[!] ligne N non reconnue` ; faire lire la
  sortie d'erreur et le fichier produit, pas seulement le résultat de pytest.
- **Montant écrit avec une virgule** : accepté. `Alors le total vaut 29,90` produit
  `assert q.total == Decimal("29.90")` (vérifié ; avant correction de l'outil, la partie décimale était perdue).
- **Calculer la valeur attendue en lançant le code.** Le scénario ne teste alors plus rien. Exiger le
  calcul à la main, comme dans le tableau de l'étape 1.
- **Chercher un panier à 30.00 € pile** : il n'existe pas. Ne pas laisser un groupe y passer dix minutes.
- **Deux scénarios de même titre** : le second test reçoit un suffixe (`test_achat_simple_2`) et l'outil
  avertit `[!] titre de scénario en double` (vérifié : 2 tests écrits, 2 exécutés ; avant correction, le
  premier était écrasé en silence). Faire tout de même renommer le scénario.
- **Mesurer la mutation sur `tests/generated` avec les deux fichiers** (offline et LLM) : le score est
  celui de l'ensemble. Isoler le fichier à mesurer.
- **Oublier de restaurer le prompt** après une variante : toutes les mesures suivantes sont faussées.
- **Comparer un seul essai par variante** et en tirer une loi. Ce corrigé n'a lui-même qu'un essai par
  ligne, et deux essais du même prompt y diffèrent de 6 fonctions.

**Questions de discussion**

- *« 95 % de couverture, pourquoi continuer ? »* Parce que cette suite laisse passer le bug d'arrondi et
  13 mutants. La couverture dit quelles lignes ont été exécutées, pas ce qui a été vérifié.
- *« 44 tests valent-ils mieux que 12 ? »* Ici oui (90 % contre 68 %), mais c'est le score de mutation
  qui le dit, pas le nombre : seize scénarios bien choisis atteignent 85 %, et les 40 tests de la
  variante few-shot font moins bien (82 %) que les 44 du prompt fourni.
- *« Le LLM fait 90 %, les tests manuels 88 % : à quoi bon écrire des tests ? »* Le LLM a eu besoin du
  code source pour y arriver (78 % sans), d'une spécification déjà écrite, et d'un humain pour repérer
  le test faux. Et il a neutralisé le bug d'arrondi sans le dire.
- *« Qui a raison quand le test généré et le code divergent ? »* Ni l'un ni l'autre par défaut : la
  spécification, relue par un humain.
- *« Faut-il versionner les tests générés ? »* Oui s'ils sont relus et intégrés ; non s'ils sont
  régénérés à chaque exécution (ils sont alors un artefact, comme à l'Atelier 4).
- *« Peut-on envoyer notre code à une API ? »* Question de l'Atelier 4 ; faire noter la règle 6 d'ici là.

**Durées à surveiller**

- Étape 4 : cinq variantes en 30 min, c'est juste. Répartir les variantes entre les groupes et mettre
  les résultats en commun dans un tableau partagé.
- Étape 5 : chaque analyse de mutation prend 45 s ; trois analyses par poste suffisent.
- L'atelier est coupé par la nuit (PLANNING.md) : finir les étapes 1 et 2 lundi, garder les étapes 3 à 6
  pour mardi matin, quand les clés d'API ont été vérifiées.

## Non vérifié

- **Reproductibilité des mesures LLM** : un seul essai par ligne. Les durées de génération et les
  fichiers générés viennent des appels faits par la session principale ; pour ce corrigé, seuls les
  tests, la couverture et la mutation ont été réexécutés sur ces fichiers.
- **Température** : aucune mesure. Le paramètre n'est pas transmis à Claude par `llm.py` ;
  `generate_tests.temperature-0.8.diff`, régénéré sur l'outil corrigé, est vérifié applicable
  (`git apply --check`) mais n'a été exécuté contre aucun fournisseur (`mistral`, `ollama`, `openai`).
- **Les fichiers générés par le modèle** l'ont été avant la correction de l'énoncé et de l'outil ; ces
  corrections ne touchent ni le prompt ni le moteur LLM, les mesures n'ont pas été refaites.
- **`LLM_EFFORT=high`** avec un `LLM_MAX_TOKENS` plus élevé : non réessayé.
- **La mesure du formateur de lundi** (31 tests, 22 `test_limite_*`, 35 s, tous verts, 9 scénarios) :
  citée, non reproduite ; couverture et mutation non relevées.
- **Un autre fournisseur** (Mistral, Ollama) et le cas du fichier généré qui ne compile pas.
- **Les commandes PowerShell** de la section « Sous Windows » de l'énoncé.

---

## Fichiers de cet atelier

Par rapport à la branche `python/atelier-02` :

| | Fichier |
|---|---|
| ajouté | `ai_tools/prompts/generate_tests.few-shot.md` |
| ajouté | `ai_tools/prompts/generate_tests.spec-seule.md` |
| ajouté | `corriges/atelier-03/pieces/ai_tools/generate_tests.temperature-0.8.diff` |
| ajouté | `corriges/atelier-03/pieces/tests/generated/test_pricing_ai.py` |
| modifié | `docs/strategie-de-test.md` |
| ajouté | `specs/pricing-etendue.feature` |
| modifié | `specs/pricing.feature` |
| ajouté | `tests/generated/test_pricing_offline.py` |

### `ai_tools/prompts/generate_tests.few-shot.md`

````markdown
Tu es un ingénieur QA senior spécialisé en Python et pytest.

Ta mission : écrire un fichier de tests pytest COMPLET et EXÉCUTABLE pour le code fourni,
à partir de la spécification fonctionnelle fournie.

Règles impératives :
1. Couvre CHAQUE scénario de la spécification par au moins un test (un test par scénario,
   nommé `test_<scenario_en_snake_case>`).
2. Ajoute ensuite des tests de cas limites que la spec ne cite pas mais que le code implique :
   bornes (valeurs de seuil incluses/exclues), valeurs invalides, arrondis, combinaisons.
   Préfixe-les par `test_limite_`.
3. Utilise `@pytest.mark.parametrize` dès que plusieurs cas partagent la même structure.
4. Utilise `decimal.Decimal` pour comparer les montants, jamais des float.
5. N'invente AUCUNE fonction, classe ou paramètre absent du code source fourni.
   Importe uniquement depuis les modules montrés (ex. `from minishop.pricing import quote`).
6. Ajoute `pytestmark = [pytest.mark.generated, pytest.mark.unit]` en tête de fichier.
7. Chaque test a une docstring d'une ligne en français qui explique la règle vérifiée.
8. Si la spécification et le code se contredisent, écris le test selon la SPÉCIFICATION
   et ajoute un commentaire `# DIVERGENCE SPEC/CODE : ...`.

Exemple de test « parfait » — imite sa FORME (paramétrage, commentaire qui justifie chaque cas,
docstring, comparaison en Decimal), pas ses valeurs :

    @pytest.mark.parametrize(
        "qty, attendu",
        [
            (9, "22.05"),  # sous le seuil : 9 x 2.45, pas de remise
            (10, "23.28"),  # seuil inclus : 24.50 x 0.95 = 23.275 -> 23.28
        ],
    )
    def test_limite_remise_volume_de_part_et_d_autre_du_seuil(qty, attendu):
        """La remise volume de 5 % s'applique à partir de 10 unités, pas à 9."""
        q = quote([{"product_id": "sticker", "qty": qty}])
        assert q.subtotal == Decimal(attendu)

Réponds UNIQUEMENT avec un bloc ```python contenant le fichier, sans texte autour.
````

### `ai_tools/prompts/generate_tests.spec-seule.md`

````markdown
Tu es un ingénieur QA senior spécialisé en Python et pytest.

Ta mission : écrire un fichier de tests pytest COMPLET et EXÉCUTABLE à partir de la seule
spécification fonctionnelle fournie. Le code source ne t'est PAS montré.

Règles impératives :
1. Couvre CHAQUE scénario de la spécification par au moins un test (un test par scénario,
   nommé `test_<scenario_en_snake_case>`).
2. Ajoute ensuite des tests de cas limites que la spec ne cite pas mais que ses règles impliquent :
   bornes (valeurs de seuil incluses/exclues), valeurs invalides, arrondis, combinaisons.
   Préfixe-les par `test_limite_`.
3. Utilise `@pytest.mark.parametrize` dès que plusieurs cas partagent la même structure.
4. Utilise `decimal.Decimal` pour comparer les montants, jamais des float.
5. La seule fonction disponible est `quote(items, coupon=None)`, à importer par
   `from minishop.pricing import quote`. `items` est une liste de dictionnaires
   `{"product_id": str, "qty": int}` ; le résultat expose `subtotal`, `discount`, `shipping`
   et `total` (des `Decimal`). N'utilise RIEN d'autre : aucune autre fonction, classe ou paramètre.
6. Ajoute `pytestmark = [pytest.mark.generated, pytest.mark.unit]` en tête de fichier.
7. Chaque test a une docstring d'une ligne en français qui explique la règle vérifiée.
8. Quand la spécification ne permet pas de connaître la valeur attendue d'un cas limite,
   n'invente pas de montant : n'écris pas le test et ajoute un commentaire `# SPEC MUETTE : ...`.

Réponds UNIQUEMENT avec un bloc ```python contenant le fichier, sans texte autour.
````

### `corriges/atelier-03/pieces/ai_tools/generate_tests.temperature-0.8.diff`

````diff
--- a/ai_tools/generate_tests.py
+++ b/ai_tools/generate_tests.py
@@ -131,7 +131,7 @@
     if out is not None:
         # Java, PHP et C# exigent que la classe porte le nom du fichier ; Node.js a besoin du chemin relatif.
         user += f" Il sera enregistré dans `{out}` : nomme la classe et écris les chemins d'import en conséquence."
-    return extract_code(chat(system, user), fence)
+    return extract_code(chat(system, user, temperature=0.8), fence)
 
 
 def generate_other_language(args: argparse.Namespace, spec: str) -> int:
````

### `corriges/atelier-03/pieces/tests/generated/test_pricing_ai.py`

````python
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
````

### `docs/strategie-de-test.md`

Modification :

````diff
diff --git a/docs/strategie-de-test.md b/docs/strategie-de-test.md
index c801d9b..360a874 100644
--- a/docs/strategie-de-test.md
+++ b/docs/strategie-de-test.md
@@ -19,9 +19,26 @@
 | nocturne | charge, ZAP complet | p95 < 300 ms, erreurs < 1 % |
 
 ## 3. Règles pour les tests générés par IA
-- Un test généré est **relu** avant fusion (marqueur `@pytest.mark.generated`).
-- Il doit échouer si on casse la règle qu'il prétend vérifier (vérifié par mutation).
-- Pas de secret ni de donnée client dans les prompts.
+| # | Règle | Comment elle est vérifiée |
+|---|---|---|
+| 1 | Un test généré porte le marqueur `@pytest.mark.generated` et vit dans `tests/generated/`. | `pytest -m generated` les isole ; `pytest -m "not generated"` mesure la suite sans eux. |
+| 2 | Un test généré est **relu par un humain** avant fusion, comme du code : une PR, un relecteur qui connaît la règle métier. | Revue de PR. Le relecteur vérifie la **valeur attendue** de chaque `assert` contre la spécification, pas contre le code. |
+| 3 | Un test sans `assert` (ou qui ne peut pas échouer) est refusé. | Lecture, puis mutation : le test doit tuer au moins un mutant. |
+| 4 | Le score de mutation de `pricing.py` ne baisse pas quand on intègre des tests générés ; seuil visé : ≥ 80 %. | `python ai_tools/mutation_score.py minishop/pricing.py tests/unit` avant fusion. |
+| 5 | Un test généré qui échoue n'est **jamais** corrigé en recopiant la valeur renvoyée par le code. On tranche : bug de l'application (ticket), spécification fausse (on la corrige) ou hallucination (on supprime le test). | Le motif est écrit dans la PR. |
+| 6 | Aucun secret, aucune donnée client, aucune donnée de production dans un prompt. On n'envoie que la spécification et le code du module testé. | Prompts versionnés dans `ai_tools/prompts/` et relus ; jeux de données fictifs uniquement. |
+| 7 | Le fournisseur du modèle et le modèle sont choisis par l'équipe (`LLM_PROVIDER`, `LLM_MODEL`), avec une clé à quota limité stockée en secret. Code confidentiel : modèle local ou moteur offline. | Variables du workflow ; pas de clé personnelle. |
+| 8 | Le prompt est du code : toute modification passe par une PR, avec le tableau de comparaison (nombre de tests, échecs, couverture, mutation). | Historique Git de `ai_tools/prompts/`. |
+| 9 | Dans la pipeline, la génération **informe** et ne bloque pas (`continue-on-error`) ; les tests générés sont publiés en artefact et un humain décide de les intégrer. | Workflow `ai-tests.yml`. |
+
+**Responsabilité.** Une fois fusionné, un test généré appartient à l'équipe, au même titre qu'un test écrit
+à la main : la personne qui a ouvert la PR et celle qui l'a approuvée en répondent. « C'est l'IA qui l'a
+écrit » n'est pas une explication recevable. Un test généré faux découvert après coup se traite comme un
+défaut : ticket, correction, et vérification des autres tests issus de la même génération.
+
+**Régénération.** Les fichiers de `tests/generated/` produits par le moteur offline ne se modifient pas à la
+main : on corrige la spécification et on régénère. Un test généré par LLM que l'on a retouché sort de
+`tests/generated/` et rejoint `tests/unit/` (il perd le marqueur `generated`).
 
 ## 4. Gestion des tests instables (flaky)
 - Détection : `ai_tools/test_history.py` (score ≥ 0,6).
````

### `specs/pricing-etendue.feature`

````gherkin
# language: fr
# Spécification fonctionnelle du calcul de panier MiniShop.
# Source d'entrée de l'Atelier 3 : génération de tests par IA.
#
# Grammaire reconnue par le générateur hors-ligne :
#   Étant donné un panier avec <qty> "<produit>" [et <qty> "<produit>" ...]
#   Étant donné un panier vide
#   Quand j'applique le coupon "<CODE>"          (facultatif)
#   Quand je calcule le total
#   Alors le <champ> vaut <montant>               (champ : sous-total | remise | livraison | total)
#   Alors une erreur "<message partiel>" est levée

Fonctionnalité: Calcul du total d'un panier

  Scénario: Panier vide
    Étant donné un panier vide
    Quand je calcule le total
    Alors le total vaut 0.00
    Et la livraison vaut 0.00
    Et la remise vaut 0.00

  Scénario: Achat simple avec frais de livraison
    Étant donné un panier avec 2 "mug"
    Quand je calcule le total
    Alors le sous-total vaut 25.00
    Et la livraison vaut 4.90
    Et le total vaut 29.90

  Scénario: Livraison offerte à partir de 50 euros
    Étant donné un panier avec 1 "hoodie" et 1 "mug"
    Quand je calcule le total
    Alors la livraison vaut 0.00
    Et le total vaut 56.50

  Scénario: Remise volume dès 10 unités
    Étant donné un panier avec 10 "sticker"
    Quand je calcule le total
    Alors le sous-total vaut 23.28

  Scénario: Coupon de bienvenue
    Étant donné un panier avec 2 "mug"
    Quand j'applique le coupon "WELCOME10"
    Et je calcule le total
    Alors la remise vaut 2.50
    Et le total vaut 27.40

  Scénario: Coupon de bienvenue sous le seuil
    Étant donné un panier avec 1 "mug"
    Quand j'applique le coupon "WELCOME10"
    Et je calcule le total
    Alors la remise vaut 0.00

  Scénario: Coupon de livraison offerte
    Étant donné un panier avec 1 "sticker"
    Quand j'applique le coupon "FREESHIP"
    Et je calcule le total
    Alors la livraison vaut 0.00
    Et le total vaut 2.45

  Scénario: Coupon inconnu
    Étant donné un panier avec 1 "mug"
    Quand j'applique le coupon "NOEL2026"
    Et je calcule le total
    Alors une erreur "Coupon inconnu" est levée

  Scénario: Produit inconnu
    Étant donné un panier avec 1 "licorne"
    Quand je calcule le total
    Alors une erreur "Produit inconnu" est levée

  # --- Scénarios ajoutés pendant l'Atelier 3 (étape 1) ---

  Scénario: Coupon de 5 euros à partir de 30 euros
    Étant donné un panier avec 1 "book" et 1 "sticker"
    Quand j'applique le coupon "FIXED5"
    Et je calcule le total
    Alors le sous-total vaut 32.44
    Et la remise vaut 5.00
    Et la livraison vaut 4.90
    Et le total vaut 32.34

  Scénario: Remise volume cumulée avec le coupon de bienvenue
    Étant donné un panier avec 10 "mug"
    Quand j'applique le coupon "WELCOME10"
    Et je calcule le total
    Alors le sous-total vaut 118.75
    Et la remise vaut 11.88
    Et la livraison vaut 0.00
    Et le total vaut 106.87

  Scénario: Quantité nulle refusée
    Étant donné un panier avec 0 "mug"
    Quand je calcule le total
    Alors une erreur "Quantité hors limites" est levée

  Scénario: Livraison offerte à 50 euros exactement
    Étant donné un panier avec 4 "mug"
    Quand je calcule le total
    Alors le sous-total vaut 50.00
    Et la livraison vaut 0.00
    Et le total vaut 50.00

  Scénario: Arrondi commercial du demi-centime
    Étant donné un panier avec 10 "book"
    Quand je calcule le total
    Alors le sous-total vaut 284.91

  Scénario: Quantité maximale acceptée
    Étant donné un panier avec 99 "sticker"
    Quand je calcule le total
    Alors le sous-total vaut 230.42

  Scénario: Quantité au-delà du maximum refusée
    Étant donné un panier avec 100 "sticker"
    Quand je calcule le total
    Alors une erreur "Quantité hors limites" est levée
````

### `specs/pricing.feature`

Modification :

````diff
diff --git a/specs/pricing.feature b/specs/pricing.feature
index bb29930..5ad8ab6 100644
--- a/specs/pricing.feature
+++ b/specs/pricing.feature
@@ -66,3 +66,28 @@ Fonctionnalité: Calcul du total d'un panier
     Étant donné un panier avec 1 "licorne"
     Quand je calcule le total
     Alors une erreur "Produit inconnu" est levée
+
+  # --- Scénarios ajoutés pendant l'Atelier 3 (étape 1) ---
+
+  Scénario: Coupon de 5 euros à partir de 30 euros
+    Étant donné un panier avec 1 "book" et 1 "sticker"
+    Quand j'applique le coupon "FIXED5"
+    Et je calcule le total
+    Alors le sous-total vaut 32.44
+    Et la remise vaut 5.00
+    Et la livraison vaut 4.90
+    Et le total vaut 32.34
+
+  Scénario: Remise volume cumulée avec le coupon de bienvenue
+    Étant donné un panier avec 10 "mug"
+    Quand j'applique le coupon "WELCOME10"
+    Et je calcule le total
+    Alors le sous-total vaut 118.75
+    Et la remise vaut 11.88
+    Et la livraison vaut 0.00
+    Et le total vaut 106.87
+
+  Scénario: Quantité nulle refusée
+    Étant donné un panier avec 0 "mug"
+    Quand je calcule le total
+    Alors une erreur "Quantité hors limites" est levée
````

### `tests/generated/test_pricing_offline.py`

````python
"""Tests générés automatiquement depuis pricing.feature (moteur : offline).

NE PAS MODIFIER À LA MAIN : régénérer avec ai_tools/generate_tests.py
"""

from decimal import Decimal

import pytest

from minishop.pricing import quote

pytestmark = [pytest.mark.generated, pytest.mark.unit]


def test_panier_vide():
    """Panier vide"""
    q = quote([], None)
    assert q.total == Decimal("0.00")
    assert q.shipping == Decimal("0.00")


def test_achat_simple_avec_frais_de_livraison():
    """Achat simple avec frais de livraison"""
    q = quote([{"product_id": "mug", "qty": 2}], None)
    assert q.subtotal == Decimal("25.00")
    assert q.shipping == Decimal("4.90")
    assert q.total == Decimal("29.90")


def test_livraison_offerte_a_partir_de_50_euros():
    """Livraison offerte à partir de 50 euros"""
    q = quote([{"product_id": "hoodie", "qty": 1}, {"product_id": "mug", "qty": 1}], None)
    assert q.shipping == Decimal("0.00")
    assert q.total == Decimal("56.50")


def test_remise_volume_des_10_unites():
    """Remise volume dès 10 unités"""
    q = quote([{"product_id": "sticker", "qty": 10}], None)
    assert q.subtotal == Decimal("23.28")


def test_coupon_de_bienvenue():
    """Coupon de bienvenue"""
    q = quote([{"product_id": "mug", "qty": 2}], "WELCOME10")
    assert q.discount == Decimal("2.50")
    assert q.total == Decimal("27.40")


def test_coupon_de_bienvenue_sous_le_seuil():
    """Coupon de bienvenue sous le seuil"""
    q = quote([{"product_id": "mug", "qty": 1}], "WELCOME10")
    assert q.discount == Decimal("0.00")


def test_coupon_de_livraison_offerte():
    """Coupon de livraison offerte"""
    q = quote([{"product_id": "sticker", "qty": 1}], "FREESHIP")
    assert q.shipping == Decimal("0.00")
    assert q.total == Decimal("2.45")


def test_coupon_inconnu():
    """Coupon inconnu"""
    with pytest.raises(ValueError, match="Coupon inconnu"):
        quote([{"product_id": "mug", "qty": 1}], "NOEL2026")


def test_produit_inconnu():
    """Produit inconnu"""
    with pytest.raises(KeyError, match="Produit inconnu"):
        quote([{"product_id": "licorne", "qty": 1}], None)


def test_coupon_de_5_euros_a_partir_de_30_euros():
    """Coupon de 5 euros à partir de 30 euros"""
    q = quote([{"product_id": "book", "qty": 1}, {"product_id": "sticker", "qty": 1}], "FIXED5")
    assert q.subtotal == Decimal("32.44")
    assert q.discount == Decimal("5.00")
    assert q.shipping == Decimal("4.90")
    assert q.total == Decimal("32.34")


def test_remise_volume_cumulee_avec_le_coupon_de_bienvenue():
    """Remise volume cumulée avec le coupon de bienvenue"""
    q = quote([{"product_id": "mug", "qty": 10}], "WELCOME10")
    assert q.subtotal == Decimal("118.75")
    assert q.discount == Decimal("11.88")
    assert q.shipping == Decimal("0.00")
    assert q.total == Decimal("106.87")


def test_quantite_nulle_refusee():
    """Quantité nulle refusée"""
    with pytest.raises(ValueError, match="Quantité hors limites"):
        quote([{"product_id": "mug", "qty": 0}], None)
````
