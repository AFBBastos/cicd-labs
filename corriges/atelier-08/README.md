# Atelier 8 — Tests fonctionnels UI de bout en bout : corrigé

**Durée : 2 h 30** · Module 3

Objectif : automatiser les parcours utilisateur de MiniShop avec Playwright, les rendre fiables et
lisibles (Page Object), les comparer à Selenium, et les exécuter dans la CI sur deux navigateurs avec
des traces exploitables en cas d'échec.

Tout a été exécuté dans l'image `mcr.microsoft.com/playwright/python:v1.65.2-noble` (Playwright 1.65.2,
pytest 9.2.0, Selenium 4.52.0), sans interface graphique, contre l'application lancée depuis une copie
du dépôt.

## Le résultat à atteindre

| Vérification | Résultat mesuré |
|---|---|
| Test de départ (`pytest -m e2e`) | 1 passed |
| Solution `test_parcours_achat.py`, Chromium | 4 passed en 1,2 s |
| Même fichier, Chromium + Firefox | 8 passed en 5,8 s ; WebKit : 4 passed |
| Version Page Object `test_parcours_achat_pom.py` | 4 passed (Chromium), 4 passed (Firefox) |
| Test Selenium `test_selenium_accueil.py` | 2 passed (Chrome 157 téléchargé par Selenium Manager) |
| Tous les tests `e2e` ensemble, `pytest -m e2e -n 2` | 10 passed |
| `time.sleep` dans `tests/e2e/` | aucun |
| Workflow `e2e-visual.yml` | actionlint : aucune remarque |
| `data-testid` cassé | 2 failed, 2 passed en 62 s ; une trace, une vidéo et une capture par test en échec |

Fichiers de solution : `formateur/solutions/atelier-08/tests/e2e/`

- `test_parcours_achat.py` : les parcours demandés (4 tests) ;
- `shop_page.py` et `test_parcours_achat_pom.py` : la classe `ShopPage` et les tests qui l'utilisent ;
- `test_selenium_accueil.py` : le test Selenium de la partie B.

Workflow : `formateur/solutions/workflows/e2e-visual.yml` (job `e2e`).

## Partie A — Playwright

### 1. Lancer le test fourni

```bash
pytest -m e2e --headed --slowmo 300
```

```text
tests/e2e/test_parcours_achat.py::test_page_accueil[chromium] PASSED
```

`--headed` ouvre un vrai navigateur, `--slowmo 300` ralentit chaque action de 300 ms pour qu'on puisse
suivre. Le `[chromium]` dans le nom du test vient de `pytest-playwright` : chaque test est paramétré par
navigateur. L'adresse de l'application vient de la fixture `app_url` (`tests/conftest.py`), qui lit la
variable `BASE_URL` et vaut `http://localhost:8000` par défaut.

### 2. Enregistrer un parcours

```bash
playwright codegen http://localhost:8000
```

Le code produit est un brouillon. Ce qu'il faut y reprendre systématiquement :

- il n'y a **aucune assertion** : codegen enregistre des gestes, pas des attentes ;
- l'adresse est écrite en dur : la remplacer par la fixture `app_url` ;
- les localisateurs sont ceux que l'outil a jugés les meilleurs, pas forcément ceux que l'équipe a
  choisis : les relire un par un ;
- tout est dans une seule fonction : découper en tests indépendants.

### 3 et 4. Les trois parcours et les bonnes pratiques

Solution : `formateur/solutions/atelier-08/tests/e2e/test_parcours_achat.py`.

```bash
pytest tests/e2e/test_parcours_achat.py -v
```

```text
tests/e2e/test_parcours_achat.py::test_page_accueil[chromium] PASSED     [ 25%]
tests/e2e/test_parcours_achat.py::test_parcours_achat_avec_coupon[chromium] PASSED [ 50%]
tests/e2e/test_parcours_achat.py::test_coupon_invalide_affiche_erreur[chromium] PASSED [ 75%]
tests/e2e/test_parcours_achat.py::test_commander_desactive_tant_que_le_panier_est_vide[chromium] PASSED [100%]
======================== 4 passed, 2 warnings in 1.21s =========================
```

Le cœur de la solution :

```python
@pytest.fixture
def shop(page: Page, app_url):
    page.goto(app_url)
    expect(page.get_by_test_id("products").locator("li")).to_have_count(5)
    return page


def test_parcours_achat_avec_coupon(shop: Page):
    shop.get_by_test_id("add-mug").click()
    shop.get_by_test_id("add-mug").click()
    expect(shop.get_by_test_id("cart-mug")).to_have_text(re.compile("× 2"))
    shop.get_by_test_id("coupon").fill("WELCOME10")
    shop.get_by_test_id("quote-btn").click()
    expect(shop.get_by_test_id("total")).to_have_text("27.40")
    shop.get_by_test_id("order-btn").click()
    expect(shop.get_by_test_id("confirmation")).to_have_text(re.compile(r"^Commande [0-9a-f]{12} confirmée$"))


def test_commander_desactive_tant_que_le_panier_est_vide(shop: Page):
    expect(shop.get_by_test_id("order-btn")).to_be_disabled()
    shop.get_by_test_id("add-mug").click()
    expect(shop.get_by_test_id("order-btn")).to_be_enabled()
```

Comment chaque bonne pratique de l'énoncé y est appliquée :

| Pratique | Dans la solution |
|---|---|
| Localisateurs par rôle, texte ou `data-testid` | `get_by_test_id(...)`, `get_by_role("alert")` ; aucun XPath, aucune classe CSS |
| Assertions « web-first » | `expect(...).to_have_text(...)` réessaie jusqu'à 5 s ; aucun `time.sleep` (`grep -n sleep tests/e2e/*.py` ne renvoie rien) |
| Fixture `shop` | ouvre la page **et attend les 5 produits** : le catalogue arrive par un appel à `/products` après l'affichage |
| Tests indépendants | `pytest-playwright` donne à chaque test un contexte de navigateur neuf (panier vide) ; aucun test ne dépend d'un autre |

Le total attendu se calcule à la main : 2 mugs à 12,50 € = 25,00 € ; WELCOME10 retire 10 % (2,50 €) ;
livraison 4,90 € ; total 27,40 €.

Deux détails de la solution à faire remarquer :

- le bouton « Commander » est vérifié dans les deux sens : désactivé panier vide, **réactivé** après un
  ajout. Vérifier seulement l'état de départ laisserait passer un bouton qui ne se réactive jamais ;
- la confirmation est vérifiée en entier, identifiant de commande compris (12 caractères
  hexadécimaux) : `to_contain_text("confirmée")` accepterait n'importe quel message contenant ce mot.

### 5. Page Object

Fichiers : `formateur/solutions/atelier-08/tests/e2e/shop_page.py` et `test_parcours_achat_pom.py`.

```python
class ShopPage:
    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url

    def open(self) -> ShopPage:
        self.page.goto(self.base_url)
        expect(self.products).to_have_count(5)
        return self

    def add(self, product: str, qty: int = 1) -> ShopPage:
        for _ in range(qty):
            self.page.get_by_test_id(f"add-{product}").click()
        return self

    def apply_coupon(self, code: str) -> ShopPage:
        self.page.get_by_label("Code promo").fill(code)
        return self.compute()

    def compute(self) -> ShopPage:
        self.page.get_by_role("button", name="Calculer le total").click()
        return self

    def order(self) -> ShopPage:
        self.order_button.click()
        return self

    def total(self) -> Locator:
        return self.page.get_by_test_id("total")
```

Les tests se lisent alors comme la règle de gestion :

```python
def test_parcours_achat_avec_coupon(shop: ShopPage):
    shop.add("mug", qty=2)
    expect(shop.cart_line("mug")).to_have_text(re.compile("× 2"))
    shop.apply_coupon("WELCOME10")
    expect(shop.total()).to_have_text("27.40")
    shop.order()
    expect(shop.confirmation).to_have_text(re.compile(r"^Commande [0-9a-f]{12} confirmée$"))


def test_commander_desactive_tant_que_le_panier_est_vide(shop: ShopPage):
    expect(shop.order_button).to_be_disabled()
    shop.add("mug")
    expect(shop.order_button).to_be_enabled()
```

```bash
pytest tests/e2e/test_parcours_achat_pom.py -v
```

```text
tests/e2e/test_parcours_achat_pom.py::test_page_accueil[chromium] PASSED [ 25%]
tests/e2e/test_parcours_achat_pom.py::test_parcours_achat_avec_coupon[chromium] PASSED [ 50%]
tests/e2e/test_parcours_achat_pom.py::test_coupon_invalide_affiche_erreur[chromium] PASSED [ 75%]
tests/e2e/test_parcours_achat_pom.py::test_commander_desactive_tant_que_le_panier_est_vide[chromium] PASSED [100%]
======================== 4 passed, 2 warnings in 1.31s =========================
```

Choix de conception à expliquer :

- **`total()` renvoie un localisateur, pas une chaîne.** Si la méthode renvoyait le texte, le test
  ferait `assert shop.total() == "27.40"` : une lecture immédiate, sans nouvel essai, qui échoue quand
  la réponse de l'API n'est pas encore affichée. En renvoyant le localisateur, on garde
  `expect(...).to_have_text(...)`. La règle : le Page Object décrit la page, l'assertion reste dans le
  test.
- **Les localisateurs passent au rôle et au libellé** là où c'est possible (`get_by_label("Code promo")`,
  `get_by_role("button", name="Calculer le total")`). Les boutons « Ajouter » portent tous le même nom :
  le `data-testid` reste le bon choix pour eux. Suite directe de la partie C de l'atelier 7.
- **Les actions renvoient `self`** : on peut écrire `shop.add("tshirt").apply_coupon("NOEL")`.
- **Un seul endroit à corriger** quand l'interface change : c'est l'argument à faire sentir, en
  renommant un `data-testid` et en comptant les lignes à modifier dans chaque version.

Import : `tests/e2e/` n'a pas de `__init__.py` ; pytest ajoute alors le dossier du test au chemin
d'import, et `from shop_page import ShopPage` fonctionne tel quel (vérifié).

## Partie B — Selenium, pour comparer

```bash
pip install selenium
pytest tests/e2e/test_selenium_accueil.py -v
```

```text
tests/e2e/test_selenium_accueil.py::test_titre_de_la_page PASSED         [ 50%]
tests/e2e/test_selenium_accueil.py::test_ajout_d_un_produit_au_panier PASSED [100%]
======================== 2 passed, 1 warning in 13.98s =========================
```

Les 14 secondes sont celles du premier lancement (14,0 et 14,5 s sur deux essais) : Selenium Manager a téléchargé Chrome et
`chromedriver` (version 157.0.8103.78, 431 Mo dans `~/.cache/selenium`). Les lancements suivants
prennent 1,8 s.

Fichier : `formateur/solutions/atelier-08/tests/e2e/test_selenium_accueil.py`. L'essentiel :

```python
def css(testid):
    return By.CSS_SELECTOR, f'[data-testid="{testid}"]'


@pytest.fixture
def driver():
    options = webdriver.ChromeOptions()
    if os.getenv("SELENIUM_HEADED") != "1":
        options.add_argument("--headless=new")
    ...
    drv = webdriver.Chrome(options=options)
    yield drv
    drv.quit()


def test_ajout_d_un_produit_au_panier(driver, app_url):
    driver.get(app_url)
    wait = WebDriverWait(driver, 10)
    wait.until(EC.element_to_be_clickable(css("add-mug"))).click()
    ligne = wait.until(EC.visibility_of_element_located(css("cart-mug")))
    assert ligne.text.endswith("× 1")
    assert driver.find_element(*css("order-btn")).is_enabled()
```

Ce qui a manqué par rapport à Playwright :

- **les attentes sont à écrire soi-même** (`WebDriverWait` + `expected_conditions`). Rien n'attend que
  le bouton existe, soit visible et cliquable avant le clic. Constat à partager : sur une machine
  rapide, le test passe même **sans** attente (10 essais sur 10 lors de la vérification, l'appel à
  `/products` étant terminé avant le premier `find_element`). C'est le piège : le test est juste par
  chance, et deviendra instable le jour où le serveur répondra plus lentement ;
- **pas de `get_by_test_id`, `get_by_role`, `get_by_label`** : il faut écrire un sélecteur CSS ;
- **pas d'assertion qui réessaie** : `assert ligne.text...` lit une fois ;
- **pas de fixture fournie** : création et fermeture du navigateur à la main (`yield` puis `quit()`),
  options du mode sans interface, `--no-sandbox` sous root dans un conteneur ;
- **pas de trace, pas de vidéo** : en cas d'échec, une exception et, au mieux, une capture qu'on aura
  pensé à prendre ;
- **un navigateur complet à télécharger** par version de pilote, là où Playwright livre les siens.

Le module commence par `pytest.importorskip("selenium")` : là où Selenium n'est pas installé (le
workflow de CI n'installe que `requirements-dev.txt`), le fichier est « skipped » au lieu de faire
échouer la collecte de `pytest -m e2e` (vérifié dans un environnement sans Selenium : `1 skipped`).

Cypress (optionnel) : non traité dans ce corrigé, voir « Non vérifié ».

## Partie C — Dans la CI

La solution est le job `e2e` de `formateur/solutions/workflows/e2e-visual.yml`, qui regroupe les
ateliers 7 et 8 ; actionlint ne relève rien. Lecture du job, étape par étape :

| Élément | Rôle |
|---|---|
| `strategy.matrix.browser: [chromium, firefox]` | deux jobs en parallèle, un par navigateur |
| `python -m playwright install --with-deps ${{ matrix.browser }}` | n'installe que le navigateur du job, avec ses bibliothèques système (`--with-deps`, Linux seulement) |
| `uvicorn minishop.api:app --port 8000 &` | démarre l'application en arrière-plan ; l'étape se termine, le processus reste |
| `timeout 30 bash -c 'until curl -sf localhost:8000/health; do sleep 1; done'` | **attend** que l'application réponde, 30 s au plus. Sans cette ligne, les tests peuvent démarrer avant que le serveur écoute |
| `pytest -m e2e --browser ${{ matrix.browser }}` | les mêmes tests, sur le navigateur du job |
| `--tracing retain-on-failure --screenshot only-on-failure --video retain-on-failure --output test-results` | enregistre tout, ne garde que ce qui concerne les tests en échec |
| `--junitxml=reports/e2e-${{ matrix.browser }}.xml` | un rapport par navigateur |
| `upload-artifact` avec `if: failure()` | publie `test-results/` seulement en cas d'échec ; le nom de l'artefact porte le navigateur, sinon les deux jobs s'écraseraient |
| `permissions: contents: read` | le jeton du workflow ne peut que lire le dépôt |
| `if: github.event_name != 'workflow_dispatch'` | le lancement manuel du workflow est réservé à la régénération des références visuelles (atelier 7) : les tests E2E ne tournent pas à cette occasion |

Le `sleep 1` de la boucle d'attente n'est pas un `sleep` de test : il cadence une attente bornée sur une
condition, ce qui est exactement ce que font les assertions « web-first ».

Vérifié en local, faute de runner : les tests passent sur les deux navigateurs de la matrice.

```bash
pytest tests/e2e/test_parcours_achat.py --browser chromium --browser firefox
```

```text
8 passed, 2 warnings in 5.75s
```

**Parallélisation.**

```bash
pytest -m e2e -n 2
```

```text
10 passed, 5 warnings in 4.18s
```

(10 tests : les trois fichiers de solution ensemble.) Cela fonctionne ici parce que chaque test a son
propre contexte de navigateur et que chaque commande reçoit un identifiant aléatoire : aucun test ne lit
une donnée écrite par un autre. Le jour où un test vérifie « il y a 1 commande en base » ou compte sur
un stock, la parallélisation le fera échouer de temps en temps. Règle : chaque test crée ses données et
ne suppose rien de l'état global.

### Casser l'interface et diagnostiquer avec la trace

Dans `minishop/static/index.html`, renommer `data-testid="quote-btn"` en `data-testid="compute-btn"`,
puis lancer comme la CI :

```bash
pytest tests/e2e/test_parcours_achat.py --tracing retain-on-failure --video retain-on-failure \
    --screenshot only-on-failure --output test-results
```

```text
E   playwright._impl._errors.TimeoutError: Locator.click: Timeout 30000ms exceeded.
E   Call log:
E     - waiting for get_by_test_id("quote-btn")
FAILED tests/e2e/test_parcours_achat.py::test_parcours_achat_avec_coupon[chromium]
FAILED tests/e2e/test_parcours_achat.py::test_coupon_invalide_affiche_erreur[chromium]
2 failed, 2 passed, 2 warnings in 62.51s (0:01:02)
```

Un dossier par test en échec, rien pour les tests réussis :

```text
test-results/tests-e2e-test-parcours-achat-py-test-parcours-achat-avec-coupon-chromium/
    test-failed-1.png    (53 Ko)
    trace.zip            (1,4 Mo)
    video.webm           (775 Ko)
```

```bash
playwright show-trace test-results/…/trace.zip      # ou déposer le fichier sur https://trace.playwright.dev
```

Démarche de diagnostic, sans relire le code de l'application :

1. **La liste des actions** (colonne de gauche). Dans la trace produite : `goto`, l'attente des 5
   produits, deux `click` sur `add-mug`, l'assertion sur `cart-mug`, `fill` du coupon, tous réussis ;
   puis un `click` en erreur sur `get_by_test_id("quote-btn")`, « Timeout 30000ms exceeded ». On sait
   déjà que l'application répond, que le catalogue s'affiche et que le panier fonctionne.
2. **Le journal de l'action en échec** (onglet *Log*). Pour les clics réussis : « locator resolved to
   `<button data-testid="add-mug">` », puis les vérifications (visible, activé, stable). Pour le clic en
   échec, une seule ligne : « waiting for get_by_test_id("quote-btn") ». Le bouton n'a donc pas été
   trouvé ; ce n'est pas un bouton caché ou désactivé, cas où le journal le dirait.
3. **L'instantané du DOM** au moment de l'action (onglets *Before* / *After*). C'est une vraie page,
   qu'on inspecte : le bouton « Calculer le total » est bien là, avec `data-testid="compute-btn"`.
   L'instantané enregistré dans la trace contient cet attribut.
4. **L'onglet réseau** : trois requêtes (`/`, `/static/style.css`, `/products`), aucune erreur. Le
   serveur n'est pas en cause.

Conclusion : l'identifiant a été renommé côté interface. Reste la question qui ne se lit pas dans la
trace : est-ce le test qu'il faut adapter, ou le renommage qui est une erreur ?

La vidéo et la capture montrent le même état final ; la trace est la seule à dire **pourquoi**. Coût de
la panne : 30 s d'attente par test en échec, d'où l'intérêt de garder des délais raisonnables.

## Comparatif Selenium / Playwright / Cypress

| | Selenium | Playwright | Cypress |
|---|---|---|---|
| Langages | Java, Python, C#, JavaScript, Ruby… | Python, JavaScript/TypeScript, Java, C# | JavaScript/TypeScript seulement |
| Navigateurs | Tous, via un pilote par navigateur (protocole WebDriver, norme W3C) | Chromium, Firefox, WebKit, livrés avec l'outil | Chromium, Firefox, WebKit en mode expérimental |
| Attentes | À écrire (`WebDriverWait`) | Automatiques avant chaque action, assertions qui réessaient | Automatiques, commandes qui réessaient |
| Diagnostic d'un échec | Exception, capture à prendre soi-même | Trace complète (actions, DOM, réseau), vidéo, capture | Lecteur interactif avec retour dans le temps, vidéo, capture |
| À retenir | Le standard historique, le plus large en langages et en grilles de navigateurs ; le plus verbeux | Le plus complet pour un projet neuf ; plusieurs onglets, contextes isolés, parallélisme inclus | Très agréable en développement d'interface ; s'exécute dans le navigateur, d'où des limites (plusieurs onglets, plusieurs domaines) |

Les colonnes Selenium et Playwright s'appuient sur ce qui a été exécuté dans cet atelier ; la colonne
Cypress est rédigée de mémoire (voir « Non vérifié »).

## Points d'animation

- **Durée à surveiller.** La partie A absorbe facilement 1 h 30 si les stagiaires peaufinent le code
  de codegen. Fixer une limite de 10 minutes à l'enregistrement. La partie B dépend du réseau : le
  premier lancement de Selenium télécharge plus de 400 Mo.
- **Application non lancée.** Erreur la plus fréquente : `net::ERR_CONNECTION_REFUSED`. Rappeler le
  second terminal avec `make run`.
- **Assertion immédiate au lieu de web-first.** `assert page.get_by_test_id("total").inner_text() == "27.40"`
  lit la valeur une seule fois : si la réponse de l'API n'est pas encore affichée, il lit une chaîne
  vide et échoue. Faire remplacer par `expect(...).to_have_text(...)`, qui réessaie jusqu'au délai.
- **`time.sleep` « pour être sûr ».** Le refuser à la relecture ; demander quelle condition on attend
  réellement, et l'écrire.
- **Mauvais total attendu.** Certains oublient la livraison (22,50 au lieu de 27,40). Faire refaire le
  calcul à la main.
- **`get_by_role("button", name="Ajouter")`** lève une erreur de mode strict : cinq boutons portent ce
  nom. Bonne occasion d'expliquer pourquoi le `data-testid` existe.
- **Page Object qui contient les assertions.** Tendance naturelle (`shop.check_total("27.40")`).
  Discussion : qui décide de ce qui est attendu, la page ou le test ?
- **Discussion : rôle, texte ou `data-testid` ?** Rôle et libellé quand ils sont uniques et stables ;
  `data-testid` pour les éléments répétés ou sans nom ; jamais la structure (XPath, classes).
- **Discussion : combien de tests E2E ?** Peu : les parcours qui rapportent de l'argent. Les cas
  d'erreur (coupon inconnu, quantités) se testent mieux au niveau API (atelier 9), dix fois plus vite.
- **Discussion : trace toujours ou seulement en échec ?** `retain-on-failure` : l'enregistrement a un
  coût, mais une trace absente le jour de l'échec intermittent coûte plus cher.

## Non vérifié

- **`--headed --slowmo 300` et `playwright codegen`** : aucun écran disponible ; les tests ont été
  exécutés sans interface, les conseils sur codegen viennent de la connaissance de l'outil.
- **`playwright show-trace` et trace.playwright.dev** : le visualiseur n'a pas été ouvert. Le contenu
  de `trace.zip` a été lu directement (liste des actions, journal, erreur, présence de
  `data-testid="compute-btn"` dans l'instantané, trois requêtes réseau) ; la description des onglets
  repose sur la connaissance de l'outil.
- **Exécution réelle dans GitHub Actions** : workflow validé par actionlint et commandes rejouées en
  local, mais aucun runner n'a été utilisé ; le téléchargement de l'artefact n'a pas été testé.
- **Cypress** : non installé, non exécuté ; la colonne du comparatif est rédigée de mémoire.
- **Selenium sur un poste** (Windows, macOS, Chrome déjà installé) : vérifié seulement dans le
  conteneur Linux, sous root, avec le Chrome téléchargé par Selenium Manager.
- **Grilles cloud et tests d'accessibilité** (« Pour aller plus loin ») : non traités.

---

## Fichiers de cet atelier

Par rapport à la branche `python/atelier-07` :

| | Fichier |
|---|---|
| ajouté | `.github/workflows/e2e-visual.yml` |
| ajouté | `tests/e2e/shop_page.py` |
| modifié | `tests/e2e/test_parcours_achat.py` |
| ajouté | `tests/e2e/test_parcours_achat_pom.py` |
| ajouté | `tests/e2e/test_selenium_accueil.py` |
| ajouté | `tests/visual/baselines/accueil-chromium.png` |
| ajouté | `tests/visual/baselines/panier-chromium.png` |

### `.github/workflows/e2e-visual.yml`

````yaml
# SOLUTION Ateliers 7 & 8 — Tests E2E et visuels (Playwright)
name: E2E & visuel

on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:   # lancement manuel : régénère les références visuelles (job « baselines »)

permissions:
  contents: read

jobs:
  e2e:
    if: github.event_name != 'workflow_dispatch'
    runs-on: ubuntu-latest
    strategy:
      matrix:
        browser: [chromium, firefox]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12", cache: pip }
      - run: pip install -r requirements-dev.txt
      - run: python -m playwright install --with-deps ${{ matrix.browser }}
      - name: Démarrer l'application
        run: |
          uvicorn minishop.api:app --port 8000 &
          timeout 30 bash -c 'until curl -sf localhost:8000/health; do sleep 1; done'
      - name: Tests E2E
        run: >
          pytest -m e2e --browser ${{ matrix.browser }}
          --tracing retain-on-failure --screenshot only-on-failure --video retain-on-failure
          --output test-results --junitxml=reports/e2e-${{ matrix.browser }}.xml
      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: playwright-traces-${{ matrix.browser }}   # ouvrir avec : playwright show-trace trace.zip
          path: test-results/

  visual:
    if: github.event_name != 'workflow_dispatch'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12", cache: pip }
      - run: pip install -r requirements-dev.txt
      - run: python -m playwright install --with-deps chromium
      - run: |
          uvicorn minishop.api:app --port 8000 &
          timeout 30 bash -c 'until curl -sf localhost:8000/health; do sleep 1; done'
      - name: Régression visuelle
        shell: bash   # active pipefail : un échec de pytest n'est pas masqué par tee
        run: |
          pytest -m visual -rs | tee visual.log
          # Sans référence commitée, le test crée la référence et se déclare « skipped » :
          # rien n'a été comparé. Un job vert serait trompeur, on échoue explicitement.
          if grep -q "Baseline créée" visual.log; then
            msg="Référence visuelle absente : rien n'a été comparé. Lancez ce workflow à la main (Run workflow), téléchargez l'artefact visual-baselines et commitez son contenu dans tests/visual/baselines/."
            echo "::error::$msg"
            echo "$msg" >> "$GITHUB_STEP_SUMMARY"
            exit 1
          fi
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: visual-diffs
          path: |
            tests/visual/baselines/
            tests/visual/current/
            tests/visual/diff/

  # Références générées dans l'environnement où elles seront comparées (jamais sur un poste).
  baselines:
    if: github.event_name == 'workflow_dispatch'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12", cache: pip }
      - run: pip install -r requirements-dev.txt
      - run: python -m playwright install --with-deps chromium
      - run: |
          uvicorn minishop.api:app --port 8000 &
          timeout 30 bash -c 'until curl -sf localhost:8000/health; do sleep 1; done'
      - name: Régénérer les références
        run: pytest -m visual -rs
        env:
          UPDATE_BASELINES: "1"
      - uses: actions/upload-artifact@v4
        with:
          name: visual-baselines   # à regarder, puis à commiter dans tests/visual/baselines/
          path: tests/visual/baselines/*.png
          if-no-files-found: error
````

### `tests/e2e/shop_page.py`

````python
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
````

### `tests/e2e/test_parcours_achat.py`

Modification :

````diff
diff --git a/tests/e2e/test_parcours_achat.py b/tests/e2e/test_parcours_achat.py
index b066c26..584e803 100644
--- a/tests/e2e/test_parcours_achat.py
+++ b/tests/e2e/test_parcours_achat.py
@@ -1,8 +1,4 @@
-"""Test E2E Playwright — POINT DE DÉPART (Atelier 8).
-
-Prérequis : application lancée (make run) ; BASE_URL=http://localhost:8000 par défaut.
-Lancer :   pytest -m e2e --headed        (pour voir le navigateur)
-"""
+"""Tests E2E Playwright — SOLUTION Atelier 8."""
 
 import re
 
@@ -12,10 +8,37 @@ from playwright.sync_api import Page, expect
 pytestmark = pytest.mark.e2e
 
 
-def test_page_accueil(page: Page, app_url):
+@pytest.fixture
+def shop(page: Page, app_url):
     page.goto(app_url)
-    expect(page).to_have_title(re.compile("MiniShop"))
     expect(page.get_by_test_id("products").locator("li")).to_have_count(5)
+    return page
+
+
+def test_page_accueil(shop: Page):
+    expect(shop).to_have_title(re.compile("MiniShop"))
+    expect(shop.get_by_test_id("order-btn")).to_be_disabled()
+
+
+def test_parcours_achat_avec_coupon(shop: Page):
+    shop.get_by_test_id("add-mug").click()
+    shop.get_by_test_id("add-mug").click()
+    expect(shop.get_by_test_id("cart-mug")).to_have_text(re.compile("× 2"))
+    shop.get_by_test_id("coupon").fill("WELCOME10")
+    shop.get_by_test_id("quote-btn").click()
+    expect(shop.get_by_test_id("total")).to_have_text("27.40")
+    shop.get_by_test_id("order-btn").click()
+    expect(shop.get_by_test_id("confirmation")).to_have_text(re.compile(r"^Commande [0-9a-f]{12} confirmée$"))
+
+
+def test_coupon_invalide_affiche_erreur(shop: Page):
+    shop.get_by_test_id("add-tshirt").click()
+    shop.get_by_test_id("coupon").fill("NOEL")
+    shop.get_by_test_id("quote-btn").click()
+    expect(shop.get_by_role("alert")).to_contain_text("Coupon inconnu")
 
 
-# TODO Atelier 8 : ajouter 2 mugs, appliquer WELCOME10, vérifier le total, commander.
+def test_commander_desactive_tant_que_le_panier_est_vide(shop: Page):
+    expect(shop.get_by_test_id("order-btn")).to_be_disabled()
+    shop.get_by_test_id("add-mug").click()
+    expect(shop.get_by_test_id("order-btn")).to_be_enabled()
````

### `tests/e2e/test_parcours_achat_pom.py`

````python
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
````

### `tests/e2e/test_selenium_accueil.py`

````python
"""Test Selenium de la page d'accueil — SOLUTION Atelier 8 (partie B).

Prérequis : `pip install selenium`, application lancée, Chrome installé (sinon
Selenium Manager le télécharge au premier lancement, avec le pilote chromedriver).
Lancer :   pytest tests/e2e/test_selenium_accueil.py
Voir le navigateur :   SELENIUM_HEADED=1 pytest tests/e2e/test_selenium_accueil.py

Ce qui change par rapport à Playwright : rien n'attend à notre place. Le catalogue est
chargé par un appel réseau après l'affichage de la page : c'est au test de dire ce qu'il
attend, avec `WebDriverWait`. Sans cette attente, un `find_element` lancé avant la fin du
chargement lève `NoSuchElementException` (sur un poste rapide, il passe par chance).

Le module est ignoré (« skipped ») si Selenium n'est pas installé : il ne casse donc pas
`pytest -m e2e` dans un environnement qui n'a que Playwright, comme le workflow de CI.
"""

import os

import pytest

pytest.importorskip("selenium")

from selenium import webdriver  # noqa: E402
from selenium.webdriver.common.by import By  # noqa: E402
from selenium.webdriver.support import expected_conditions as EC  # noqa: E402
from selenium.webdriver.support.ui import WebDriverWait  # noqa: E402

pytestmark = pytest.mark.e2e


def css(testid: str) -> tuple[str, str]:
    return By.CSS_SELECTOR, f'[data-testid="{testid}"]'


@pytest.fixture
def driver():
    options = webdriver.ChromeOptions()
    if os.getenv("SELENIUM_HEADED") != "1":
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1280,800")
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        options.add_argument("--no-sandbox")  # Chrome refuse le bac à sable sous root (conteneur, CI)
    drv = webdriver.Chrome(options=options)
    yield drv
    drv.quit()


def test_titre_de_la_page(driver, app_url):
    driver.get(app_url)
    assert "MiniShop" in driver.title
    assert driver.find_element(*css("title")).text == "MiniShop"


def test_ajout_d_un_produit_au_panier(driver, app_url):
    driver.get(app_url)
    wait = WebDriverWait(driver, 10)

    # Attente explicite : le bouton n'existe qu'une fois /products chargé.
    wait.until(EC.element_to_be_clickable(css("add-mug"))).click()

    ligne = wait.until(EC.visibility_of_element_located(css("cart-mug")))
    assert ligne.text.endswith("× 1")
    assert driver.find_element(*css("order-btn")).is_enabled()
````

### `tests/visual/baselines/accueil-chromium.png`

Fichier binaire (image).

### `tests/visual/baselines/panier-chromium.png`

Fichier binaire (image).
