# Atelier 6 — Machine learning : prédire les zones à risque et prioriser les tests : corrigé

**Durée : 2 h 30** (étapes : 25, 30, 35, 25 et 25 min) · Module 2

Objectif : entraîner un modèle qui estime, pour un changement de code, la probabilité de casser la
CI, l'évaluer honnêtement, puis s'en servir pour lancer d'abord les tests les plus susceptibles
d'échouer et pour décider où investir l'effort de test.

Tous les chiffres viennent d'une exécution réelle (Python 3.13, scikit-learn et pandas de
`requirements-dev.txt`). Les données sont simulées avec une graine fixe et les modèles ont un
`random_state` fixe : les stagiaires obtiennent les mêmes valeurs.

Fichiers de solution, dans `formateur/solutions/atelier-06/ai_tools/` (à copier dans `ai_tools/` du dépôt) :

| Fichier | Étape | Rôle |
|---|---|---|
| `explore_history.py` | 1 | Les trois chiffres de l'énoncé et la vérification de trois hypothèses |
| `risk_experiments.py` | 2 et 3 | Tableau des variantes, coût des erreurs, démonstration de la fuite de données |
| `coverage_test_map.py` | 4 | Table fichier → tests déduite de la couverture |
| `risk_model.py` | 4 | Version du script qui lit cette table si elle existe (seule différence avec l'original) |
| `test_dashboard.py` | 5 | Tableau de bord texte par module |

## Le résultat à atteindre

| Mesure | Valeur obtenue |
|---|---|
| Données | 1 284 lignes, 600 commits, taux de casse global 16,2 % |
| Découpage temporel | 963 lignes pour apprendre, 321 pour tester, dont 54 casses (16,8 %) |
| Référence naïve « ça ne casse jamais » | exactitude 83 %, rappel 0 % |
| Régression logistique (modèle retenu par le script) | AUC 0,746, exactitude 83 %, rappel casse 0 % |
| Gradient boosting | AUC 0,718, exactitude 82 %, rappel casse 7 % |
| `class_weight="balanced"` | AUC 0,753, rappel 48 %, précision 28 % |
| Coût des erreurs (FP = 2 min, FN = 60 min) | défaut : 3 242 min ; `balanced` : 1 812 min ; seuil 0,1 : 418 min |
| Prédiction `pricing.py` + `style.css` | 29,4 % et 1,9 % ; `tests/unit/test_pricing.py` en tête |
| Table déduite de la couverture | `pricing.py` → `tests/unit/test_pricing.py` (49 lignes), puis `tests/api/test_api.py` (40 lignes) |
| Tableau de bord | priorité à `minishop/api.py` : couverture 66 %, score de mutation 5 %, risque prédit 27,9 % |

## Données

```bash
python scripts/simulate_history.py      # déjà fait à l'Atelier 5
head -3 data/git-history.csv
```

```text
commit,file,author,lines_added,lines_deleted,is_fix_commit,files_in_commit,hour,broke_ci
c0001,minishop/catalog.py,driss,5,1,0,1,23,0
c0002,minishop/static/index.html,emma,10,0,0,2,10,1
```

Une ligne est un couple (commit, fichier). Un commit de trois fichiers donne trois lignes. Il n'y a
pas de date : l'ordre des lignes est l'ordre chronologique.

## Étape 1 — Explorer les données

```bash
python ai_tools/explore_history.py data/git-history.csv
```

### Les trois chiffres de l'énoncé

`df.broke_ci.mean()` : **0,162**. Un changement sur six casse la CI. Les classes sont déséquilibrées,
ce qui prépare le piège de l'exactitude de l'étape 2.

`df.groupby("file").broke_ci.mean().sort_values()` :

| Fichier | Taux de casse | Lignes |
|---|---|---|
| `docs/index.md` | 0,000 | 142 |
| `README.md` | 0,014 | 144 |
| `minishop/static/style.css` | 0,021 | 142 |
| `minishop/catalog.py` | 0,090 | 134 |
| `minishop/static/index.html` | 0,156 | 154 |
| `minishop/search.py` | 0,183 | 164 |
| `minishop/api.py` | 0,268 | 127 |
| `minishop/pricing.py` | 0,357 | 140 |
| `minishop/stock.py` | 0,387 | 137 |

`df.groupby("author").broke_ci.mean()` :

| Auteur | Taux de casse | Lignes |
|---|---|---|
| alice | 0,137 | 262 |
| bob | 0,136 | 250 |
| chloe | 0,175 | 252 |
| driss | 0,138 | 282 |
| emma | 0,231 | 238 |

Le fichier est de loin la variable la plus discriminante (de 0 % à 39 %). L'écart entre auteurs est
plus faible, et l'hypothèse 3 montre qu'il ne faut pas le lire comme un classement des personnes.

### Trois hypothèses vérifiées

**H1 — « Les gros changements cassent plus. » Confirmée, mais l'effet est modéré.**

| Taille (lignes ajoutées + supprimées) | Taux de casse | Lignes |
|---|---|---|
| 1 à 10 | 0,153 | 170 |
| 11 à 25 | 0,119 | 352 |
| 26 à 50 | 0,161 | 461 |
| 51 à 100 | 0,214 | 266 |
| plus de 100 | 0,257 | 35 |

Le taux monte nettement au-delà de 50 lignes, mais la corrélation taille / casse n'est que de +0,090,
et la tranche « plus de 100 » ne compte que 35 lignes. La tranche 1 à 10 casse plus que la tranche
11 à 25 : sur de petits effectifs, la courbe n'est pas régulière.

**H2 — « Les commits tardifs (20 h et après) cassent plus. » Réfutée.**

| Heure | Taux de casse | Lignes |
|---|---|---|
| avant 20 h | 0,162 | 1 031 |
| 20 h et après | 0,162 | 253 |

Aucune différence. Une idée reçue plausible n'est pas un fait : c'est l'intérêt de vérifier.

**H3 — « emma casse plus que les autres. » Vraie en moyenne, fausse comme jugement.**

| | Commits 1 à 299 | Commits 300 à 600 |
|---|---|---|
| emma | 0,275 | 0,170 |
| les autres | 0,137 | 0,154 |

L'écart vient entièrement de la première moitié de l'historique : c'est un effet d'arrivée dans
l'équipe, qui a disparu ensuite. Un taux « depuis toujours » continue pourtant de la désigner. C'est
l'argument concret pour la mise en garde de l'énoncé sur l'usage RH.

**Complément — une hypothèse qui semble confirmée et ne l'est pas.** Les commits de correction
(`is_fix_commit = 1`) cassent moins : 0,129 contre 0,171. Or le simulateur n'utilise pas cette
variable pour décider de la casse (voir `git_history()` dans `scripts/simulate_history.py`) : l'écart
est dû au hasard, sur 278 lignes. Le modèle de l'étape 2 lui donnera pourtant un coefficient de
−0,467. De même, le nombre de fichiers du commit donne 0,176, 0,185, 0,120 et 0,161 pour 1, 2, 3 et
4 fichiers : aucune tendance. Un modèle apprend aussi le bruit.

## Étape 2 — Entraîner et évaluer

```bash
python ai_tools/risk_model.py train data/git-history.csv
```

```text
1284 lignes — apprentissage sur 963, test sur 321 (les plus récentes)

== Régression logistique : AUC = 0.746
              precision    recall  f1-score   support
          ok       0.83      1.00      0.91       267
       casse       0.00      0.00      0.00        54
    accuracy                           0.83       321

== Gradient boosting : AUC = 0.718
              precision    recall  f1-score   support
          ok       0.84      0.97      0.90       267
       casse       0.33      0.07      0.12        54
    accuracy                           0.82       321

Référence naïve (toujours la classe majoritaire) : exactitude 83%

Coefficients (signe = sens de l'effet ; variables non normalisées) :
  is_code                    +2.301
  file_past_breaks_rate      +1.678
  author_past_breaks_rate    +0.519
  is_fix_commit              -0.467
  files_in_commit            -0.104
  late_hour                  -0.072
  lines_deleted              +0.012
  lines_added                +0.009
  file_past_commits          -0.004

Modèle sauvegardé : reports/risk_model.pkl
```

Le script garde le modèle qui a la meilleure AUC, ici la régression logistique, puis le ré-entraîne
sur tout l'historique avant de le sauvegarder.

### Pourquoi une validation temporelle et pas un découpage aléatoire ?

Parce que le modèle sera utilisé pour prédire le **futur** à partir du **passé**. L'évaluation doit
reproduire cette situation : apprendre sur les 75 % de lignes les plus anciennes, tester sur les
25 % les plus récentes. Un découpage aléatoire mélange les époques et pose trois problèmes :

1. le modèle s'entraîne sur des lignes postérieures à celles qu'il doit prédire, ce qui n'arrivera
   jamais en production ;
2. un projet change dans le temps. Ici l'effet « emma » disparaît après le commit 300 : un modèle
   évalué au hasard est noté en partie sur une époque révolue ;
3. le résultat dépend du tirage. Mesuré avec `risk_experiments.py` sur 20 tirages aléatoires : AUC
   moyenne 0,751, mais de 0,692 à 0,819 selon la graine. Sur ces données la moyenne est proche de
   l'AUC temporelle (0,746) ; le problème est qu'un seul tirage favorable peut faire croire à 0,82.

### Le piège de l'exactitude : que vaut vraiment le modèle ?

La régression logistique a 83 % d'exactitude, exactement comme la règle « ça ne casse jamais ». Et
pour cause : au seuil de 0,5 elle ne détecte **aucune** des 54 casses (rappel 0 %), et elle lève une
seule alerte, fausse. Comme outil de décision oui / non, elle ne vaut rien de plus que la règle naïve.
Sur des classes déséquilibrées (17 % de casses), l'exactitude récompense le fait de toujours répondre
« non ».

Deux mesures disent ce que le modèle vaut réellement :

- **le rappel sur la classe « casse »** : 0 % pour la régression logistique, 7 % (4 casses sur 54)
  pour le gradient boosting. C'est la mesure qui compte si l'on veut être prévenu ;
- **l'AUC** : 0,746. Elle ne dépend pas du seuil. Elle se lit ainsi : si l'on tire au hasard un
  changement qui a cassé et un qui n'a pas cassé, le modèle donne la probabilité la plus haute au
  premier environ 3 fois sur 4 (0,5 serait le hasard, 1 la perfection).

Conclusion à faire formuler : le modèle **classe correctement** les changements par ordre de risque,
mais ses probabilités dépassent rarement 0,5, donc il ne « prédit » jamais une casse. Il est
utilisable pour **ordonner** des tests (étape 4), et il faut régler le seuil ou les poids pour en
faire une alerte (étape 3). Faire remarquer aussi que le gradient boosting, plus sophistiqué, fait
moins bien en AUC que le modèle linéaire : avec 963 lignes, il apprend du bruit.

Lecture des coefficients : `is_code` (+2,3) et `file_past_breaks_rate` (+1,7) dominent, ce qui
confirme l'exploration. Les coefficients de `is_fix_commit` (−0,47) et `files_in_commit` (−0,10) sont
du bruit appris (voir le complément de l'étape 1). Les variables ne sont pas normalisées : on ne peut
pas comparer la taille des coefficients de `lines_added` (en lignes) et de `is_code` (0 ou 1).

### `featurize()` et la fuite de données

Dans `featurize()`, les compteurs par fichier et par auteur sont mis à jour **après** l'ajout de la
ligne à `X`. Les variables `file_past_commits`, `file_past_breaks_rate` et `author_past_breaks_rate`
d'une ligne ne contiennent donc que ce qui s'est passé avant elle. C'est indispensable : au moment
de prédire un nouveau changement, on ne connaît pas son résultat, ni celui des changements suivants.

Une **fuite de données** est une information présente à l'entraînement et qui ne sera pas disponible
au moment de la prédiction, parce qu'elle vient du futur ou parce qu'elle contient la réponse. Le
modèle obtient alors de très bons scores en évaluation et échoue en production. Démonstration, dans
`risk_experiments.py` :

| Construction des variables | AUC |
|---|---|
| Correcte : taux calculés sur le passé de chaque ligne | 0,746 |
| Taux par fichier et par auteur calculés sur tout l'historique, futur compris | 0,770 |
| Ajout du taux de casse du commit, qui contient l'étiquette de la ligne | 0,964 |

La première fuite est discrète (+0,024) : c'est le cas le plus dangereux, parce qu'il ressemble à une
amélioration honnête. La seconde est grossière : une AUC de 0,96 sur un problème aussi bruité doit
alerter. Règle pratique : un score trop beau est d'abord un bug à chercher.

## Étape 3 — Améliorer le modèle

```bash
python ai_tools/risk_experiments.py data/git-history.csv
```

Le script reprend `load()` et `featurize()` de `risk_model.py` et le même découpage, sans modifier
l'original. Les variantes de l'énoncé sont appliquées au modèle retenu par défaut (régression
logistique). Pour les faire à la main dans `risk_model.py` :

```python
"Régression logistique": LogisticRegression(max_iter=1000, class_weight="balanced"),   # variante 2
print(classification_report(y[cut:], (proba >= 0.3).astype(int), ...))                 # variante 3
"Random forest": RandomForestClassifier(random_state=0),                               # variante 4
```

### Tableau rempli

VP : casses détectées ; FP : fausses alertes ; FN : casses manquées (sur 321 lignes de test, dont 54 casses).

| Variante | AUC | Rappel casse | Précision casse | VP | FP | FN |
|---|---|---|---|---|---|---|
| Défaut (régression logistique, seuil 0,5) | 0,746 | 0 % | 0 % | 0 | 1 | 54 |
| `class_weight="balanced"` | 0,753 | 48 % | 28 % | 26 | 66 | 28 |
| Seuil de décision 0,3 au lieu de 0,5 | 0,746 | 9 % | 71 % | 5 | 2 | 49 |
| `RandomForestClassifier` | 0,750 | 6 % | 50 % | 3 | 3 | 51 |
| Nouvelle variable `taille` (`lines_added + lines_deleted`) | 0,746 | 0 % | 0 % | 0 | 1 | 54 |
| Nouvelle variable `risque_x_taille` | 0,750 | 0 % | 0 % | 0 | 1 | 54 |
| `risque_x_taille` + `class_weight="balanced"` | 0,755 | 48 % | 30 % | 26 | 60 | 28 |

Mesures complémentaires, hors énoncé :

| Variante | AUC | Rappel casse | Précision casse | VP | FP | FN |
|---|---|---|---|---|---|---|
| Gradient boosting (second modèle du script) | 0,718 | 7 % | 33 % | 4 | 8 | 50 |
| Random forest + `balanced` | 0,724 | 19 % | 48 % | 10 | 11 | 44 |
| Random forest, seuil 0,3 | 0,750 | 50 % | 28 % | 27 | 71 | 27 |
| Régression logistique, seuil 0,1 | 0,746 | 96 % | 26 % | 52 | 149 | 2 |
| Une seule variable : `risque_x_taille` | 0,772 | 0 % | 0 % | 0 | 0 | 54 |
| Sans `author_past_breaks_rate` | 0,746 | 0 % | 0 % | 0 | 1 | 54 |
| Sans `author_past_breaks_rate` + `balanced` | 0,753 | 50 % | 28 % | 27 | 68 | 27 |

### Ce qu'il faut en retenir

- **Changer le seuil ne change pas l'AUC** (0,746 dans les deux cas) : le classement des changements
  est le même, on déplace seulement la frontière. Le seuil 0,3 de l'énoncé est encore trop haut
  (rappel 9 %) : les probabilités du modèle dépassent rarement 0,3 puisque le taux de base est de 16 %.
- **`class_weight="balanced"` fait surtout bouger le seuil.** L'AUC gagne à peine (0,753), mais le
  rappel passe de 0 à 48 %. Donner plus de poids aux casses pousse toutes les probabilités vers le
  haut. C'est le changement le plus efficace des variantes de l'énoncé.
- **La forêt aléatoire ne fait pas mieux** que le modèle linéaire (0,750 contre 0,746) et son rappel
  au seuil 0,5 reste de 6 %. Le problème n'est pas l'algorithme.
- **La variable `taille` n'apporte strictement rien** à une régression logistique : c'est la somme
  de deux colonnes déjà présentes, le modèle linéaire savait déjà la calculer. Bon exemple de
  variable redondante.
- **La variable `risque_x_taille`** (taux de casse passé du fichier × (1 + taille / 150), taille
  plafonnée à 300) traduit l'hypothèse H1 en interaction : un gros changement dans un fichier fragile.
  Gain faible avec les autres variables (0,750), mais **seule, elle obtient la meilleure AUC du
  tableau (0,772)** : un modèle à une variable bien choisie bat un modèle à neuf variables dont
  plusieurs sont du bruit. La connaissance du domaine compte plus que le choix de l'algorithme.
- **Retirer la variable « auteur » ne coûte rien** (0,746 avec ou sans, 0,753 avec `balanced`). On peut
  donc suivre la recommandation éthique de l'énoncé sans perte.
- Toutes ces AUC sont dans un mouchoir (0,72 à 0,77) et l'ensemble de test ne compte que 54 casses :
  un écart de 0,01 n'est pas significatif. Ne pas laisser les stagiaires conclure sur la troisième
  décimale.

### Quelle variante si un faux positif coûte 2 min et un faux négatif 1 h ?

Coût total sur l'ensemble de test = 2 × FP + 60 × FN (en minutes) :

| Stratégie | FP | FN | Coût |
|---|---|---|---|
| Ne jamais alerter (référence naïve) | 0 | 54 | 3 240 min |
| Défaut (seuil 0,5) | 1 | 54 | 3 242 min |
| `RandomForestClassifier` | 3 | 51 | 3 066 min |
| Seuil 0,3 | 2 | 49 | 2 944 min |
| `class_weight="balanced"` | 66 | 28 | 1 812 min |
| `risque_x_taille` + `balanced` | 60 | 28 | 1 800 min |
| Régression logistique, seuil 0,1 | 149 | 2 | 418 min |
| Régression logistique, seuil 0,08 (minimum mesuré) | 155 | 1 | 370 min |
| Toujours alerter (lancer les tests ciblés à chaque fois) | 267 | 0 | 534 min |

Réponse attendue : **parmi les variantes de l'énoncé, `class_weight="balanced"`**, qui divise le coût
par 1,8 par rapport au défaut (1 812 min contre 3 242). Le modèle « par défaut », qui a la meilleure
exactitude, est le pire choix économique : il coûte autant que de ne rien faire.

Réponse complète, pour les groupes à l'aise : quand un faux négatif coûte 30 fois plus qu'un faux
positif, il faut alerter dès que la probabilité dépasse 2 / (2 + 60) ≈ 0,03. Le seuil se déduit des
coûts, pas d'une habitude (0,5) ni d'une valeur proposée (0,3). Mesuré : avec la régression
logistique par défaut, le coût minimal est atteint vers 0,08 (370 min) et le seuil 0,1 donne 418 min.
C'est mieux que « toujours lancer les tests ciblés » (534 min), mais de peu : avec de tels coûts, on
lance les tests presque toujours, et l'apport du modèle est surtout de dire **dans quel ordre**. C'est
exactement l'usage de l'étape 4.

Réserve à énoncer : le seuil 0,08 a été choisi en regardant l'ensemble de test, il est donc optimiste.
En toute rigueur on le choisit sur une troisième tranche de données (validation), située entre
l'apprentissage et le test.

## Étape 4 — Prioriser les tests

### Prédiction

```bash
python ai_tools/risk_model.py predict --files minishop/pricing.py minishop/static/style.css
cat reports/tests_to_run.txt
```

```text
Risque estimé par fichier modifié :
   29.4%  minishop/pricing.py
    1.9%  minishop/static/style.css

Ordre de test proposé : tests/unit/test_pricing.py tests/generated tests/e2e tests/visual
```

`reports/tests_to_run.txt` contient la même liste sur une ligne, séparée par des espaces ;
`reports/risk.json` contient les probabilités. Les fichiers sont triés par risque décroissant, puis
chaque fichier apporte ses tests d'après `TEST_MAP`, sans doublon.

Essai local de la sélection (dépôt de départ, sans application lancée) :

```bash
pytest -x -m "not e2e and not visual" $(cat reports/tests_to_run.txt)    # 3 passed, 3 deselected
```

Cas limites mesurés avec l'étape « tests ciblés » de l'énoncé, à montrer :

| Changement | Ordre proposé | Effet de l'étape de l'énoncé |
|---|---|---|
| `style.css` seul | `tests/e2e tests/visual` | tout est désélectionné : code retour **5** (« aucun test »), que l'énoncé demande de tolérer |
| `README.md` seul | aucun test ciblé, fichier vide | le test `-gt 0` saute l'étape (code 0) ; sans lui, pytest lancerait **toute la suite** deux fois |
| `minishop/nouveau.py` (inconnu du modèle) | aucun test | risque estimé 9,3 % : démarrage à froid, le modèle n'a que `is_code` et la taille |

Deux observations sur le modèle lui-même :

- le risque de `pricing.py` vaut 29,4 % dans un changement de 2 fichiers et 16,0 % dans un changement
  de 10 fichiers. C'est l'effet du coefficient négatif appris par hasard sur `files_in_commit` :
  l'ordre reste utilisable, la valeur absolue beaucoup moins (l'énoncé le signale dans « Éthique &
  limites ») ;
- `stock.py` et `search.py` ont un risque élevé mais ne figurent pas dans `TEST_MAP` (et n'existent
  pas dans le dépôt : ils ne sont présents que dans l'historique simulé). Un fichier risqué sans test
  associé est une information pour l'étape 5.

### Dans la CI

L'extrait de l'énoncé, placé dans un workflow de pull request (validé par `actionlint`) :

```yaml
- run: python ai_tools/risk_model.py predict --git-diff origin/${{ github.base_ref }}
- name: D'abord les tests ciblés (échec rapide)
  run: |
    read -r -a TARGETS < reports/tests_to_run.txt || true    # liste séparée par des espaces
    if [ "${#TARGETS[@]}" -gt 0 ]; then                       # liste vide (PR de documentation) : rien à cibler
      pytest -x -m "not e2e and not visual" "${TARGETS[@]}"
    fi
- run: pytest -m "not e2e and not visual"                                      # puis la suite complète
```

Il reste aux stagiaires à tolérer le code 5 (PR purement CSS), comme l'énoncé le demande. La version
complète est dans `formateur/solutions/workflows/ml-insights.yml`, job `risk-based-tests`
(`actionlint` : aucune erreur) :

```yaml
jobs:
  risk-based-tests:
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }          # sans l'historique, origin/<base> n'existe pas pour git diff
      # … installation, simulate_history.py, risk_model.py train …
      - name: Prédire le risque des fichiers modifiés
        env:                                  # jamais de ${{ … }} directement dans un script : injection de commandes
          BASE_REF: ${{ github.base_ref }}
          PR_AUTHOR: ${{ github.actor }}
        run: python ai_tools/risk_model.py predict --git-diff "origin/$BASE_REF" --author "$PR_AUTHOR"
      - name: Lancer d'abord les tests les plus risqués (échec rapide)
        run: |
          read -r -a TARGETS < reports/tests_to_run.txt || true
          if [ "${#TARGETS[@]}" -gt 0 ]; then
            pytest -x -m "not e2e and not visual" "${TARGETS[@]}" || [ $? -eq 5 ]
          fi
      - name: Puis le reste de la suite
        run: pytest -m "not e2e and not visual" -q
```

- `fetch-depth: 0` : par défaut, `actions/checkout` ne récupère qu'un commit et `git diff origin/main`
  échoue.
- Le modèle est ré-entraîné à chaque run (quelques secondes) : `reports/risk_model.pkl` n'est pas
  versionné. Sur un vrai projet, on l'entraîne dans un job planifié et on le publie en artefact.
- `|| [ $? -eq 5 ]` tolère le code 5 d'une PR purement CSS : c'est la seule différence avec l'étape
  de l'énoncé.
- Les valeurs issues de l'événement (`github.base_ref`, `github.actor`) passent par `env:` plutôt que
  d'être écrites dans le script : une valeur contrôlée par l'auteur de la PR ne doit jamais être
  interprétée par le shell. Bonne habitude à faire prendre, même si l'extrait de l'énoncé reste simple.

Vérification locale de cette étape, dans un dépôt Git de test (branche `main`, puis une branche où
l'on change `BULK_QTY = 10` en `11` dans `pricing.py` et où l'on ajoute une ligne à `style.css`) :

```text
$ python ai_tools/risk_model.py predict --git-diff main --author octocat
Risque estimé par fichier modifié :
   21.4%  minishop/pricing.py
    1.2%  minishop/static/style.css

$ # puis le script de l'étape « Lancer d'abord les tests les plus risqués », exécuté tel quel
FAILED tests/unit/test_pricing.py::test_remise_volume_a_partir_de_10 - Assert...
!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!!!
================== 1 failed, 6 passed, 3 deselected in 0.18s ===================
```

Le défaut est trouvé après 7 tests au lieu des 52 de la suite complète (tests des solutions des
ateliers 1 et 9 installés). Avec la PR CSS seule, l'étape se termine avec le code 0 (« 3 deselected ») ;
sans aucun fichier modifié, elle ne lance rien. Sur MiniShop le gain de temps est insignifiant (0,18 s
contre 0,33 s) : le dire franchement. L'ordre de test devient intéressant quand la suite dure des
minutes ; ici on apprend le mécanisme.

### Remplacer `TEST_MAP` par une table déduite de la couverture

Avec `--cov-context=test`, coverage.py enregistre pour chaque ligne exécutée le test qui l'a
exécutée. `coverage json --show-contexts` exporte cette information : dans chaque fichier, une
entrée `contexts` associe un numéro de ligne à une liste de la forme
`tests/unit/test_pricing.py::test_money_arrondi_commercial|run` (une chaîne vide désigne le code
exécuté à l'import, hors de tout test).

```bash
pytest -m "not e2e and not visual" --cov --cov-context=test
coverage json --show-contexts -o reports/coverage-contexts.json
python ai_tools/coverage_test_map.py          # écrit reports/test_map.json
```

Le cœur du script (`build()` dans `coverage_test_map.py`) :

```python
for source, data in report["files"].items():
    for line, contexts in data.get("contexts", {}).items():
        for ctx in contexts:
            if not ctx:  # contexte vide = exécuté à l'import, hors de tout test
                continue
            test_id = ctx.split("|")[0]  # « tests/x.py::test_y|run » -> « tests/x.py::test_y »
            detail[source][test_id.split("::")[0]].add(line)
```

Pour chaque fichier source, on compte les lignes exécutées par chaque fichier de test, et on trie par
nombre décroissant : le fichier de test qui traverse le plus le module passe en premier.

Résultat avec les tests de l'Atelier 1 (solution) et les tests d'API de départ, c'est-à-dire l'état
normal d'un stagiaire à ce stade (38 tests, couverture totale 85 %) :

| Fichier source | Fichier de test | Lignes du fichier exécutées par ces tests |
|---|---|---|
| `minishop/api.py` | `tests/api/test_api_smoke.py` | 18 |
| `minishop/catalog.py` | `tests/unit/test_pricing.py` | 4 |
| `minishop/catalog.py` | `tests/api/test_api_smoke.py` | 1 |
| `minishop/pricing.py` | `tests/unit/test_pricing.py` | 49 |

Résultat une fois les tests d'API de l'Atelier 9 (solution) ajoutés (52 tests, couverture 97 %) :

| Fichier source | Fichier de test | Lignes du fichier exécutées par ces tests |
|---|---|---|
| `minishop/api.py` | `tests/api/test_api.py` | 40 |
| `minishop/api.py` | `tests/api/test_api_smoke.py` | 18 |
| `minishop/catalog.py` | `tests/api/test_api.py` | 4 |
| `minishop/catalog.py` | `tests/unit/test_pricing.py` | 4 |
| `minishop/catalog.py` | `tests/api/test_api_smoke.py` | 1 |
| `minishop/pricing.py` | `tests/unit/test_pricing.py` | 49 |
| `minishop/pricing.py` | `tests/api/test_api.py` | 40 |

Avec le dépôt de départ, sans aucun test ajouté (5 tests, couverture 63 %), la table se réduit à
trois lignes : `api.py` → `test_api_smoke.py` (18), `catalog.py` → `test_api_smoke.py` (1),
`pricing.py` → `tests/unit/test_pricing.py` (18).

Le fichier `reports/test_map.json` obtenu dans le second cas :

```json
{
  "minishop/api.py": ["tests/api/test_api.py", "tests/api/test_api_smoke.py"],
  "minishop/catalog.py": ["tests/api/test_api.py", "tests/unit/test_pricing.py", "tests/api/test_api_smoke.py"],
  "minishop/pricing.py": ["tests/unit/test_pricing.py", "tests/api/test_api.py"],
  "minishop/static/": ["tests/e2e", "tests/visual"]
}
```

Ce que la table mesurée apprend par rapport à la table manuelle :

- `pricing.py` est aussi exercé par les tests d'API (40 lignes) : la table manuelle l'ignorait et
  proposait `tests/generated`, qui est vide dans le dépôt de départ ;
- `catalog.py` est exercé par `tests/unit/test_pricing.py` (les tests de devis lisent le catalogue) ;
- la table se met à jour toute seule quand on ajoute des tests, alors que `TEST_MAP` vieillit.

Ses limites, à dire :

- seuls les fichiers Python mesurés apparaissent. Le HTML et le CSS ne sont pas « couverts » : le
  script conserve pour eux la règle manuelle `minishop/static/` → `tests/e2e`, `tests/visual` ;
- les tests e2e pilotent un serveur lancé dans un autre processus : ils ne laissent pas de trace ici ;
- il faut avoir exécuté toute la suite une fois pour construire la table. Dans une CI, on la
  construit sur la branche principale (job planifié ou après fusion) et on la publie en artefact ;
- un test qui exécute une ligne ne la vérifie pas forcément : l'option `--min-lines` écarte les tests
  qui ne font qu'effleurer un module (avec `--min-lines 5`, `catalog.py` sort de la table).

Pour brancher la table, la version de solution de `risk_model.py` ajoute une fonction et change une
ligne de `predict()` :

```python
TEST_MAP_FILE = Path("reports/test_map.json")  # produite par ai_tools/coverage_test_map.py


def load_test_map() -> dict[str, list[str]]:
    """Table déduite de la couverture si elle existe, sinon la table manuelle."""
    if TEST_MAP_FILE.exists():
        return json.loads(TEST_MAP_FILE.read_text(encoding="utf-8"))
    return TEST_MAP
```

Résultat avec la table mesurée (tests des ateliers 1 et 9) :

```text
$ python ai_tools/risk_model.py predict --files minishop/pricing.py minishop/static/style.css
Ordre de test proposé : tests/unit/test_pricing.py tests/api/test_api.py tests/e2e tests/visual
$ pytest -x -q -m "not e2e and not visual" $(cat reports/tests_to_run.txt)
50 passed, 3 deselected
```

Avec la table manuelle, la même commande ne lançait que 36 tests : les 14 tests de
`tests/api/test_api.py`, qui traversent pourtant `pricing.py`, étaient oubliés.

## Étape 5 — Analyser les métriques de test

### Construire le tableau de bord

```bash
pytest -m "not e2e and not visual" --cov && coverage json -o reports/coverage.json
python ai_tools/mutation_score.py minishop/pricing.py tests/unit > reports/mutation-pricing.txt
python ai_tools/mutation_score.py minishop/api.py tests/api      > reports/mutation-api.txt
python ai_tools/mutation_score.py minishop/catalog.py tests/unit > reports/mutation-catalog.txt
python ai_tools/test_dashboard.py            # affiche et écrit reports/test-dashboard.md
```

Les trois calculs de mutation prennent moins de 2 minutes au total sur la machine d'essai
(40, 21 et 11 mutants). Le modèle
doit avoir été entraîné (`reports/risk_model.pkl`) et l'historique simulé doit être présent.

Le script croise cinq sources : la couverture (`coverage json`), le score de mutation (lu dans la
sortie de `mutation_score.py`), l'historique Git (nombre de modifications et taux de casse), les
échecs de l'historique JUnit de l'Atelier 5, et le risque prédit par le modèle pour un changement
type (30 lignes ajoutées, 10 supprimées, fichier seul dans son commit : les valeurs par défaut de
`predict --files`). Deux choix sont explicites dans le code et à discuter :

- les tests de l'historique sont rattachés à un module par une table (`HISTORY_MAP`), par exemple
  `tests.unit.test_pricing` → `minishop/pricing.py`. C'est une hypothèse de lecture ;
- les échecs dont le message est une panne d'environnement (« Connection refused ») sont comptés à
  part : ils ne disent rien de la qualité du module (Atelier 5, familles 2 et 4).

Résultat, avec les tests de l'Atelier 1 (solution) et les tests d'API de départ :

| Module | Couverture | Score de mutation | Modifs (Git) | Taux de casse | Échecs historiques (code / infra) | Risque prédit | Priorité |
|---|---|---|---|---|---|---|---|
| `minishop/stock.py` | n.d. | n.d. | 137 | 38,7 % | 0 / 2 | 32,8 % | 0,328 |
| `minishop/api.py` | 66 % | 1/21 = 5 % | 127 | 26,8 % | 0 / 3 | 27,9 % | 0,266 |
| `minishop/search.py` | n.d. | n.d. | 164 | 18,3 % | 0 / 1 | 24,1 % | 0,241 |
| `minishop/static/index.html` | n.d. | n.d. | 154 | 15,6 % | 5 / 0 | 23,2 % | 0,232 |
| `minishop/catalog.py` | 100 % | 0/11 = 0 % | 134 | 9,0 % | 0 / 0 | 21,1 % | 0,211 |
| `minishop/pricing.py` | 100 % | 35/40 = 88 % | 140 | 35,7 % | 4 / 0 | 31,5 % | 0,039 |
| `minishop/static/style.css` | n.d. | n.d. | 142 | 2,1 % | 0 / 0 | 2,1 % | 0,021 |

Priorité = risque prédit × (1 − protection), où la protection est le score de mutation, à défaut la
couverture, à défaut 0. C'est un indicateur de tri volontairement simple, pas une vérité : le
présenter comme une proposition à critiquer. « n.d. » signifie que rien n'a été mesuré.

### Où investir la semaine prochaine ? Recommandation rédigée

**Priorité 1 — `minishop/api.py` : écrire de vrais tests d'API.** C'est le module existant le plus
exposé et le moins protégé : un changement sur quatre y casse la CI (26,8 %), le modèle lui donne
27,9 % de risque, et les tests actuels n'en vérifient presque rien. La couverture de 66 % est
trompeuse : un seul mutant sur 21 est détecté (5 %). On peut changer les codes 404, 422 ou 201 de
l'API sans qu'aucun test ne s'en aperçoive. Effort proposé : une journée de tests sur `/products/{id}`,
`/cart/quote`, `/orders` (codes de retour, corps, cas d'erreur). C'est le contenu de l'Atelier 9.
Effet mesuré avec les tests de la solution de l'Atelier 9 : couverture 94 %, score de mutation 8/21
= 38 %, priorité ramenée de 0,266 à 0,173. Le score reste moyen : les mutants restants touchent les
bornes de validation (`qty` ≤ 99), le middleware de mesure et la longueur de l'identifiant de
commande, à traiter ensuite.

**Priorité 2 — `stock.py` et `search.py` : mesurer avant tout.** Ils sont en tête ou presque
(38,7 % et 18,3 % de casse, 137 et 164 modifications), et l'on n'a ni couverture ni score de
mutation. Dans ce dépôt de formation, c'est parce que ces deux modules n'existent que dans
l'historique simulé. Sur un vrai projet, la lecture serait : un module très modifié, qui casse
souvent, et pour lequel on ne sait rien de ses tests, est la première chose à instrumenter. Leurs
échecs historiques sont tous des pannes d'infrastructure (base de données, réseau), ce qui relève de
la fiabilité de l'environnement, pas de nouveaux tests.

**Priorité 3 — `static/index.html` : fiabiliser le test existant plutôt qu'en ajouter.** Les 5 échecs
historiques sont ceux du test e2e instable de l'Atelier 5. Ajouter des tests e2e au-dessus d'un test
instable augmenterait le bruit. Effort proposé : une demi-journée pour corriger l'attente du bouton
de commande, puis sortir le test de quarantaine.

**À ne pas faire — réinvestir dans `pricing.py`.** C'est le module qui casse le plus (35,7 %) et son
risque prédit est le deuxième (31,5 %), mais il est déjà bien protégé : couverture 100 %, 35 mutants
sur 40 détectés. Les 4 échecs historiques sont la régression des runs 48 à 51, que les tests ont
justement attrapée. Les 5 mutants survivants portent sur des constantes décimales (`'4.90'` devenu
`'4.901'`, valeurs initiales `'0.00'`) que l'arrondi au centime rend probablement équivalentes. Le
modèle seul aurait désigné `pricing.py` : c'est le croisement avec la protection qui change la
décision.

**À relativiser — `catalog.py`.** Couverture 100 % et score de mutation 0/11 : l'exemple le plus net
de l'écart entre « exécuté » et « vérifié ». Mais les mutants sont des modifications de données (prix
augmenté d'un millième, stock augmenté de 1), le module casse rarement (9,0 %) et ne contient presque
pas de logique. Un test de contenu du catalogue suffit, en une heure. Remarque : le risque prédit
(21,1 %) est très au-dessus du taux observé (9,0 %) ; le modèle surestime tout fichier de code, à
cause du poids de `is_code`. Les probabilités ne sont pas calibrées : s'en servir pour classer, pas
pour chiffrer.

**`style.css`** : rien à faire (2,1 %).

En résumé : la semaine prochaine, l'effort va aux tests d'API, puis à la stabilisation du test e2e ;
`pricing.py` est laissé en l'état. Aucun test n'est supprimé sur la foi du modèle.

## Critères de réussite

| Critère | Démonstration |
|---|---|
| Modèle entraîné, évalué correctement (AUC, rappel), piège de l'exactitude expliqué | Étape 2 |
| Au moins 2 variantes comparées, choix argumenté par le coût des erreurs | Étape 3 : 7 variantes de l'énoncé, 7 complémentaires, tableau des coûts |
| La sélection de tests par risque tourne dans un workflow de PR | Étape 4 : workflow validé par `actionlint`, étape exécutée localement avec `--git-diff` ; exécution sur GitHub non vérifiée |
| Recommandation écrite d'investissement de test | Étape 5 |

## Points d'animation

**Erreurs fréquentes**

- Se réjouir des 83 % d'exactitude. Faire calculer la part de « ok » dans le test (267 / 321 = 83 %)
  avant de lire le rapport.
- Lancer `predict` avant `train` : `reports/risk_model.pkl` n'existe pas, le script s'arrête sur
  `FileNotFoundError`. De même, un `reports/` supprimé entre deux ateliers impose de ré-entraîner.
- Ajouter une variable dans `featurize()` et oublier `FEATURES` et la construction du vecteur dans
  `predict()` : l'entraînement s'arrête à l'affichage des coefficients (`ValueError: zip() argument 2 is longer
  than argument 1`), et la prédiction échouerait ensuite sur le nombre de colonnes. C'est pourquoi la solution passe par un script
  d'expérience séparé.
- Calculer une nouvelle variable « historique » avec un `groupby` sur tout le fichier : c'est la
  fuite de données de l'étape 2. Demander systématiquement : « cette valeur était-elle connue au
  moment du commit ? »
- Comparer des variantes à des seuils différents sans regarder l'AUC, ou conclure sur un écart
  d'AUC de 0,005.
- Étape 4 : oublier `--cov-context=test` (la table est vide, le script le signale) ou oublier
  `--show-contexts` à l'export. Lancer `pytest --cov` sans le filtre `-m` : les tests e2e et visuels
  échouent faute d'application démarrée.
- Étape 5 : lancer `mutation_score.py minishop/api.py tests` sur tout le dossier : le script répond
  « Les tests échouent déjà sur le code non muté », parce que les tests e2e n'ont pas d'application.
  Donner un dossier précis (`tests/unit`, `tests/api`).
- Étape 5 : interrompre `mutation_score.py` brutalement. Le script restaure le fichier source dans un
  `finally`, mais après un arrêt forcé vérifier avec `git status` que `minishop/` est intact.

**Questions de discussion**

- *Le modèle par auteur est-il acceptable ?* Éléments : H3 montre qu'il fige une situation passée ;
  la variable n'apporte rien en AUC (0,746 avec ou sans) ; la retirer est gratuit. Un indicateur
  individuel de « casse » pousse aussi à moins committer ou à éviter les modules difficiles.
- *Que fait le modèle d'un nouveau fichier ?* Mesuré : 9,3 % pour `minishop/nouveau.py`, moins que
  tous les modules connus. Le code neuf, souvent le plus risqué, est celui que le modèle connaît le
  moins. D'où la règle : on réordonne, on ne retire jamais de tests.
- *Pourquoi le modèle simple bat-il les modèles complexes ?* 963 lignes d'apprentissage, 9 variables
  dont plusieurs sans effet réel : les modèles souples apprennent le bruit.
- *Le coût d'un faux positif est-il vraiment de 2 minutes ?* Si l'alerte bloque une fusion ou exige
  une revue supplémentaire, le coût change et le seuil optimal aussi. Refaire le calcul avec 15 min.
- *Les données sont simulées : qu'est-ce qui changerait en vrai ?* L'étiquette « ce commit a cassé
  la CI » est difficile à obtenir (tests instables, casses dues à l'infrastructure : voir Atelier 5),
  et un commit casse rarement à cause d'un seul fichier.

**Durée à surveiller**

- Étape 1 : limiter à 25 minutes ; trois hypothèses, pas dix. Le script de solution peut être donné
  aux stagiaires qui ne connaissent pas pandas.
- Étape 3 : c'est la plus longue. Si le groupe est en retard, faire les variantes `balanced` et
  « seuil » à la main, puis distribuer `risk_experiments.py` pour le reste et passer au calcul du coût.
- Étape 5 : les calculs de mutation prennent moins de 2 minutes sur la machine d'essai ; les lancer avant
  d'expliquer le tableau. Garder 10 minutes pour que chaque binôme rédige sa recommandation.

## Non vérifié

- **Exécution du workflow sur GitHub Actions** (déclenchement sur pull request, `origin/<base>`,
  `github.actor`) : seuls `actionlint` et l'exécution locale des commandes, dans un dépôt Git de
  test, ont été faits.
- **Publication de la table de couverture en artefact** entre un job planifié et le job de PR :
  décrite, non mise en place ni exécutée.
- **Variante PowerShell** de la commande de sélection : non exécutée (essais sous Linux uniquement).
- **Équivalence des 5 mutants survivants de `pricing.py`** : jugée probable à la lecture du code,
  non démontrée.
- L'étape 1 est faite avec un script ; l'usage dans un notebook n'a pas été essayé.

---

## Fichiers de cet atelier

Par rapport à la branche `python/atelier-05` :

| | Fichier |
|---|---|
| ajouté | `.github/workflows/ml-insights.yml` |
| ajouté | `ai_tools/coverage_test_map.py` |
| ajouté | `ai_tools/explore_history.py` |
| ajouté | `ai_tools/risk_experiments.py` |
| modifié | `ai_tools/risk_model.py` |
| ajouté | `ai_tools/test_dashboard.py` |

### `.github/workflows/ml-insights.yml`

````yaml
# SOLUTION Ateliers 5 & 6 — Anomalies, flakiness, priorisation des tests par ML
name: ML - insights tests

on:
  pull_request:
  schedule:
    - cron: "0 6 * * 1-5"       # analyse quotidienne de l'historique
  workflow_dispatch:

permissions:
  contents: read

jobs:
  risk-based-tests:
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: actions/setup-python@v5
        with: { python-version: "3.12", cache: pip }
      - run: pip install -r requirements-dev.txt
      - run: python scripts/simulate_history.py         # en vrai : historique Git + JUnit réels
      - run: python ai_tools/risk_model.py train data/git-history.csv
      - name: Prédire le risque des fichiers modifiés
        env:                                  # jamais de ${{ … }} directement dans un script : injection de commandes
          BASE_REF: ${{ github.base_ref }}
          PR_AUTHOR: ${{ github.actor }}
        run: python ai_tools/risk_model.py predict --git-diff "origin/$BASE_REF" --author "$PR_AUTHOR"
      - name: Lancer d'abord les tests les plus risqués (échec rapide)
        run: |
          read -r -a TARGETS < reports/tests_to_run.txt || true      # liste séparée par des espaces, parfois vide
          if [ "${#TARGETS[@]}" -gt 0 ]; then
            # code 5 = aucun test sélectionné (PR qui ne touche que minishop/static/ -> e2e/visuel, lancés ailleurs)
            pytest -x -m "not e2e and not visual" "${TARGETS[@]}" || [ $? -eq 5 ]
          fi
      - name: Puis le reste de la suite
        run: pytest -m "not e2e and not visual" -q

  history-and-anomalies:
    if: github.event_name != 'pull_request'    # analyse quotidienne (ou lancée à la main), pas à chaque PR
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12", cache: pip }
      - run: pip install -r requirements-dev.txt
      - run: python scripts/simulate_history.py
      - name: Analyse de l'historique (flaky, lenteurs, familles d'échecs)
        run: python ai_tools/test_history.py data/junit-history --report reports/test-insights.md
      - name: Anomalies dans les logs d'un run réel
        run: |
          MINISHOP_LOG_FILE=logs/app.jsonl uvicorn minishop.api:app --port 8000 &
          timeout 30 bash -c 'until curl -sf localhost:8000/health; do sleep 1; done'
          locust -f tests/perf/locustfile.py --host http://localhost:8000 --headless -u 20 -r 5 -t 60s || true
          # 60 s en fenêtres de 5 s : il faut au moins 10 fenêtres, sinon l'outil n'analyse rien
          python ai_tools/log_anomalies.py logs/app.jsonl --window 5 --report reports/anomalies-run.md
          python ai_tools/log_anomalies.py data/app-logs.jsonl --report reports/anomalies-simulees.md
      - run: cat reports/test-insights.md >> "$GITHUB_STEP_SUMMARY"
      - uses: actions/upload-artifact@v4
        with: { name: ml-insights, path: reports/ }
````

### `ai_tools/coverage_test_map.py`

````python
"""Atelier 6, étape 4 — déduire la table fichier -> tests de la couverture, au lieu de TEST_MAP manuelle.

Principe : avec `--cov-context=test`, coverage.py note pour chaque ligne exécutée QUEL test l'a
exécutée. On en déduit, pour chaque fichier source, les fichiers de test qui le traversent, classés
par nombre de lignes couvertes (les plus pertinents d'abord).

Usage (depuis la racine du dépôt) :
    pytest -m "not e2e and not visual" --cov --cov-context=test
    coverage json --show-contexts -o reports/coverage-contexts.json
    python ai_tools/coverage_test_map.py                 # écrit reports/test_map.json
    python ai_tools/coverage_test_map.py --min-lines 3   # ignore les tests qui ne font qu'effleurer

Limites : seuls les fichiers Python mesurés apparaissent. Les fichiers statiques (HTML, CSS) ne sont
pas « couverts » : on garde pour eux une règle manuelle (STATIC_RULES). Les tests e2e pilotent un
serveur dans un autre processus : sans configuration particulière, ils ne laissent pas de trace ici.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

STATIC_RULES = {"minishop/static/": ["tests/e2e", "tests/visual"]}


def build(report: dict, min_lines: int) -> tuple[dict[str, list[str]], dict[str, dict[str, int]]]:
    """Retourne (table fichier -> fichiers de test triés, détail fichier -> {fichier de test: lignes})."""
    detail: dict[str, dict[str, set]] = defaultdict(lambda: defaultdict(set))
    for source, data in report["files"].items():
        for line, contexts in data.get("contexts", {}).items():
            for ctx in contexts:
                if not ctx:  # contexte vide = exécuté à l'import, hors de tout test
                    continue
                test_id = ctx.split("|")[0]  # « tests/x.py::test_y|run » -> « tests/x.py::test_y »
                detail[source][test_id.split("::")[0]].add(line)
    table, counts = {}, {}
    for source in sorted(detail):
        c = {t: len(lines) for t, lines in detail[source].items() if len(lines) >= min_lines}
        if c:
            counts[source] = dict(sorted(c.items(), key=lambda kv: (-kv[1], kv[0])))
            table[source] = list(counts[source])
    return table, counts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--coverage-json", type=Path, default=Path("reports/coverage-contexts.json"))
    ap.add_argument("--out", type=Path, default=Path("reports/test_map.json"))
    ap.add_argument("--min-lines", type=int, default=1, help="nb min. de lignes du fichier exécutées par le test")
    args = ap.parse_args()

    report = json.loads(args.coverage_json.read_text(encoding="utf-8"))
    if not report.get("meta", {}).get("show_contexts"):
        print("Rapport sans contextes : relancez `coverage json --show-contexts`.")
        return 2
    table, counts = build(report, args.min_lines)
    if not table:
        print("Aucun contexte de test : relancez pytest avec `--cov --cov-context=test`.")
        return 2

    print("| Fichier source | Fichier de test | Lignes du fichier exécutées par ces tests |")
    print("|---|---|---|")
    for source, tests in counts.items():
        for test, n in tests.items():
            print(f"| `{source}` | `{test}` | {n} |")
    table.update(STATIC_RULES)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(table, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nTable écrite dans {args.out} ({len(table)} entrées, dont {len(STATIC_RULES)} règle(s) manuelle(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
````

### `ai_tools/explore_history.py`

````python
"""Atelier 6, étape 1 — exploration de data/git-history.csv et vérification de trois hypothèses.

Usage (depuis la racine du dépôt, après `python scripts/simulate_history.py`) :
    python ai_tools/explore_history.py data/git-history.csv
"""

from __future__ import annotations

import sys

import pandas as pd

pd.set_option("display.width", 120)


def taux(serie: pd.Series) -> pd.DataFrame:
    """Taux de casse et effectif par groupe."""
    return serie.agg(taux="mean", lignes="size").round({"taux": 3})


def main() -> int:
    df = pd.read_csv(sys.argv[1] if len(sys.argv) > 1 else "data/git-history.csv")
    df["num"] = df.commit.str[1:].astype(int)
    df["taille"] = df.lines_added + df.lines_deleted

    print(f"{len(df)} lignes, {df.commit.nunique()} commits")
    print(f"Taux de casse global : {df.broke_ci.mean():.3f}\n")
    print("Par fichier :")
    print(taux(df.groupby("file").broke_ci).sort_values("taux"), "\n")
    print("Par auteur :")
    print(taux(df.groupby("author").broke_ci), "\n")

    print("H1 — les gros changements cassent plus (taille = lignes ajoutées + supprimées)")
    tranches = pd.cut(df.taille, [0, 10, 25, 50, 100, 10_000], labels=["1-10", "11-25", "26-50", "51-100", ">100"])
    print(taux(df.groupby(tranches, observed=True).broke_ci))
    print(f"corrélation taille / casse : {df.taille.corr(df.broke_ci):+.3f}\n")

    print("H2 — les commits tardifs (20 h et après) cassent plus")
    print(taux(df.groupby(df.hour >= 20).broke_ci).rename(index={False: "avant 20 h", True: "20 h et après"}), "\n")

    print("H3 — emma casse plus que les autres… mais seulement au début (commits 1 à 299)")
    periode = df.num.lt(300).map({True: "commits 1-299", False: "commits 300-600"})
    qui = df.author.eq("emma").map({True: "emma", False: "autres"})
    print(df.pivot_table(index=qui, columns=periode, values="broke_ci", aggfunc="mean").round(3), "\n")

    print("Complément — commits de correction, nombre de fichiers du commit")
    print(taux(df.groupby("is_fix_commit").broke_ci))
    print(taux(df.groupby("files_in_commit").broke_ci))
    return 0


if __name__ == "__main__":
    sys.exit(main())
````

### `ai_tools/risk_experiments.py`

````python
"""Atelier 6, étape 3 — comparer des variantes du modèle de risque sans modifier risk_model.py.

Même découpage que `risk_model.py train` : validation temporelle, 75 % de lignes les plus anciennes
pour apprendre, 25 % les plus récentes pour évaluer. Pour chaque variante : AUC, rappel et précision
sur la classe « casse », matrice de confusion, et coût des erreurs
(faux positif = 2 min de tests lancés pour rien, faux négatif = 60 min de débogage).

Usage (depuis la racine du dépôt, après `python scripts/simulate_history.py`) :
    python ai_tools/risk_experiments.py data/git-history.csv
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, roc_auc_score
from sklearn.model_selection import train_test_split

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ai_tools.risk_model import FEATURES, featurize, load  # noqa: E402

COUT_FP_MIN = 2  # tests ciblés lancés pour rien
COUT_FN_MIN = 60  # casse non anticipée : débogage
COL = {name: i for i, name in enumerate(FEATURES)}


def nouvelles_variables(X: np.ndarray) -> np.ndarray:
    """Deux variables ajoutées, dérivées de colonnes déjà « sans fuite » de featurize().

    - taille          : lines_added + lines_deleted (suggestion de l'énoncé) ;
    - risque_x_taille : taux de casse passé du fichier × (1 + taille / 150), taille plafonnée à 300.
                        Idée issue de l'exploration : un gros changement dans un fichier fragile
                        est plus dangereux que la somme des deux effets (interaction).
    """
    taille = X[:, COL["lines_added"]] + X[:, COL["lines_deleted"]]
    inter = X[:, COL["file_past_breaks_rate"]] * (1 + np.minimum(taille, 300) / 150)
    return np.column_stack([taille, inter])


def evaluer(nom: str, modele, X: np.ndarray, y: np.ndarray, cut: int, seuil: float = 0.5) -> dict:
    modele.fit(X[:cut], y[:cut])
    proba = modele.predict_proba(X[cut:])[:, 1]
    tn, fp, fn, tp = confusion_matrix(y[cut:], (proba >= seuil).astype(int), labels=[0, 1]).ravel()
    return {
        "nom": nom,
        "auc": roc_auc_score(y[cut:], proba),
        "rappel": tp / max(tp + fn, 1),
        "precision": tp / max(tp + fp, 1),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "cout": COUT_FP_MIN * fp + COUT_FN_MIN * fn,
        "proba": proba,
    }


def ligne(r: dict) -> str:
    return (
        f"| {r['nom']} | {r['auc']:.3f} | {r['rappel']:.0%} | {r['precision']:.0%} | "
        f"{r['tp']} | {r['fp']} | {r['fn']} | {r['cout']} |"
    )


def main() -> int:
    rows = load(Path(sys.argv[1] if len(sys.argv) > 1 else "data/git-history.csv"))
    X, y, _ = featurize(rows)
    extra = nouvelles_variables(X)
    X_taille = np.hstack([X, extra[:, :1]])
    X_inter = np.hstack([X, extra[:, 1:]])
    X_sans_auteur = np.delete(X, COL["author_past_breaks_rate"], axis=1)
    cut = int(len(X) * 0.75)
    n_test, n_casse = len(y) - cut, int(y[cut:].sum())
    print(f"{len(X)} lignes — apprentissage sur {cut}, test sur {n_test} dont {n_casse} casses\n")

    def lr(**kw):
        return LogisticRegression(max_iter=1000, **kw)

    def rf(**kw):
        return RandomForestClassifier(random_state=0, **kw)

    resultats = [
        evaluer("Défaut (régression logistique, seuil 0,5)", lr(), X, y, cut),
        evaluer('`class_weight="balanced"`', lr(class_weight="balanced"), X, y, cut),
        evaluer("Seuil de décision 0,3", lr(), X, y, cut, seuil=0.3),
        evaluer("`RandomForestClassifier`", rf(), X, y, cut),
        evaluer("Nouvelle variable `taille`", lr(), X_taille, y, cut),
        evaluer("Nouvelle variable `risque_x_taille`", lr(), X_inter, y, cut),
        evaluer("`risque_x_taille` + `balanced`", lr(class_weight="balanced"), X_inter, y, cut),
    ]
    entete = "| Variante | AUC | Rappel casse | Précision casse | VP | FP | FN | Coût (min) |"
    print(entete)
    print("|---|---|---|---|---|---|---|---|")
    for r in resultats:
        print(ligne(r))

    print("\nPour comparaison (hors énoncé) :")
    print(entete)
    print("|---|---|---|---|---|---|---|---|")
    autres = [
        evaluer("Gradient boosting (défaut du script)", GradientBoostingClassifier(random_state=0), X, y, cut),
        evaluer("Random forest + `balanced`", rf(class_weight="balanced"), X, y, cut),
        evaluer("Random forest, seuil 0,3", rf(), X, y, cut, seuil=0.3),
        evaluer("Régression logistique, seuil 0,1", lr(), X, y, cut, seuil=0.1),
        evaluer("Une seule variable : `risque_x_taille`", lr(), extra[:, 1:], y, cut),
        evaluer("Sans `author_past_breaks_rate`", lr(), X_sans_auteur, y, cut),
        evaluer("Sans `author_past_breaks_rate` + `balanced`", lr(class_weight="balanced"), X_sans_auteur, y, cut),
    ]
    for r in autres:
        print(ligne(r))

    print("\nRéférences sans modèle :")
    print(f"  ne jamais alerter  : {n_casse} FN -> {COUT_FN_MIN * n_casse} min")
    print(f"  toujours alerter   : {n_test - n_casse} FP -> {COUT_FP_MIN * (n_test - n_casse)} min")

    print("\nSeuil qui minimise le coût (régression logistique par défaut) :")
    proba, yt = resultats[0]["proba"], y[cut:]
    meilleurs = []
    for s in np.arange(0.02, 0.61, 0.02):
        pred = proba >= s
        fp, fn = int((pred & (yt == 0)).sum()), int((~pred & (yt == 1)).sum())
        meilleurs.append((COUT_FP_MIN * fp + COUT_FN_MIN * fn, round(float(s), 2), fp, fn))
    for cout, s, fp, fn in sorted(meilleurs)[:5]:
        print(f"  seuil {s:.2f} : {fp} FP, {fn} FN -> {cout} min")
    theorique = COUT_FP_MIN / (COUT_FP_MIN + COUT_FN_MIN)
    print(f"  seuil théorique si les probabilités sont calibrées : {theorique:.3f}")

    print("\nDémonstration de la fuite de données (à ne PAS faire) :")
    # 1) taux par fichier et par auteur calculés sur TOUT l'historique, futur compris
    f_n, f_b, a_n, a_b, c_n, c_b = (defaultdict(int) for _ in range(6))
    for r in rows:
        casse = int(r["broke_ci"])
        f_n[r["file"]] += 1
        f_b[r["file"]] += casse
        a_n[r["author"]] += 1
        a_b[r["author"]] += casse
        c_n[r["commit"]] += 1
        c_b[r["commit"]] += casse
    X_fuite = X.copy()
    X_fuite[:, COL["file_past_breaks_rate"]] = [f_b[r["file"]] / f_n[r["file"]] for r in rows]
    X_fuite[:, COL["author_past_breaks_rate"]] = [a_b[r["author"]] / a_n[r["author"]] for r in rows]
    print(f"  taux calculés sur tout l'historique         : AUC {evaluer('', lr(), X_fuite, y, cut)['auc']:.3f}")
    # 2) une variable qui contient l'étiquette de la ligne elle-même : taux de casse du commit
    X_commit = np.column_stack([X, [c_b[r["commit"]] / c_n[r["commit"]] for r in rows]])
    print(f"  + taux de casse du commit (contient la cible) : AUC {evaluer('', lr(), X_commit, y, cut)['auc']:.3f}")

    print("\nDécoupage aléatoire au lieu de temporel (20 graines, régression logistique) :")
    aucs = []
    for graine in range(20):
        Xa, Xb, ya, yb = train_test_split(X, y, test_size=0.25, random_state=graine, stratify=y)
        aucs.append(roc_auc_score(yb, lr().fit(Xa, ya).predict_proba(Xb)[:, 1]))
    print(f"  AUC moyenne {np.mean(aucs):.3f}, de {min(aucs):.3f} à {max(aucs):.3f} selon le tirage")
    return 0


if __name__ == "__main__":
    sys.exit(main())
````

### `ai_tools/risk_model.py`

Modification :

````diff
diff --git a/ai_tools/risk_model.py b/ai_tools/risk_model.py
index 46e3703..1df9fe6 100644
--- a/ai_tools/risk_model.py
+++ b/ai_tools/risk_model.py
@@ -1,5 +1,8 @@
 """Prédiction des zones à risque à partir de l'historique Git (apprentissage SUPERVISÉ).
 
+SOLUTION Atelier 6, étape 4 : seule différence avec la version du dépôt stagiaires, la table
+fichier -> tests est lue dans reports/test_map.json (déduite de la couverture) quand ce fichier existe.
+
 Idée : chaque ligne de data/git-history.csv = (commit, fichier modifié, caractéristiques)
 avec l'étiquette `broke_ci` (ce commit a-t-il cassé la CI ?). On entraîne un modèle qui,
 pour un NOUVEAU changement, estime la probabilité de casse -> on priorise les tests
@@ -52,6 +55,14 @@ TEST_MAP = {
     "minishop/api.py": ["tests/api", "tests/e2e"],
     "minishop/static/": ["tests/e2e", "tests/visual"],
 }
+TEST_MAP_FILE = Path("reports/test_map.json")  # produite par ai_tools/coverage_test_map.py (Atelier 6, étape 4)
+
+
+def load_test_map() -> dict[str, list[str]]:
+    """Table déduite de la couverture si elle existe, sinon la table manuelle."""
+    if TEST_MAP_FILE.exists():
+        return json.loads(TEST_MAP_FILE.read_text(encoding="utf-8"))
+    return TEST_MAP
 
 
 def load(path: Path) -> list[dict]:
@@ -167,8 +178,9 @@ def predict(files: list[tuple[str, int, int]], author: str, hour: int) -> int:
         scored.append((f, float(m.predict_proba(np.array(x, dtype=float))[0, 1])))
     scored.sort(key=lambda t: -t[1])
     order: list[str] = []
+    mapping = load_test_map()
     for f, _ in scored:
-        for prefix, tests in TEST_MAP.items():
+        for prefix, tests in mapping.items():
             if f.startswith(prefix):
                 order += [t for t in tests if t not in order]
     print("Risque estimé par fichier modifié :")
````

### `ai_tools/test_dashboard.py`

````python
"""Atelier 6, étape 5 — tableau de bord texte : où investir l'effort de test ?

Croise, pour chaque module :
  * la couverture                 (reports/coverage.json, produit par `coverage json`) ;
  * le score de mutation          (reports/mutation-<module>.txt, sortie de mutation_score.py) ;
  * l'historique Git              (data/git-history.csv : modifications et taux de casse) ;
  * les échecs de tests           (data/junit-history/*.xml, rattachés à un module par HISTORY_MAP) ;
  * le risque prédit par le modèle (reports/risk_model.pkl, pour un changement type).

Préparation (depuis la racine du dépôt) :
    python scripts/simulate_history.py
    python ai_tools/risk_model.py train data/git-history.csv
    pytest -m "not e2e and not visual" --cov && coverage json -o reports/coverage.json
    python ai_tools/mutation_score.py minishop/pricing.py tests/unit > reports/mutation-pricing.txt
    python ai_tools/mutation_score.py minishop/api.py tests/api      > reports/mutation-api.txt
    python ai_tools/mutation_score.py minishop/catalog.py tests/unit > reports/mutation-catalog.txt
Puis :
    python ai_tools/test_dashboard.py            # affiche et écrit reports/test-dashboard.md

Une donnée absente est affichée « n.d. » : c'est une information en soi (module non mesuré).
"""

from __future__ import annotations

import argparse
import csv
import json
import pickle  # noqa: S403 — modèle produit localement par risk_model.py
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ai_tools.test_history import load_runs  # noqa: E402

# Rattachement des tests de l'historique JUnit à un module (hypothèse de lecture, à adapter au projet).
# La clé la plus longue qui préfixe « classname::test » l'emporte.
HISTORY_MAP = {
    "tests.unit.test_pricing": "minishop/pricing.py",
    "tests.api.test_api": "minishop/api.py",
    "tests.api.test_api::test_recherche_produits": "minishop/search.py",
    "tests.e2e.test_parcours_achat": "minishop/static/index.html",
    "tests.integration.test_stock": "minishop/stock.py",
}
# Échecs à ne pas imputer au module : pannes d'environnement (voir Atelier 5, familles d'échecs).
INFRA = ("Connection refused", "could not connect")
# Changement type utilisé pour le risque prédit : mêmes valeurs que `risk_model.py predict --files <f>`.
CHANGE = {"added": 30, "deleted": 10, "files": 1, "author": "alice", "hour": 15}


def coverage_by_file(path: Path) -> dict[str, float]:
    if not path.exists():
        return {}
    files = json.loads(path.read_text(encoding="utf-8"))["files"]
    return {f.replace("\\", "/"): d["summary"]["percent_covered"] for f, d in files.items()}


def mutation_by_file(folder: Path, modules: list[str]) -> dict[str, tuple[int, int]]:
    out = {}
    for m in modules:
        f = folder / f"mutation-{Path(m).stem}.txt"
        if f.exists():
            found = re.search(r"Score de mutation : (\d+)/(\d+)", f.read_text(encoding="utf-8", errors="replace"))
            if found:
                out[m] = (int(found.group(1)), int(found.group(2)))
    return out


def git_stats(path: Path) -> dict[str, tuple[int, float]]:
    n, b = Counter(), Counter()
    with path.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            n[r["file"]] += 1
            b[r["file"]] += int(r["broke_ci"])
    return {f: (n[f], b[f] / n[f]) for f in n}


def history_failures(folder: Path) -> dict[str, dict[str, int]]:
    """Par module : échecs imputables au code ou au test (« code ») et pannes d'environnement (« infra »)."""
    out: dict[str, dict[str, int]] = defaultdict(lambda: {"code": 0, "infra": 0})
    keys = sorted(HISTORY_MAP, key=len, reverse=True)
    for run in load_runs(folder):
        for name, case in run["cases"].items():
            if not case["failed"]:
                continue
            module = next((HISTORY_MAP[k] for k in keys if name.startswith(k)), "(non rattaché)")
            out[module]["infra" if any(s in case["message"] for s in INFRA) else "code"] += 1
    return out


def predicted_risk(model_path: Path, files: list[str]) -> dict[str, float]:
    if not model_path.exists():
        return {}
    bundle = pickle.loads(model_path.read_bytes())  # noqa: S301
    m, st = bundle["model"], bundle["state"]
    ac, ab = st["author_commits"].get(CHANGE["author"], 0), st["author_breaks"].get(CHANGE["author"], 0)
    out = {}
    for f in files:
        fc, fb = st["file_commits"].get(f, 0), st["file_breaks"].get(f, 0)
        x = [
            CHANGE["added"],
            CHANGE["deleted"],
            CHANGE["files"],
            0,
            int(CHANGE["hour"] >= 20),
            fc,
            fb / fc if fc else 0.0,
            ab / ac if ac else 0.0,
            int(f.endswith((".py", ".html", ".js"))),
        ]
        out[f] = float(m.predict_proba(np.array([x], dtype=float))[0, 1])
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--git-history", type=Path, default=Path("data/git-history.csv"))
    ap.add_argument("--junit", type=Path, default=Path("data/junit-history"))
    ap.add_argument("--reports", type=Path, default=Path("reports"))
    ap.add_argument("--out", type=Path, default=Path("reports/test-dashboard.md"))
    args = ap.parse_args()

    git = git_stats(args.git_history)
    modules = sorted(f for f in git if f.startswith("minishop/"))
    cov = coverage_by_file(args.reports / "coverage.json")
    mut = mutation_by_file(args.reports, modules)
    fails = history_failures(args.junit)
    risk = predicted_risk(args.reports / "risk_model.pkl", modules)

    rows = []
    for m in modules:
        # Protection = ce que l'on sait de mieux sur la capacité des tests à détecter un bug dans ce module :
        # le score de mutation s'il existe, sinon la couverture, sinon 0 (rien de mesuré).
        if m in mut:
            protection = mut[m][0] / max(mut[m][1], 1)
        elif m in cov:
            protection = cov[m] / 100
        else:
            protection = 0.0
        rows.append((risk.get(m, 0.0) * (1 - protection), m))
    rows.sort(reverse=True)

    L = [
        "# Tableau de bord des tests par module",
        "",
        "| Module | Couverture | Score de mutation | Modifs (Git) | Taux de casse | Échecs historiques (code / infra) "
        "| Risque prédit | Priorité |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for prio, m in rows:
        c = f"{cov[m]:.0f} %" if m in cov else "n.d."
        s = f"{mut[m][0]}/{mut[m][1]} = {mut[m][0] / max(mut[m][1], 1):.0%}" if m in mut else "n.d."
        f = fails.get(m, {"code": 0, "infra": 0})
        r = f"{risk[m]:.1%}" if m in risk else "n.d."
        L.append(
            f"| `{m}` | {c} | {s} | {git[m][0]} | {git[m][1]:.1%} | {f['code']} / {f['infra']} | {r} | {prio:.3f} |"
        )
    L += [
        "",
        "Priorité = risque prédit × (1 − protection) ; protection = score de mutation, à défaut couverture, "
        "à défaut 0.",
        f"Risque prédit pour un changement type : {CHANGE['added']} lignes ajoutées, {CHANGE['deleted']} supprimées, "
        f"fichier seul dans son commit, {CHANGE['hour']} h.",
    ]
    autres = {m: f for m, f in fails.items() if m not in modules}
    if autres:
        L.append(f"Échecs non rattachés à un module suivi : {dict(autres)}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
````
