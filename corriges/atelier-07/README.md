# Atelier 7 — Tests visuels et outils « AI-powered » : corrigé

**Durée : 2 h** · Module 2

Objectif : détecter une régression d'interface par comparaison d'images, comprendre ce que mesure
chaque indicateur (pixels, SSIM), savoir où générer les références, et situer les outils du marché.

Toutes les mesures de ce corrigé ont été prises dans l'image
`mcr.microsoft.com/playwright/python:v1.65.2-noble` (Playwright 1.65.2, Chromium sans interface),
fenêtre de 1280 × 800, contre l'application lancée depuis une copie du dépôt. Sur un autre poste les
chiffres diffèrent de quelques dixièmes de point (polices installées) : c'est le sujet de l'étape 4.

## Le résultat à atteindre

| Vérification | Résultat mesuré |
|---|---|
| `pytest -m visual -rs`, 1er passage | 2 tests « skipped », 2 références créées (`accueil-chromium.png` 1280 × 800, `panier-chromium.png` 427 × 800) |
| `pytest -m visual`, 2e passage | 2 passed, 0,0000 % de pixels différents, SSIM 1,0000 |
| Couleur d'accent verte → bleue | détectée par les pixels (1,395 %), **pas** par le SSIM (1,0000) |
| Espacement 12 → 14 px | détecté : 1,931 % de pixels, SSIM 0,9181 |
| Police Georgia | détecté : 5,404 % de pixels, SSIM 0,8541 |
| Bouton « Ajouter » masqué | détecté : 2,038 % de pixels, SSIM 0,9250 sur l'accueil ; le test du panier échoue au clic (délai de 5 s) |
| Outil corrigé (SSIM par canal + ΔE) sur le changement de couleur | SSIM par canal 0,9880, 1,406 % de pixels avec ΔE > 10 : refusé |
| Heure dans l'en-tête, avec masque | 0,0000 % de pixels différents à 65 s d'intervalle |

Fichiers de solution : `formateur/solutions/atelier-07/`

- `ai_tools/visual_diff.py` : l'outil corrigé (étape 3) ;
- `tests/visual/test_visual.py` : les tests avec masquage des zones dynamiques (étape 5).

Workflow : `formateur/solutions/workflows/e2e-visual.yml`, jobs `visual` et `baselines` (étape 4).

## Partie A — Régression visuelle maison

### 1. Créer les références, puis comparer

Application lancée dans un premier terminal (`make run`), puis :

```bash
pytest -m visual -rs
```

```text
SKIPPED [1] tests/visual/test_visual.py:39: Baseline créée : …/tests/visual/baselines/accueil-chromium.png
SKIPPED [1] tests/visual/test_visual.py:39: Baseline créée : …/tests/visual/baselines/panier-chromium.png
================= 2 skipped, 6 deselected, 2 warnings in 1.17s =================
```

```bash
pytest -m visual
```

```text
================= 2 passed, 6 deselected, 2 warnings in 1.20s ==================
```

Ce qu'il faut faire remarquer :

- le premier passage ne vérifie **rien** : il enregistre l'état courant comme vérité. Un test
  « skipped » n'est pas un test vert. Si la page est déjà cassée ce jour-là, la référence l'est aussi ;
- les deux tests ne couvrent pas la même zone. `accueil` capture la page entière ; `panier` ne capture
  que la colonne de droite (`clip` à partir de x = 853). Cela explique plusieurs lignes du tableau
  ci-dessous ;
- `tests/visual/current/` et `tests/visual/diff/` sont dans `.gitignore` ; `tests/visual/baselines/`
  ne l'est pas : les références se commitent ;
- le nom de chaque référence porte celui du navigateur (`accueil-chromium.png`) : lancé avec
  `--browser firefox`, le test crée ses propres références au lieu de comparer Firefox à une image de
  Chromium (vérifié : 2 skipped, puis 4 passed avec les deux navigateurs).

Les deux avertissements affichés viennent de `pytest-playwright` et de FastAPI, pas du test.

### 2. Provoquer des régressions

Une modification à la fois dans `minishop/static/style.css`, puis `pytest -m visual`, puis retour à
l'état d'origine (`git checkout minishop/static/style.css`). Il n'est pas nécessaire de relancer
l'application : le fichier CSS est relu à chaque requête.

Le test refuse une capture si plus de 0,2 % des pixels diffèrent **ou** si le SSIM passe sous 0,99
(constantes `MAX_DIFF` et `MIN_SSIM` de `ai_tools/visual_diff.py`, communes au test et à la ligne de
commande).

| Changement dans `minishop/static/style.css` | Détecté ? | % pixels (`accueil` / `panier`) | SSIM (`accueil` / `panier`) |
|---|---|---|---|
| `--accent: #2563eb` (bleu au lieu de vert) | Oui, 2 tests en échec — par les pixels seulement | 1,395 % / 1,953 % | 1,0000 / 1,0000 |
| `padding: 12px` → `padding: 14px` sur `#products li` | Oui pour `accueil` ; `panier` reste vert | 1,931 % / 0,000 % | 0,9181 / 1,0000 |
| Police : `font-family: Georgia, serif` | Oui, 2 tests en échec | 5,404 % / 8,150 % | 0,8541 / 0,8139 |
| Bouton « Ajouter » masqué (`#products button { display: none; }`) | Oui, 2 tests en échec : `accueil` par la comparaison, `panier` au clic sur le bouton absent | 2,038 % / — (pas de capture) | 0,9250 / — |

Sortie du premier cas :

```text
E   AssertionError: Régression visuelle sur 'accueil-chromium' : 1.395% pixels, SSIM=1.0000 -> voir …/tests/visual/diff/accueil-chromium.png
E   AssertionError: Régression visuelle sur 'panier-chromium' : 1.953% pixels, SSIM=1.0000 -> voir …/tests/visual/diff/panier-chromium.png
2 failed, 6 deselected, 2 warnings in 1.21s
```

Lecture ligne par ligne :

- **Couleur.** Les boutons changent de couleur, rien ne bouge : peu de pixels (les seules surfaces des
  boutons), mais chacun change beaucoup. Le SSIM affiche 1,0000 : il ne voit rien. C'est l'étape 3.
- **Espacement.** Deux pixels de plus par ligne de produit décalent tout ce qui suit dans la colonne
  de gauche. Le SSIM chute nettement (0,9181) alors que peu de pixels changent : il mesure la
  structure, et un décalage est un changement de structure. Le test `panier` reste vert parce que la
  colonne de droite n'a pas bougé : une capture ne détecte que ce qu'elle cadre.
- **Police.** Tous les textes changent de forme et de largeur : c'est le plus gros écart sur les deux
  mesures. Dans l'image Playwright, Georgia n'est pas installée ; le navigateur prend la police à
  empattements disponible. Sur un poste Windows ou macOS, où Georgia existe, le chiffre sera différent.
- **Bouton masqué.** La page d'accueil est capturée et comparée normalement : 2,038 % de pixels, SSIM
  0,9250, et l'image de diff montre les cinq boutons disparus. Le test `panier`, lui, doit cliquer sur
  « Ajouter » : Playwright attend le bouton 5 s (délai fixé dans la fixture `shop`), puis lève
  `TimeoutError: Locator.click … waiting for get_by_test_id("add-mug")`. Les deux tests échouent en
  6,4 s au total, pour deux raisons différentes : une régression visuelle d'un côté, un parcours devenu
  impossible de l'autre. Bonne occasion de rappeler qu'un test visuel qui manipule la page est aussi un
  test fonctionnel.

Pour mesurer un écart sans passer par pytest :

```bash
python ai_tools/visual_diff.py tests/visual/baselines/accueil-chromium.png tests/visual/current/accueil-chromium.png --diff /tmp/diff.png
```

```text
pixels différents : 1.3952% | SSIM : 1.0000 | tailles différentes : False
```

Le code retour vaut 1 si un seuil est dépassé. Les seuils par défaut de la ligne de commande sont ceux
du test (0,2 % et 0,99) ; `--max-diff` et `--min-ssim` permettent d'en essayer d'autres.

### 3. Pourquoi le SSIM rate le changement de couleur

`compare()` convertit les deux images en niveaux de gris avant de calculer le SSIM :

```python
def _gray(a):
    return a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114
```

Cette formule donne la luminance d'une couleur. Or le vert d'origine et le bleu de remplacement ont
presque la même :

| Couleur | R, V, B | Niveau de gris |
|---|---|---|
| `#1f7a5a` (vert) | 31, 122, 90 | 91,1 |
| `#2563eb` (bleu) | 37, 99, 235 | 96,0 |

Cinq niveaux d'écart sur 255 : une fois en gris, les deux boutons sont le même bouton. De plus le SSIM
compare la structure (moyenne, contraste, corrélation par fenêtre de 8 × 8 pixels), et la structure n'a
pas bougé : mêmes formes, mêmes textes, mêmes positions. Le SSIM en gris vaut 0,99998.

Dans le test fourni, c'est le diff de pixels qui sauve la situation (1,395 % > 0,2 %). Mais ce seuil
est justement celui qu'on relâche dès que le rendu varie un peu d'une machine à l'autre. Avec un seuil
de pixels porté à 5 %, l'outil d'origine laisse passer le changement de couleur :

```bash
python ai_tools/visual_diff.py tests/visual/baselines/accueil-chromium.png tests/visual/current/accueil-chromium.png --max-diff 0.05 ; echo $?
```

```text
pixels différents : 1.3952% | SSIM : 1.0000 | tailles différentes : False
0
```

**Correction** (`formateur/solutions/atelier-07/ai_tools/visual_diff.py`). Deux mesures ajoutées, qui
ne passent plus par le gris :

```python
def ssim_per_channel(a, b):
    """SSIM calculé sur chaque canal R, V, B : on retient le plus mauvais."""
    return min(ssim(a[..., c], b[..., c]) for c in range(3))

def delta_e(a, b):
    """ΔE CIE76 par pixel : distance euclidienne dans l'espace Lab."""
    return np.sqrt(((rgb_to_lab(a) - rgb_to_lab(b)) ** 2).sum(axis=-1))
```

- le **SSIM par canal** : le bleu passe de 90 à 235 sur le canal B, ce que le gris écrasait ;
- le **ΔE** : la distance entre deux couleurs dans l'espace Lab, construit pour qu'une même distance
  corresponde à un même écart perçu. L'outil compte la part de pixels dont le ΔE dépasse 10 (un écart
  visible au premier regard) et refuse au-delà de 0,1 %.

L'interface reste la même (`compare()`, `r.ok(max_diff, min_ssim)`, `r.ssim`) : le fichier de test n'a
pas à changer. Même commande, même seuil de pixels relâché à 5 %, avec l'outil corrigé :

```text
pixels différents : 1.3952% | SSIM par canal : 0.9880 (gris : 1.0000) | ΔE moyen : 1.40 | pixels ΔE>10 : 1.4059% | tailles différentes : False
1
```

Mesures de l'outil corrigé sur les quatre régressions (page d'accueil entière) :

| Changement | SSIM gris | SSIM R / V / B | SSIM par canal | Pixels ΔE > 10 |
|---|---|---|---|---|
| Aucun | 1,0000 | 1,0000 / 1,0000 / 1,0000 | 1,0000 | 0,000 % |
| Couleur d'accent | 1,0000 | 0,9999 / 0,9996 / 0,9880 | 0,9880 | 1,406 % |
| Espacement | 0,9181 | 0,9251 / 0,9184 / 0,9004 | 0,9004 | 1,841 % |
| Police | 0,8541 | 0,8613 / 0,8545 / 0,8340 | 0,8340 | 5,261 % |
| Bouton masqué | 0,9250 | 0,9309 / 0,9255 / 0,9088 | 0,9088 | 1,957 % |

À dire honnêtement aux stagiaires : le SSIM par canal détecte le changement de couleur, mais de peu
(0,9880 pour un seuil à 0,99 dans le test). Les boutons occupent une petite surface et le SSIM est une
moyenne sur toute l'image. Le ΔE est le signal le plus net : chacun des deux critères, pris seul,
suffit à faire échouer la comparaison (vérifié en neutralisant l'autre). Placé dans la copie du dépôt,
l'outil corrigé laisse les deux tests verts sur les références et les fait échouer sur le changement de
couleur avec `SSIM=0.9880` (accueil) et `SSIM=0.9814` (panier).

### 4. Le problème des références

Générées sur un poste puis comparées dans la CI, les références échouent sans qu'aucune ligne de code
n'ait changé. Ce qu'on compare n'est pas la page, c'est le **rendu** de la page, et le rendu dépend de
la machine : polices installées (`system-ui` désigne une police différente sur chaque système),
lissage des caractères, version et moteur du navigateur, densité d'écran.

Mesuré dans le même conteneur, même page, mêmes références Chromium, en ne changeant que le moteur ou
une option de rendu du texte :

| Environnement de la capture | % pixels (`accueil`) | SSIM | Verdict du test |
|---|---|---|---|
| Chromium, identique aux références | 0,000 % | 1,0000 | vert |
| Chromium, lissage sous-pixel coupé (`--disable-lcd-text`) | 0,239 % | 0,9999 | rouge (pixels) |
| Chromium, `--disable-font-subpixel-positioning` | 0,167 % | 0,9977 | vert, de peu |
| Capture Firefox comparée à la référence Chromium | 2,298 % | 0,9223 | rouge |
| Capture WebKit comparée à la référence Chromium | 3,471 % | 0,8968 | rouge |

Un simple réglage de lissage produit déjà autant de « différence » qu'un vrai changement
d'espacement. Entre un poste Windows et un runner Ubuntu, l'écart est de cet ordre ou pire.

Stratégie à retenir :

1. **Les références sont générées là où elles sont comparées** : dans la CI, jamais sur un poste.
2. Un job dédié, lancé à la main, exécute `UPDATE_BASELINES=1 pytest -m visual` et publie
   `tests/visual/baselines/` en artefact : c'est le job `baselines` de
   `formateur/solutions/workflows/e2e-visual.yml`, déclenché par `workflow_dispatch` (bouton
   *Run workflow*). Les jobs `e2e` et `visual` ne tournent pas lors de ce lancement manuel.
3. On télécharge l'artefact `visual-baselines`, on **regarde** les images, on les commite dans une PR :
   le changement de référence se relit comme du code.
4. L'environnement est figé : même image de runner, même version de Playwright (donc de navigateur).
   Pour aller plus loin, exécuter le job dans le conteneur `mcr.microsoft.com/playwright/python:<version>`
   à la fois en CI et sur les postes : c'est ce qui a servi à produire ce corrigé.
5. Une référence par navigateur : le test s'en charge par le nom des fichiers. Les deux dernières lignes
   du tableau montrent ce que donnerait une référence partagée.

Le job `visual` du même workflow lance `pytest -m visual -rs` et publie références, captures et diffs en
artefact, que le job réussisse ou non (`if: always()`). Tant qu'aucune référence n'est commitée, le
test crée la référence et se déclare « skipped » : rien n'est comparé. Le job **échoue alors
explicitement** : l'étape cherche « Baseline créée » dans la sortie de pytest, écrit une erreur et un
message dans le résumé du job (« Référence visuelle absente… lancez ce workflow à la main… »), et sort
en code 1. Choix assumé : un job vert qui n'a rien vérifié est plus dangereux qu'un job rouge qui dit
quoi faire, et un simple avertissement dans le résumé n'est lu par personne. L'étape a été rejouée en
local : code 0 avec les références, code 1 s'il en manque une, code 1 sur une vraie régression
(`shell: bash` active `pipefail`, l'échec de pytest n'est pas masqué par `tee`). Le workflow passe
actionlint sans remarque.

### 5. Contenu dynamique

Ajout de l'heure dans l'en-tête de `minishop/static/index.html` :

```html
    <p class="tagline">La boutique des pipelines verts</p>
    <p class="tagline" data-testid="clock"></p>
```

```javascript
    document.querySelector('[data-testid="clock"]').textContent = new Date().toLocaleTimeString('fr-FR');
    loadProducts();
```

Références régénérées (`UPDATE_BASELINES=1 pytest -m visual`), puis comparaison un peu plus tard :

| Délai depuis la référence | % pixels | SSIM | Test du cours (0,2 % / 0,99) | Seuil serré (`--max-diff 0.0001`) |
|---|---|---|---|---|
| 3 s (un chiffre change) | 0,0118 % | 0,9997 | vert | rouge |
| 70 à 80 s (minutes et secondes) | 0,0125 % à 0,0182 % | 0,9994 à 0,9997 | vert | rouge |

C'est le constat que l'énoncé fait faire : avec les seuils du cours, une petite horloge **ne fait pas**
échouer le test. Quelques chiffres représentent environ 0,02 % de la page. Ce n'est pas une protection,
c'est une marge qui se consomme : l'heure prend déjà un dixième du budget de 0,2 %, et le test échouera
au hasard le jour où l'on resserre le seuil (colonne de droite), où l'on cadre plus près de l'en-tête,
ou quand un contenu plus gros varie (date complète, numéro de commande, bandeau, avatar). Un test qui
passe « presque toujours » est le pire cas.

La bonne réponse est de retirer la zone de la comparaison :

```python
DYNAMIC = ['[data-testid="clock"]']

def check(page, name, **kwargs):
    ...
    page.screenshot(path=str(current), mask=[page.locator(s) for s in DYNAMIC], **kwargs)
```

Playwright recouvre la zone d'un rectangle uni avant de capturer. Fichier complet :
`formateur/solutions/atelier-07/tests/visual/test_visual.py`. Les références doivent être régénérées
une fois avec le masque. Vérification :

```text
UPDATE_BASELINES=1 pytest -m visual     -> 2 skipped
(65 s plus tard) pytest -m visual       -> 2 passed
pixels différents : 0.0000% | SSIM : 1.0000 | tailles différentes : False     (même avec --max-diff 0)
```

Deux précisions :

- un localisateur qui ne trouve rien ne masque rien : le fichier de solution fonctionne aussi sur la
  page d'origine, sans horloge (vérifié : la référence produite est identique, octet pour octet, à
  celle du fichier d'origine) ;
- le masque couvre la boîte de l'élément. Ici c'est un paragraphe, de largeur fixe. Sur un `<span>`
  dont la largeur suit le texte, le rectangle changerait de taille avec le contenu : masquer un
  conteneur de taille stable.

Autres réponses possibles, à citer : figer l'horloge du navigateur (`page.clock`), injecter des données
de test fixes, ou capturer un composant plutôt que la page (`locator.screenshot()`).

## Partie B — Outils IA du marché

> **Non vérifié.** Aucun compte d'essai n'a été créé et aucun de ces outils n'a été exécuté pour ce
> corrigé. La grille ci-dessous est rédigée à partir de connaissances générales sur ces produits ; les
> offres, les prix et les fonctionnalités changent vite. **À actualiser avant chaque session** à partir
> des sites des éditeurs, et à confronter à ce que les groupes trouvent en séance.

Ce qu'on attend de chaque présentation de 5 minutes : le principe, ce que l'IA apporte réellement (et ce
qui relève du discours commercial), l'intégration à la CI, le modèle de prix, les limites, la
dépendance au fournisseur.

| Critère | Applitools Eyes | Testim (Tricentis) | Mabl | Outils ouverts (Playwright `toHaveScreenshot`, BackstopJS, Lost Pixel ; Percy est un service hébergé) | Outil maison de l'atelier |
|---|---|---|---|---|---|
| Principe | SDK ajouté aux tests existants ; les captures sont comparées chez l'éditeur par un modèle entraîné | Enregistrement de parcours dans le navigateur, localisateurs à plusieurs attributs | Plateforme low-code hébergée : parcours enregistrés, exécutés dans le cloud de l'éditeur | Comparaison de pixels avec seuils, références dans le dépôt (ou dans le service pour Percy) | Diff de pixels + SSIM, références dans le dépôt |
| Détection de vraies régressions | Bonne sur la mise en page et le contenu ; plusieurs niveaux de comparaison (strict, mise en page, contenu) | Surtout fonctionnelle ; le visuel est secondaire | Fonctionnelle, plus des alertes visuelles et de performance après plusieurs exécutions | Bonne tant que l'environnement est figé | Bonne dans un environnement figé (tableau de l'étape 2) |
| Taux de faux positifs | Faible : c'est l'argument principal (bruit de rendu ignoré, diffs semblables regroupés) | Réduit sur les localisateurs ; l'auto-réparation peut créer des faux **négatifs** | Réduit par l'auto-réparation, même réserve | Élevé si l'environnement varie ; se règle par seuils, masques, conteneur figé | Élevé hors du conteneur de référence (étape 4) |
| Effort de maintenance | Faible côté seuils ; revue des diffs dans un tableau de bord | Faible au départ, croît avec le nombre de parcours enregistrés | Faible au départ ; les tests vivent dans la plateforme, pas dans le dépôt | Moyen : références à régénérer et à relire | Moyen, et l'outil lui-même est à maintenir |
| Coût | Payant, sur devis ou par paliers ; offre gratuite limitée | Payant, sur devis ; essai gratuit | Payant, sur devis ; essai gratuit | Gratuit pour les outils ouverts ; Percy a un palier gratuit puis un prix au volume de captures | Gratuit (temps de l'équipe) |
| Données envoyées chez le fournisseur | Captures d'écran et DOM des pages testées | Parcours, captures, parfois données saisies | Parcours, captures, journaux réseau | Aucune pour les outils ouverts ; captures pour Percy | Aucune |
| Intégration CI | SDK dans les tests + clé d'API en secret | CLI ou déclenchement par API | CLI ou déclenchement par API | Native : c'est un test comme un autre | Native (`pytest -m visual`) |
| Dépendance au fournisseur | Moyenne : les tests restent les vôtres, l'historique et les références sont chez l'éditeur | Forte : les tests sont dans le format de l'outil | Forte : idem | Faible | Nulle |

Trois idées à faire ressortir au moment de la mise en commun :

- la « Visual AI » ne voit pas mieux, elle **ignore mieux** : sa valeur est dans la baisse des faux
  positifs, donc dans le temps de revue économisé. Le tableau de l'étape 4 donne l'ordre de grandeur du
  bruit qu'elle doit absorber ;
- la question à poser à chaque éditeur : quelles données sortent de l'entreprise (captures de pages
  internes, données saisies dans les formulaires), et où sont-elles hébergées ;
- on peut commencer sans rien acheter : un conteneur figé, des masques et un seuil raisonnable couvrent
  une bonne part du besoin. L'outil payant se justifie quand le temps passé à trier les faux positifs
  dépasse son prix.

## Partie C — Auto-healing : le principe

Dans `minishop/static/index.html`, remplacer `data-testid="quote-btn"` par `data-testid="compute-btn"`.

Le test visuel `test_panier_avec_total` clique sur `quote-btn` : il casse. Le test E2E fourni
(`test_page_accueil`) n'utilise pas ce bouton et reste vert ; les tests écrits à l'atelier 8 casseront
de la même façon.

```bash
pytest -m "visual or e2e"
```

```text
E   playwright._impl._errors.TimeoutError: Locator.click: Timeout 5000ms exceeded.
E     - waiting for get_by_test_id("quote-btn")
FAILED tests/visual/test_visual.py::test_panier_avec_total[chromium]
1 failed, 2 passed, 5 deselected, 2 warnings in 6.38s
```

Pour montrer la différence entre les deux localisateurs, ajouter ce fichier le temps de la
démonstration (`tests/e2e/test_partie_c.py`) :

```python
import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


@pytest.fixture
def shop(page: Page, app_url):
    page.set_default_timeout(5000)
    page.goto(app_url)
    page.get_by_test_id("add-mug").click()
    return page


def test_total_par_testid(shop: Page):
    shop.get_by_test_id("quote-btn").click()
    expect(shop.get_by_test_id("total")).to_have_text("17.40")


def test_total_par_role(shop: Page):
    shop.get_by_role("button", name="Calculer le total").click()
    expect(shop.get_by_test_id("total")).to_have_text("17.40")
```

Résultat avec l'identifiant renommé :

```text
E   playwright._impl._errors.TimeoutError: Locator.click: Timeout 5000ms exceeded.
E     - waiting for get_by_test_id("quote-btn")
FAILED tests/e2e/test_partie_c.py::test_total_par_testid[chromium]
1 failed, 2 passed, 7 deselected, 2 warnings in 6.20s
```

Le test par identifiant échoue ; le test par rôle passe, sans aucune « réparation ».

**Pourquoi `get_by_role("button", name="Calculer le total")` est-il plus robuste ?** Il désigne le
bouton comme le fait l'utilisateur, et comme le fait un lecteur d'écran : un bouton, dont le nom
accessible est « Calculer le total ». Ce contrat-là change rarement, et quand il change c'est une
décision visible (produit, traduction). Un `data-testid`, un `id` ou une classe CSS sont des détails
d'implémentation qu'un développeur renomme sans penser aux tests. Le localisateur par rôle vérifie en
plus, sans le dire, que l'élément est bien un bouton avec un nom lisible : c'est un petit test
d'accessibilité gratuit. Sa limite : il casse si le libellé change ou si l'application est traduite ;
le `data-testid` garde alors son intérêt, à condition d'être traité comme une interface publique.

**Quel risque si l'outil « répare » un test qui aurait dû échouer ?** Un faux négatif. L'outil
retrouve « le bouton le plus ressemblant » par son texte, sa position, ses voisins ; si le bouton a été
supprimé ou remplacé par un autre (« Calculer le total » devenu « Vider le panier » au même endroit),
il clique sur le mauvais élément et le test reste vert, ou échoue plus loin pour une raison sans
rapport. La réparation masque aussi une information utile : quelqu'un a changé un identifiant sur
lequel d'autres comptaient. Règles de prudence : toute réparation est tracée et relue comme une
modification de test ; elle propose un correctif, elle ne l'applique pas en silence ; un test réparé
plusieurs fois de suite se réécrit.

## Points d'animation

- **Durée à surveiller.** L'étape 2 dérape si l'on oublie de revenir au CSS d'origine entre deux
  essais ; la partie B déborde toujours : tenir les 5 minutes par groupe.
- **« Skipped » pris pour « vert ».** Beaucoup lancent une seule fois et concluent que tout va bien.
  Faire lire la ligne `SKIPPED … Baseline créée`.
- **Oublier de remettre le CSS d'origine** entre deux essais : les régressions se cumulent et le
  tableau devient illisible. `git checkout minishop/static/style.css` après chaque mesure.
- **Régénérer les références pour faire passer le test.** `UPDATE_BASELINES=1` est le geste réflexe du
  stagiaire pressé. Question à poser : qui a regardé la nouvelle image avant de la commiter ?
- **Références créées sur le poste puis poussées.** C'est l'erreur que l'étape 4 veut faire commettre :
  la laisser arriver, puis l'expliquer avec le tableau des environnements.
- **Discussion : pixels ou SSIM ?** Aucun des deux seul. Les pixels voient la couleur et ratent
  l'importance d'un décalage ; le SSIM voit la structure et rate la couleur. Les outils du marché
  empilent plusieurs mesures, puis un modèle qui apprend ce qu'il faut ignorer.
- **Discussion : où placer le seuil ?** Trop serré, le test échoue au hasard et l'équipe l'ignore ; trop
  lâche, il laisse passer le changement de couleur (démonstration de l'étape 3 avec `--max-diff 0.05`).
- **Discussion : que cadrer ?** Le test `panier` n'a pas vu le changement d'espacement. Des captures par
  composant sont plus stables et plus lisibles qu'une page entière, mais il en faut davantage.

## Non vérifié

- **Partie B en entier** : aucun outil du marché n'a été exécuté, aucun compte créé ; grille rédigée de
  mémoire, à actualiser (prix, offres gratuites, fonctionnalités).
- **Exécution réelle dans GitHub Actions** : `e2e-visual.yml` est validé par actionlint et l'étape de
  contrôle du job `visual` a été rejouée en local, mais le workflow n'a pas été lancé sur un runner
  (déclenchement manuel, résumé du job, artefact `visual-baselines` non observés). L'écart
  entre un poste réel (Windows, macOS) et le runner n'a pas été mesuré : le tableau de l'étape 4 le
  simule à l'intérieur d'un même conteneur.
- **Police réellement utilisée** pour `Georgia, serif` dans l'image Playwright : non identifiée ; seul
  l'écart d'image a été mesuré.
- **Mode `--headed`** et rendu sur un écran réel : tout a été exécuté sans interface graphique.
- Les autres parades de l'étape 5 (`page.clock`, capture par composant) sont citées sans avoir été
  exécutées.

---

## Fichiers de cet atelier

Par rapport à la branche `python/atelier-06` :

| | Fichier |
|---|---|
| modifié | `ai_tools/visual_diff.py` |
| modifié | `tests/visual/test_visual.py` |

### `ai_tools/visual_diff.py`

Modification :

````diff
diff --git a/ai_tools/visual_diff.py b/ai_tools/visual_diff.py
index 1614167..be0647f 100644
--- a/ai_tools/visual_diff.py
+++ b/ai_tools/visual_diff.py
@@ -1,20 +1,22 @@
-"""Comparaison visuelle de captures d'écran (régression visuelle).
+"""Comparaison visuelle de captures d'écran — SOLUTION Atelier 7.
 
-Deux mesures complémentaires :
-  * diff pixel (avec tolérance par canal) : % de pixels différents — rapide mais
-    sensible à l'anti-aliasing et aux polices ;
-  * SSIM (similarité structurelle, proche de la perception humaine) : 1.0 = identique.
-    C'est le principe de base des outils « Visual AI » (Applitools, Percy...), qui y
-    ajoutent des modèles entraînés à ignorer le bruit (contenu dynamique, rendu).
+Version corrigée de l'outil du dépôt stagiaires. Le SSIM d'origine est calculé sur une
+image convertie en niveaux de gris : deux couleurs de même luminance (le vert #1f7a5a et
+le bleu #2563eb, par exemple) y deviennent presque le même gris, et le changement passe
+inaperçu. Deux corrections, indépendantes l'une de l'autre :
 
-Produit une image de diff (pixels changés en magenta sur fond atténué).
+  * SSIM par canal : le SSIM est calculé séparément sur R, V et B, on garde le plus
+    mauvais des trois ;
+  * ΔE (CIE76) : distance entre les deux couleurs d'un même pixel dans l'espace Lab,
+    proche de l'écart perçu par l'œil. On compte la part de pixels dont le ΔE dépasse
+    un seuil (10 par défaut : un écart visible au premier regard).
+
+L'interface est compatible avec l'outil d'origine : `compare()` renvoie un résultat dont
+`ssim` est désormais le SSIM par canal ; l'ancien calcul reste disponible dans `ssim_gray`.
 
 Usage :
     python ai_tools/visual_diff.py baseline.png current.png --diff diff.png
     # code retour 1 si la différence dépasse les seuils
-
-Les seuils par défaut (MAX_DIFF, MIN_SSIM) sont les mêmes en ligne de commande et dans
-tests/visual/test_visual.py, qui les importe d'ici.
 """
 
 from __future__ import annotations
@@ -28,17 +30,26 @@ import numpy as np
 from PIL import Image
 
 MAX_DIFF = 0.002  # part maximale de pixels différents (0,2 %)
-MIN_SSIM = 0.99  # SSIM minimal
+MIN_SSIM = 0.99  # SSIM par canal minimal
+MAX_DELTA_E_RATIO = 0.001  # part maximale de pixels dont le ΔE dépasse le seuil
 
 
 @dataclass
 class VisualResult:
     diff_ratio: float
-    ssim: float
+    ssim: float  # SSIM par canal (le plus mauvais des trois canaux)
     size_mismatch: bool
+    ssim_gray: float = 1.0  # ancien calcul, conservé pour comparer
+    delta_e_mean: float = 0.0  # ΔE moyen sur toute l'image
+    delta_e_ratio: float = 0.0  # part de pixels dont le ΔE dépasse le seuil
 
-    def ok(self, max_diff: float, min_ssim: float) -> bool:
-        return not self.size_mismatch and self.diff_ratio <= max_diff and self.ssim >= min_ssim
+    def ok(self, max_diff: float, min_ssim: float, max_delta_e_ratio: float = MAX_DELTA_E_RATIO) -> bool:
+        return (
+            not self.size_mismatch
+            and self.diff_ratio <= max_diff
+            and self.ssim >= min_ssim
+            and self.delta_e_ratio <= max_delta_e_ratio
+        )
 
 
 def _gray(a: np.ndarray) -> np.ndarray:
@@ -58,18 +69,58 @@ def ssim(x: np.ndarray, y: np.ndarray, win: int = 8) -> float:
     return float(s.mean())
 
 
-def compare(baseline: Path, current: Path, diff_out: Path | None = None, tolerance: int = 16) -> VisualResult:
+def ssim_per_channel(a: np.ndarray, b: np.ndarray) -> float:
+    """SSIM calculé sur chaque canal R, V, B : on retient le plus mauvais."""
+    return min(ssim(a[..., c], b[..., c]) for c in range(3))
+
+
+def rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
+    """sRGB (0-255) -> CIE Lab, illuminant D65."""
+    c = rgb / 255.0
+    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
+    m = np.array(
+        [
+            [0.4124564, 0.3575761, 0.1804375],
+            [0.2126729, 0.7151522, 0.0721750],
+            [0.0193339, 0.1191920, 0.9503041],
+        ]
+    )
+    xyz = lin @ m.T / np.array([0.95047, 1.0, 1.08883])
+    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
+    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], axis=-1)
+
+
+def delta_e(a: np.ndarray, b: np.ndarray) -> np.ndarray:
+    """ΔE CIE76 par pixel : distance euclidienne dans l'espace Lab."""
+    return np.sqrt(((rgb_to_lab(a) - rgb_to_lab(b)) ** 2).sum(axis=-1))
+
+
+def compare(
+    baseline: Path,
+    current: Path,
+    diff_out: Path | None = None,
+    tolerance: int = 16,
+    delta_e_threshold: float = 10.0,
+) -> VisualResult:
     a = np.asarray(Image.open(baseline).convert("RGB"), dtype=np.float64)
     b = np.asarray(Image.open(current).convert("RGB"), dtype=np.float64)
     if a.shape != b.shape:
-        return VisualResult(1.0, 0.0, True)
+        return VisualResult(1.0, 0.0, True, 0.0, 100.0, 1.0)
     changed = (np.abs(a - b) > tolerance).any(axis=2)
     if diff_out:
         out = (a * 0.3 + 178).astype(np.uint8)
         out[changed] = [255, 0, 255]
         diff_out.parent.mkdir(parents=True, exist_ok=True)
         Image.fromarray(out).save(diff_out)
-    return VisualResult(float(changed.mean()), ssim(_gray(a), _gray(b)), False)
+    de = delta_e(a, b)
+    return VisualResult(
+        diff_ratio=float(changed.mean()),
+        ssim=ssim_per_channel(a, b),
+        size_mismatch=False,
+        ssim_gray=ssim(_gray(a), _gray(b)),
+        delta_e_mean=float(de.mean()),
+        delta_e_ratio=float((de > delta_e_threshold).mean()),
+    )
 
 
 def main() -> int:
@@ -78,11 +129,18 @@ def main() -> int:
     ap.add_argument("current", type=Path)
     ap.add_argument("--diff", type=Path)
     ap.add_argument("--max-diff", type=float, default=MAX_DIFF, help="part max de pixels différents")
-    ap.add_argument("--min-ssim", type=float, default=MIN_SSIM)
+    ap.add_argument("--min-ssim", type=float, default=MIN_SSIM, help="SSIM par canal minimal")
+    ap.add_argument(
+        "--max-delta-e-ratio", type=float, default=MAX_DELTA_E_RATIO, help="part max de pixels dont le ΔE dépasse 10"
+    )
     args = ap.parse_args()
     r = compare(args.baseline, args.current, args.diff)
-    print(f"pixels différents : {r.diff_ratio:.4%} | SSIM : {r.ssim:.4f} | tailles différentes : {r.size_mismatch}")
-    return 0 if r.ok(args.max_diff, args.min_ssim) else 1
+    print(
+        f"pixels différents : {r.diff_ratio:.4%} | SSIM par canal : {r.ssim:.4f} (gris : {r.ssim_gray:.4f}) | "
+        f"ΔE moyen : {r.delta_e_mean:.2f} | pixels ΔE>10 : {r.delta_e_ratio:.4%} | "
+        f"tailles différentes : {r.size_mismatch}"
+    )
+    return 0 if r.ok(args.max_diff, args.min_ssim, args.max_delta_e_ratio) else 1
 
 
 if __name__ == "__main__":
````

### `tests/visual/test_visual.py`

Modification :

````diff
diff --git a/tests/visual/test_visual.py b/tests/visual/test_visual.py
index 6bcd3be..85ad0e4 100644
--- a/tests/visual/test_visual.py
+++ b/tests/visual/test_visual.py
@@ -1,4 +1,12 @@
-"""Tests de régression visuelle (Atelier 7).
+"""Tests de régression visuelle — SOLUTION Atelier 7 (étape 5 : contenu dynamique).
+
+Par rapport au fichier du dépôt stagiaires, une seule chose change : toutes les captures
+masquent les zones dont le contenu varie d'une exécution à l'autre (ici l'heure affichée
+dans l'en-tête, `data-testid="clock"`). Playwright recouvre la zone d'un rectangle de
+couleur unie avant de capturer : la référence et la capture courante portent le même
+rectangle, la comparaison ne voit plus l'heure. Un localisateur qui ne trouve aucun
+élément ne masque rien : ce fichier fonctionne aussi sur la page d'origine, sans horloge.
+Les références doivent être régénérées une fois avec le masque.
 
 Premier lancement : les baselines n'existent pas -> elles sont créées et le test est
 « skipped ». Committez tests/visual/baselines/*.png ; les lancements suivants comparent.
@@ -26,12 +34,15 @@ pytestmark = pytest.mark.visual
 HERE = Path(__file__).parent
 BASE, CURRENT, DIFF = HERE / "baselines", HERE / "current", HERE / "diff"
 
+# Sélecteurs des zones à contenu variable (heure, numéro de commande, bandeau…).
+DYNAMIC = ['[data-testid="clock"]']
+
 
 def check(page: Page, name: str, **kwargs):
     name = f"{name}-{page.context.browser.browser_type.name}"
     CURRENT.mkdir(exist_ok=True)
     current = CURRENT / f"{name}.png"
-    page.screenshot(path=str(current), **kwargs)
+    page.screenshot(path=str(current), mask=[page.locator(s) for s in DYNAMIC], **kwargs)
     baseline = BASE / f"{name}.png"
     if not baseline.exists() or os.getenv("UPDATE_BASELINES") == "1":
         BASE.mkdir(exist_ok=True)
````
