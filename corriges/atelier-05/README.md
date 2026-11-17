# Atelier 5 — Détecter les anomalies dans les logs et les exécutions de tests : corrigé

**Durée : 2 h** (A : 50 min, B : 50 min, C : 20 min) · Module 2

Objectif : repérer automatiquement, sans exemples étiquetés, ce qu'un humain ne voit pas dans des
milliers de lignes — pics de latence, rafales d'erreurs, tests instables, tests qui ralentissent,
familles d'échecs — et savoir régler puis critiquer le détecteur.

Tous les chiffres ci-dessous viennent d'une exécution réelle (Python 3.13, `LLM_PROVIDER=offline`).
Les données simulées sont déterministes (graine fixe) : les stagiaires obtiennent les mêmes valeurs.
Les mesures de l'étape A.4 (application réelle sous charge) varient d'une exécution à l'autre.

Fichier de solution : `formateur/solutions/atelier-05/ai_tools/eval_fenetres.py` (balayage de
plusieurs réglages en une commande, à copier dans `ai_tools/` du dépôt).

## Le résultat à atteindre

| Mesure | Valeur obtenue |
|---|---|
| Données générées | 5 000 requêtes, 60 runs JUnit, 1 284 lignes d'historique Git |
| Anomalies réelles dans les logs (`_truth`) | 69 : 40 `burst_500`, 19 `latency_spike`, 10 `scan` |
| Réglage par défaut, niveau fenêtre | 2 fenêtres sur 84 signalées, rappel 8 % (2/24), précision 100 % |
| Réglage par défaut, niveau requête | 69 requêtes atypiques, rappel 100 %, précision 100 % |
| `--window 5 --contamination 0.10`, niveau fenêtre | 50 fenêtres sur 499 signalées, rappel 100 % (33/33), précision 66 % |
| `--z-threshold 3 --min-latency-ms 0`, niveau requête | 76 requêtes atypiques, rappel 100 %, précision 91 % (7 faux positifs) |
| Logs réels, phase normale puis phase ralentie | 182 requêtes atypiques, toutes sur `/cart/quote` : les 182 de la phase ralentie, aucune de la phase normale |
| `--fail-on-anomaly` | code 1 sur ce journal (12 fenêtres sur 25 avec p95 ≥ 500 ms), code 0 sur la phase normale seule |
| Test instable | `tests.e2e.test_parcours_achat::test_parcours_achat_avec_coupon` (92 % de réussite, score 0,8) |
| Test qui ralentit | `tests.api.test_api::test_recherche_produits` (0,127 s au run 1, 0,548 s au run 60) |
| Familles d'échecs | 4 : 1 test fragile, 1 bug applicatif, 2 pannes d'infrastructure |
| `ml-insights.yml` | `actionlint` : aucune erreur |

## Préparation

```bash
python scripts/simulate_history.py
```

```text
Données générées dans …/data/ : junit-history/ (60 runs), app-logs.jsonl, git-history.csv
```

Vérification rapide : `ls data/junit-history | wc -l` donne 60, `wc -l data/app-logs.jsonl` donne 5000.
Le dossier `data/` est ignoré par Git : il se régénère à l'identique.

## Partie A — Logs applicatifs

### A.1 Que chercher « à la main » ?

```json
{"ts": 1790000000.892, "method": "GET", "path": "/products/{product_id}", "status": 200, "latency_ms": 7.25, "_truth": null}
{"ts": 1790000001.032, "method": "POST", "path": "/cart/quote", "status": 200, "latency_ms": 14.5, "_truth": null}
{"ts": 1790000002.089, "method": "POST", "path": "/orders", "status": 201, "latency_ms": 34.13, "_truth": null}
```

Réponse attendue : les statuts 5xx (surtout groupés dans le temps), les latences très supérieures à
l'habitude **de la route** (35 ms est normal sur `/orders`, pas sur `/health`), les chemins qui
n'existent pas dans l'application (`/.env`, `/wp-admin` : un scan), un volume de requêtes inhabituel.
Faire remarquer qu'à la main on ne tient pas 5 000 lignes, et que 98,6 % sont normales
(4 931 lignes sans étiquette, 69 anomalies).

La colonne `_truth` est la vérité terrain : elle n'existe que parce que les données sont simulées.
Le détecteur ne la lit pas pour décider ; elle sert seulement à l'évaluation finale.

### A.2 Lancer la détection

```bash
python ai_tools/log_anomalies.py data/app-logs.jsonl
```

```text
# Rapport d'anomalies

- Fichier : `data/app-logs.jsonl` — 5000 requêtes, 84 fenêtres de 30s
- Fenêtres anormales (IsolationForest) : **2**
- Requêtes atypiques (z-score robuste > 6 et latence >= 100 ms, ou chemin inconnu) : **69**
- Fenêtres graves (critère absolu de --fail-on-anomaly) : **2 fenêtre(s) sur 84 avec 5xx >= 5% ou p95 >= 500 ms**

## Évaluation (données simulées)

- Niveau fenêtre (IsolationForest) — rappel : 2/24 fenêtres anormales signalées (8%) ; précision : 2/2 signalements justes (100%)
- Niveau requête (z-score / chemin inconnu) — rappel : 69/69 requêtes anormales signalées (100%) ; précision : 69/69 signalements justes (100%)
```

Extrait de `reports/anomalies.md` :

```text
| Début (ts) | Score | Req. | 5xx | 4xx | p50 ms | p95 ms | max ms | chemins inconnus |
| 1790001510 | -0.099 | 61 | 56% | 0% | 783 | 1041 | 1172 | 0 |
| 1790001480 | -0.009 | 70 | 9% | 1% | 11 | 814 | 1615 | 0 |
```

Les deux techniques ne répondent pas à la même question, et le rapport les évalue séparément :

- **IsolationForest sur des fenêtres** : « cette demi-minute ressemble-t-elle aux autres ? ». Chaque
  fenêtre est décrite par 7 nombres (volume, taux de 5xx, taux de 4xx, p50, p95, max, nombre de
  chemins inconnus). L'algorithme isole les points faciles à séparer par des coupes aléatoires.
  Ici il trouve les deux fenêtres de la rafale de 500 sur `/orders` (56 % de 5xx, p50 à 783 ms).
  Le paramètre `contamination` n'est pas un seuil de gravité : c'est la **part de fenêtres que l'on
  décide de signaler**. Avec 0,02 et 84 fenêtres, on en obtient 2, quoi qu'il arrive.
  Évaluation au niveau fenêtre : une fenêtre est réellement anormale si elle contient au moins une
  requête étiquetée. Il y en a 24 ; le réglage par défaut en signale 2.
- **z-score robuste par route** : « cette requête est-elle lente pour sa route ? ». On compare à la
  médiane de la route, et l'écart est mesuré en MAD (médiane des écarts absolus) plutôt qu'en
  écart-type, parce que moyenne et écart-type sont eux-mêmes déformés par les valeurs extrêmes que
  l'on cherche. Un plancher absolu (`--min-latency-ms`, 100 ms par défaut) évite de signaler une
  requête de quelques millisecondes. S'y ajoute une règle sans statistique : tout chemin hors de
  `KNOWN_PATHS` est signalé.
- La ligne « **Fenêtres graves** » est d'une autre nature : c'est un critère absolu (5xx ≥ 5 % ou
  p95 ≥ 500 ms par fenêtre), celui de la barrière `--fail-on-anomaly` (Partie C).

### A.3 Expérimenter : tableau rempli

Une commande par ligne, par exemple `python ai_tools/log_anomalies.py data/app-logs.jsonl --window 5`.

| Paramètre | Fenêtres signalées | Rappel (fenêtres) | Précision (fenêtres) | Rappel (requêtes) | Précision (requêtes) |
|---|---|---|---|---|---|
| défaut (`--window 30 --contamination 0.02`) | 2 sur 84 | 8 % (2/24) | 100 % (2/2) | 100 % (69/69) | 100 % (69/69) |
| `--contamination 0.10` | 9 sur 84 | 29 % (7/24) | 78 % (7/9) | 100 % (69/69) | 100 % (69/69) |
| `--window 5` | 10 sur 499 | 30 % (10/33) | 100 % (10/10) | 100 % (69/69) | 100 % (69/69) |
| `--window 5 --contamination 0.10` | 50 sur 499 | 100 % (33/33) | 66 % (33/50) | 100 % (69/69) | 100 % (69/69) |
| `--z-threshold 3 --min-latency-ms 0` | 2 sur 84 | 8 % (2/24) | 100 % (2/2) | 100 % (69/69) | 91 % (69/76) |

**Quels paramètres agissent sur quelles colonnes ?** `--window` et `--contamination` ne règlent que
l'IsolationForest : seules les colonnes « fenêtres » bougent. `--z-threshold` et `--min-latency-ms`
ne règlent que la règle par requête : seules les colonnes « requêtes » bougent.

**Que règle vraiment `--contamination` ?** Un quota, pas une sensibilité à la gravité. Faire calculer :
84 × 0,02 ≈ 2, 84 × 0,10 ≈ 9, 499 × 0,02 ≈ 10, 499 × 0,10 ≈ 50. Ce sont exactement les nombres de
fenêtres signalées.

Lecture du tableau, à faire trouver aux stagiaires :

1. **Niveau fenêtre, le compromis est net.** Le réglage par défaut ne voit que l'incident massif
   (2 fenêtres, toutes deux justes) et ignore les pics isolés et les scans : rappel de 8 %,
   précision de 100 %. Monter la contamination ou réduire la fenêtre fait remonter davantage de
   fenêtres réellement anormales, au prix de fausses alertes : avec 5 s et 0,10, toutes les fenêtres
   anormales sont trouvées mais une alerte sur trois est fausse (17 fausses alertes en 42 minutes de
   trafic).
2. **Une fenêtre courte localise mieux** (la rafale occupe 5 fenêtres de 5 s au lieu de 2 de 30 s)
   mais contient peu de requêtes : ses percentiles sont bruités.
3. **Niveau requête, baisser le seuil z à 3 sans plancher fait apparaître 7 faux positifs** sans
   gagner un seul vrai : des requêtes ordinaires, à peine plus lentes que la médiane (`/cart/quote`
   à 28 ms, `/health` à 17,8 ms, `/products` à 16,8 ms). Avec le plancher de 100 ms, ces 7 faux
   positifs disparaissent même au seuil 3 (69 signalements, tous vrais) : c'est son rôle.
4. **Les anomalies simulées sont trop faciles.** En balayant le seuil sans plancher
   (`eval_fenetres.py --z … --min-latency-ms 0`), on obtient exactement 69 signalements, tous vrais,
   pour tout seuil de 4 à 100 ; à 2,5 la précision tombe à 71 % (97 signalements), à 2 elle tombe à
   46 % (150 signalements) ; à 500 c'est le rappel qui tombe à 42 % (29/69). Sur des logs réels, la
   zone confortable est bien plus étroite.

Le script de solution affiche tous les couples (fenêtre, contamination) d'un coup, ce qui évite
cinq lancements en démonstration :

```bash
python ai_tools/eval_fenetres.py data/app-logs.jsonl
```

| Fenêtre | Contamination | Fenêtres | Signalées | Réellement anormales | Rappel | Précision | Rafale 500 vue |
|---|---|---|---|---|---|---|---|
| 30 s | 0.02 | 84 | 2 | 24 | 8 % | 100 % | 2/2 |
| 30 s | 0.10 | 84 | 9 | 24 | 29 % | 78 % | 2/2 |
| 5 s | 0.02 | 499 | 10 | 33 | 30 % | 100 % | 5/5 |
| 5 s | 0.10 | 499 | 50 | 33 | 100 % | 66 % | 5/5 |
| 60 s | 0.02 | 42 | 1 | 21 | 5 % | 100 % | 1/1 |

Avec `--min-anomalies 5` (on ne compte comme « réellement anormales » que les fenêtres d'incident
massif, c'est-à-dire la rafale de 500), le rappel est de 100 % dans tous les réglages et la précision
vaut 100 % (30 s, 0,02), 22 % (30 s, 0,10), 50 % (5 s, 0,02) et 10 % (5 s, 0,10). Autrement dit :
tous les réglages voient la panne ; ce qui les distingue, c'est le bruit qu'ils ajoutent autour.

### Conclusion : quel compromis pour une alerte qui réveille quelqu'un la nuit ?

On privilégie la **précision**. Une astreinte réveillée à tort plusieurs fois cesse de croire
l'alerte, et la vraie panne passera inaperçue. Concrètement :

- pour l'alerte de nuit : fenêtres de 30 s, contamination basse (0,02), seuil z élevé (6). Dans nos
  mesures, ce réglage ne signale que la rafale de 500, sans fausse alerte. Les incidents massifs sont
  ceux qui justifient un réveil ;
- pour le reste (pics isolés, scans) : un réglage sensible (fenêtres de 5 s, contamination 0,10),
  mais dirigé vers un **rapport du matin ou un ticket**, pas vers le téléphone d'astreinte ;
- et de toute façon, une alerte de nuit doit reposer sur un seuil absolu lié à un engagement de
  service (taux de 5xx, p95), pas seulement sur « différent des autres fenêtres » : la contamination
  fixe un quota d'alertes, pas une gravité. C'est le choix fait pour `--fail-on-anomaly`.

### A.4 Sur vos logs réels

Commandes de l'énoncé (ici sur le port 18091 attribué pour les essais ; les stagiaires gardent 8000).
La procédure a été exécutée telle quelle, dans une copie fraîche du dépôt :

```bash
rm -f logs/app.jsonl
MINISHOP_LOG_FILE=logs/app.jsonl uvicorn minishop.api:app &                     # phase normale
locust -f tests/perf/locustfile.py --host http://localhost:8000 --headless -u 20 -r 5 -t 60s
kill $!                                                                          # arrête l'application
MINISHOP_LOG_FILE=logs/app.jsonl MINISHOP_BUG=slow uvicorn minishop.api:app &   # phase ralentie
locust -f tests/perf/locustfile.py --host http://localhost:8000 --headless -u 20 -r 5 -t 60s
kill $!
python ai_tools/log_anomalies.py logs/app.jsonl --window 5
```

Les deux tests de charge, vus par Locust : le premier passe, le second échoue, c'est attendu.

```text
== SLO == p95=7 ms (max 300) | erreurs=0.00% (max 1%)
== SLO == p95=660 ms (max 300) | erreurs=0.00% (max 1%)
SLO NON RESPECTÉ -> échec du job
```

Résultat de la détection :

```text
- Fichier : `logs/app.jsonl` — 1815 requêtes, 25 fenêtres de 5s
- Fenêtres anormales (IsolationForest) : **1**
- Requêtes atypiques (z-score robuste > 6 et latence >= 100 ms, ou chemin inconnu) : **182**
- Fenêtres graves (critère absolu de --fail-on-anomaly) : **12 fenêtre(s) sur 25 avec 5xx >= 5% ou p95 >= 500 ms**

| ts | méthode | chemin | statut | latence ms | z |
| 1794924825.966374 | POST | `/cart/quote` | 200 | 462.25 | 361.3 |
| 1794924827.0778434 | POST | `/cart/quote` | 200 | 492.05 | 384.7 |
| 1794924827.139696 | POST | `/cart/quote` | 200 | 649.89 | 508.5 |
```

**Le ralentissement est-il détecté ? Oui, par la règle par requête, et uniquement sur `/cart/quote`.**
Les 182 requêtes atypiques sont exactement les 182 appels à `/cart/quote` de la phase ralentie
(médiane 528 ms) ; aucune requête de la phase normale n'est signalée, et aucune autre route : leurs
médianes restent à 0,6 ms (`/products`, `/products/{product_id}`) et 1,0 ms (`/orders`) pendant la
phase ralentie.

**Par laquelle des deux techniques ?** Pas par l'IsolationForest : avec `contamination=0.02` et
25 fenêtres, il n'en signale qu'une, et ce n'est pas une fenêtre du ralentissement mais la dernière
du fichier, incomplète (6 requêtes). Avec `--contamination 0.10` il en signale 3, alors que 12
fenêtres sur 25 sont dégradées. Quand la moitié des fenêtres est anormale, « rare » ne veut plus
dire « anormal » : le quota ne suit pas. La ligne « Fenêtres graves », elle, compte bien les 12.

**Pourquoi la phase normale est-elle nécessaire ?** Mesuré en analysant chaque phase à part (on note
`wc -l logs/app.jsonl` entre les deux phases, ici 952, puis `head -n 952` et `tail -n +953` donnent
les deux moitiés) :

| Journal analysé (`--window 5`) | Requêtes | Fenêtres signalées | Requêtes atypiques | Fenêtres graves | `--fail-on-anomaly` |
|---|---|---|---|---|---|
| Phase normale seule | 952 | 1 sur 12 | 0 | 0 | code 0 |
| Phase ralentie seule | 863 | 1 sur 13 | **0** | 12 | code 1 |
| Les deux phases (énoncé) | 1 815 | 1 sur 25 | 182 | 12 | code 1 |

Sur la phase ralentie seule, la règle par requête ne signale **rien** : toutes les requêtes
`/cart/quote` sont lentes, la médiane de la route vaut 528 ms, et par rapport à elle aucune requête
n'est atypique. Un détecteur non supervisé trouve ce qui est rare, pas ce qui est mauvais : une
dégradation permanente devient la norme. Il lui faut une référence. Seul le critère absolu (fenêtres
graves, ou le seuil de Locust) voit le défaut sans référence.

Deux autres constats à tirer de ces essais :

- **Le plancher de 100 ms est indispensable en local.** Sur la phase normale seule, avec
  `--min-latency-ms 0`, l'outil signale 78 « requêtes atypiques » de quelques millisecondes : la
  médiane d'une route est d'environ 0,6 ms et la MAD est minuscule, si bien qu'une requête à 3 ms
  obtient un z supérieur à 20. Un écart statistiquement énorme peut être sans importance en pratique.
- **Avec `--window 30`, l'outil répond « Pas assez de données pour un modèle (min. 10 fenêtres) »**
  sur une seule phase de 60 s. C'est pour cela que l'énoncé impose `--window 5`.

Note pour le formateur : dans une version antérieure de l'application, le défaut `slow` bloquait
tout le serveur et ralentissait toutes les routes. Il est maintenant limité à `/cart*`
(`await asyncio.sleep` dans le middleware). Si un stagiaire observe des routes `/products` lentes,
son dépôt n'est pas à jour.

## Partie B — Historique des exécutions de tests

### B.1 Lancer l'analyse

```bash
python ai_tools/test_history.py data/junit-history
```

```text
60 exécutions analysées, 11 tests.

## Tests instables (flaky)
| `tests.e2e.test_parcours_achat::test_parcours_achat_avec_coupon` | 92% | 4 | 0.8 |

## Tests qui ralentissent
| `tests.api.test_api::test_recherche_produits` | 0.34s | +0.0071 | 1.7 |

### Famille 1 — 5 échecs, 5 runs
- Exemple : `TimeoutError: Locator.click: Timeout 5000ms exceeded waiting for get_by_test_id('order-btn')`
- Tests touchés : test_parcours_achat_avec_coupon
- Runs : run-026.xml … run-060.xml

### Famille 2 — 4 échecs, 1 runs
- Exemple : `httpx.ConnectError: [Errno 111] Connection refused`
- Tests touchés : test_commande_cycle_complet, test_contrat_openapi, test_quote_ok, test_recherche_produits
- Runs : run-037.xml … run-037.xml

### Famille 3 — 4 échecs, 4 runs
- Exemple : `AssertionError: assert Decimal('23.27') == Decimal('23.28')`
- Tests touchés : test_remise_volume_a_partir_de_10
- Runs : run-048.xml … run-051.xml

### Famille 4 — 2 échecs, 2 runs
- Exemple : `OperationalError: could not connect to server: Connection refused (localhost:5432)`
- Tests touchés : test_reservation_stock
- Runs : run-023.xml … run-024.xml
```

- **Test instable** : `tests.e2e.test_parcours_achat::test_parcours_achat_avec_coupon`.
- **Test qui ralentit** : `tests.api.test_api::test_recherche_produits`.

### B.2 Les algorithmes, section par section

**Tests instables** (`per_test_stats`). Pour chaque test, on met ses résultats dans l'ordre des runs
et on compte les **échecs isolés** : un échec dont le run précédent et le run suivant sont des succès.
Score = échecs isolés / nombre total d'échecs, calculé seulement à partir de 3 échecs ; un test est
déclaré instable à partir de 0,6. L'idée : un vrai bug échoue plusieurs fois de suite jusqu'à sa
correction, un test instable échoue une fois puis repasse sans que rien n'ait changé.

Vérification sur les données : le test e2e échoue aux runs 26, 41, 51, 53 et 60, soit 5 échecs sur
60 (92 % de réussite). Quatre sont isolés ; le cinquième est au dernier run, qui n'a pas de
successeur et n'est donc pas compté. Score : 4/5 = 0,8. À l'inverse, `test_remise_volume_a_partir_de_10`
a 4 échecs consécutifs (runs 48 à 51) : aucun échec isolé, score 0. Les quatre tests d'API ont
chacun un seul échec (run 37) : moins de 3 échecs, score 0.

**Tests qui ralentissent**. On ajuste une droite (`np.polyfit` de degré 1) sur la durée en fonction du
numéro de run ; la pente est le temps gagné ou perdu à chaque run. Un test est signalé si sa pente
dépasse 1 % de sa durée moyenne par run. `test_recherche_produits` passe de 0,127 s (run 1) à
0,548 s (run 60) : pente de +0,0071 s par run, pour une moyenne de 0,34 s, soit environ 2 % par run.
Le seuil est relatif, et c'est voulu : le test e2e instable a une pente plus forte en valeur absolue
(+0,0116 s par run, à cause de ses échecs à 5,2 s) mais elle ne représente que 0,4 % de sa durée
moyenne (2,76 s), il n'est donc pas signalé. La colonne « Dernier run (z) » compare le dernier run
à la moyenne des précédents : elle signale un saut brutal, la pente signale une dérive lente.

**Familles d'échecs** (`cluster_failures`). Chaque message d'échec est transformé en vecteur TF-IDF
(mots d'au moins 3 lettres ; un mot pèse d'autant plus qu'il est fréquent dans le message et rare
dans l'ensemble). Un clustering hiérarchique ascendant regroupe ensuite les messages proches, sans
fixer à l'avance le nombre de groupes : on fusionne tant que la distance reste sous 1,2. Résultat :
15 échecs, 4 familles. Faire remarquer que « Connection refused » apparaît dans deux familles
(réseau et base de données) et que l'algorithme les sépare tout de même, grâce aux autres mots
(`httpx`, `ConnectError` d'un côté, `OperationalError`, `server`, `localhost` de l'autre).

### B.3 Classement des familles et action

| Famille | Indices | Classement | Action |
|---|---|---|---|
| 1 — `TimeoutError: Locator.click … 'order-btn'` | 5 échecs sur 5 runs dispersés (26, 41, 51, 53, 60), toujours le même test e2e, qui repasse au run suivant | **Test fragile** (instable) | Mettre en quarantaine (marqueur dédié, hors du chemin bloquant) avec un ticket et une date, puis corriger la cause : attente explicite de l'état du bouton plutôt qu'un clic immédiat. La relance automatique n'est qu'un pansement provisoire |
| 2 — `httpx.ConnectError: Connection refused` | 4 tests d'API différents, tous au run 37 et seulement là | **Infrastructure** (l'application n'était pas joignable) | Relancer automatiquement le job ; attendre `/health` avant de lancer les tests. Ne pas toucher aux tests |
| 3 — `AssertionError: Decimal('23.27') == Decimal('23.28')` | 1 test unitaire, 4 runs consécutifs (48 à 51), message identique, disparaît au run 52 | **Bug applicatif** (régression d'arrondi sur la remise volume) | Corriger le code, ou annuler le changement fautif. Jamais de relance ni de quarantaine : le test fait son travail |
| 4 — `OperationalError … localhost:5432` | 1 test d'intégration, runs 23 et 24 | **Infrastructure** (base de données indisponible) | Relancer automatiquement ; ajouter un contrôle de disponibilité du service de base de données avant les tests. Si cela se répète, c'est un sujet de plateforme, pas de test |

Règle de lecture à faire formuler par les stagiaires :

- plusieurs tests, un seul run, un message d'environnement : infrastructure ;
- un seul test, des runs consécutifs, un message d'assertion métier : bug applicatif ;
- un seul test, des runs dispersés, un message de délai : test fragile.

Le run 51 cumule un échec de la famille 1 et un de la famille 3 : un run rouge peut avoir deux
causes indépendantes, d'où l'intérêt de regrouper par message plutôt que par run.

### B.4 Option `--explain`

```bash
python ai_tools/test_history.py data/junit-history --explain
```

Avec un LLM configuré, le script envoie pour chaque famille au plus 8 messages d'échec (nom du test
et message) avec la consigne : répondre en français, en 3 lignes au plus, en donnant la cause
probable, le classement (bug applicatif, test fragile ou infrastructure) et l'action à mener. La
réponse est ajoutée sous la famille, sur une ligne « **Analyse IA** ». En cas d'erreur du
fournisseur, la ligne devient « Analyse IA indisponible : … » et le rapport est tout de même produit.

Ce qui est vérifié : en mode `offline`, l'outil le dit (« Option --explain ignorée : aucun LLM
configuré (LLM_PROVIDER=offline)… », sur la sortie d'erreur et en tête de la section des familles) et
produit le rapport sans analyse IA. Ce qui ne l'est pas : le contenu des réponses d'un LLM (voir
« Non vérifié »).

Ce qu'il faut faire discuter : le LLM ne reçoit que les messages. Il ne voit ni la dispersion des
runs ni le nombre de tests touchés, qui sont justement les indices décisifs du classement ci-dessus.
On peut s'attendre à ce qu'il classe correctement les messages explicites (5432 : base de données)
et à ce qu'il hésite entre « test fragile » et « application lente » pour le délai dépassé. Son
explication est une aide à la rédaction du ticket, pas une décision.

## Partie C — Quality gate

La solution existe : `formateur/solutions/workflows/ml-insights.yml`, job `history-and-anomalies`.
`actionlint` ne signale aucune erreur sur ce fichier.

Ce que fait le job :

1. il s'exécute sur `schedule` (`cron: "0 6 * * 1-5"` : du lundi au vendredi à 6 h UTC), et aussi sur
   `workflow_dispatch` pour le lancer à la main pendant l'atelier. La condition
   `if: github.event_name != 'pull_request'` l'écarte des pull requests, qui déclenchent l'autre job
   du même fichier ;
2. il régénère l'historique simulé (dans un vrai projet : les rapports JUnit des derniers runs,
   récupérés par l'API ou les artefacts) ;
3. il lance `test_history.py` avec `--report reports/test-insights.md` ;
4. il démarre l'application avec `MINISHOP_LOG_FILE`, attend `/health`, envoie 60 s de charge Locust,
   puis lance `log_anomalies.py --window 5` sur les logs obtenus (le commentaire du workflow rappelle
   la contrainte des 10 fenêtres) ;
5. il ajoute le rapport au résumé du run : `cat reports/test-insights.md >> "$GITHUB_STEP_SUMMARY"` ;
6. il publie `reports/` en artefact.

Version minimale attendue d'un stagiaire (validée par `actionlint`) :

```yaml
name: Analyse quotidienne des tests

on:
  schedule:
    - cron: "0 6 * * 1-5"   # du lundi au vendredi, 6 h UTC
  workflow_dispatch:

permissions:
  contents: read

jobs:
  history:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12", cache: pip }
      - run: pip install -r requirements-dev.txt
      - run: python scripts/simulate_history.py     # en vrai : les JUnit des derniers runs
      - run: python ai_tools/test_history.py data/junit-history --report reports/test-insights.md
      - run: cat reports/test-insights.md >> "$GITHUB_STEP_SUMMARY"
      - uses: actions/upload-artifact@v4
        with: { name: test-insights, path: reports/test-insights.md }
```

Points à relever avec le groupe :

- `schedule` ne se déclenche que sur la branche par défaut, en heure UTC, et GitHub suspend les
  workflows planifiés d'un dépôt sans activité pendant 60 jours.
- Ce job informe, il ne bloque pas : `test_history.py` renvoie 0 même s'il trouve un test instable.

**Bonus `--fail-on-anomaly`.** Après un test de charge :

```bash
python ai_tools/log_anomalies.py logs/app.jsonl --window 5 --fail-on-anomaly
```

La commande renvoie le code 1 si au moins une fenêtre dépasse un seuil absolu : taux de 5xx ≥ 5 %
(`--gate-5xx-rate`) ou p95 ≥ 500 ms (`--gate-p95-ms`). Elle affiche alors, par exemple,
« ÉCHEC de la barrière : 12 fenêtre(s) sur 25 avec 5xx >= 5% ou p95 >= 500 ms ». Codes mesurés :

| Journal | Code retour |
|---|---|
| Charge normale (p95 Locust de 7 ms) | 0 |
| Charge avec `MINISHOP_BUG=slow`, avec ou sans phase de référence | 1 |
| Logs simulés `data/app-logs.jsonl` (rafale de 500) | 1 |

Réponse à la question de l'énoncé (« pourquoi ne pas faire échouer le job sur les fenêtres
atypiques ? ») : parce que l'IsolationForest en signale toujours, par construction. Sur le journal
d'une charge parfaitement normale, il signale 1 fenêtre sur 12 ; une barrière fondée sur ce
signalement échouerait à chaque exécution. Une barrière doit reposer sur un critère de gravité, que
l'on peut justifier et régler ; la détection d'anomalies sert au diagnostic et au rapport.

## Critères de réussite

| Critère | Démonstration |
|---|---|
| Tableau rappel/précision rempli et compromis argumenté | Partie A.3 et conclusion |
| Les 4 familles d'échecs identifiées et classées | Partie B.3 |
| Le test instable et le test qui ralentit sont identifiés | Partie B.1 |
| Analyse quotidienne ajoutée à la CI | Partie C : workflow validé par `actionlint` ; exécution sur GitHub non vérifiée |

## Points d'animation

**Erreurs fréquentes**

- Lancer les outils depuis un autre dossier que la racine du dépôt : `reports/`, `data/` et `logs/`
  sont créés dans le dossier courant.
- Croire que la contamination est un seuil de sensibilité à la gravité : renvoyer au calcul du
  quota (A.3).
- Chercher l'effet de `--window` dans les colonnes « requêtes », ou celui de `--z-threshold` dans les
  colonnes « fenêtres ».
- Étape A.4 : oublier un `kill $!` : la seconde application ne démarre pas (port occupé) et les deux
  phases sont normales, ou bien une application reste en service et bloque le port pour les ateliers
  suivants. `$!` désigne la dernière commande lancée en arrière-plan : ne rien lancer d'autre avec
  `&` entre-temps.
- Étape A.4 : oublier le `rm -f logs/app.jsonl` et analyser plusieurs essais cumulés (le fichier est
  ouvert en ajout). Laisser `MINISHOP_BUG=slow` exporté dans le terminal fausse aussi les ateliers
  suivants (ici la variable n'est posée que pour une commande).
- Étape A.4 : s'inquiéter de l'échec du second Locust. Il est attendu, l'énoncé le dit.
- Étape A.4 : conclure que l'IsolationForest « ne marche pas ». La bonne conclusion est qu'il répond
  à une autre question (ce qui est rare dans le lot) et qu'un défaut qui touche la moitié des
  fenêtres n'est plus rare.
- Partie B : classer la famille 1 en bug applicatif parce que le message parle d'un bouton. L'indice
  décisif est la répartition des échecs dans le temps, pas le message.

**Questions de discussion**

- *Pourquoi la médiane et la MAD plutôt que la moyenne et l'écart-type ?* Parce que les valeurs
  extrêmes que l'on cherche tirent la moyenne et gonflent l'écart-type, ce qui les cache.
- *Faut-il relancer automatiquement les tests qui échouent ?* Oui pour l'infrastructure, avec une
  limite ; provisoirement pour un test instable mis en quarantaine ; jamais comme réponse durable :
  une relance qui passe masque aussi les vrais bugs intermittents (accès concurrents).
- *Que vaut un taux de réussite de 92 % ?* Avec 10 tests de ce niveau dans une suite, la suite
  complète ne passe qu'environ 4 fois sur 10 (0,92 puissance 10 ≈ 0,43) sans aucun bug.
- *Les données simulées sont-elles représentatives ?* Non : les anomalies de latence y ont un z-score
  compris entre 203 et 1 353, alors que la requête normale la plus atypique plafonne à 3,8. Tout seuil
  entre les deux donne un résultat parfait. L'étape A.4 montre ce qui se passe sur des données réelles.
- *Le test instable est tiré avec 15 % de risque d'échec par run ; on observe 5 échecs sur 60, soit 8 %.*
  C'est le hasard du tirage sur 60 runs : bon exemple d'incertitude sur un petit échantillon.

**Durée à surveiller**

- Partie A : l'étape A.4 prend à elle seule 10 à 15 minutes (deux charges de 60 s, les démarrages,
  puis l'analyse). L'essai « phase ralentie seule » se fait sans relancer de charge, en découpant le
  journal ; le faire en démonstration formateur si le groupe est en retard.
- Partie B : ne pas laisser lire tout le code ; cibler `per_test_stats` et `cluster_failures`.
- Partie C : 20 minutes suffisent si le pipeline de l'Atelier 2 existe ; l'exécution planifiée ne
  peut pas être observée en séance, utiliser `workflow_dispatch`.

## Non vérifié

- **Option `--explain` avec un vrai LLM** : aucun LLM n'était disponible. Le comportement décrit vient
  de la lecture du code (`explain()` dans `ai_tools/test_history.py`) ; le contenu et la qualité des
  réponses ne sont pas vérifiés. Seul le mode `offline` a été exécuté.
- **Exécution des workflows sur GitHub Actions** (déclenchement planifié, affichage du résumé,
  artefact) : seuls `actionlint` et l'exécution locale des commandes du job ont été faits.
- **Variante PowerShell** de l'étape A.4 : non exécutée (essais sous Linux uniquement).
- Les mesures de l'étape A.4 dépendent de la machine : les ordres de grandeur sont stables d'un essai
  à l'autre (deux essais : 206 puis 182 requêtes atypiques, toutes sur `/cart/quote` ; 12 fenêtres
  graves sur 25 dans les deux cas), les valeurs exactes non.

---

## Fichiers de cet atelier

Par rapport à la branche `python/atelier-04` :

| | Fichier |
|---|---|
| ajouté | `ai_tools/eval_fenetres.py` |

### `ai_tools/eval_fenetres.py`

````python
"""Atelier 5 — balayage des réglages de log_anomalies.py en une seule commande.

`log_anomalies.py` évalue un réglage à la fois (niveau fenêtre et niveau requête). Ce script reprend
les mêmes définitions et affiche d'un coup plusieurs couples (fenêtre, contamination), pour remplir
le tableau de l'étape A.3 et discuter le compromis. Une fenêtre est « réellement anormale » si elle
contient au moins une requête étiquetée dans `_truth` ; `--min-anomalies` permet de ne compter que
les incidents massifs.

Usage (depuis la racine du dépôt, après `python scripts/simulate_history.py`) :
    python ai_tools/eval_fenetres.py data/app-logs.jsonl
    python ai_tools/eval_fenetres.py data/app-logs.jsonl --min-anomalies 5
    python ai_tools/eval_fenetres.py data/app-logs.jsonl --z 3 --min-latency-ms 0
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.ensemble import IsolationForest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ai_tools.log_anomalies import load, per_request_outliers, windows  # noqa: E402

REGLAGES = [(30, 0.02), (30, 0.10), (5, 0.02), (5, 0.10), (60, 0.02)]


def evaluer(logs: list[dict], window: int, contamination: float, min_anomalies: int) -> dict:
    keys, X = windows(logs, window)
    pred = IsolationForest(contamination=contamination, random_state=0).fit(X).predict(X)
    signalees = {keys[i] for i in np.where(pred == -1)[0]}
    par_fenetre = Counter(int(e["ts"] // window) for e in logs if e.get("_truth"))
    vraies = {k for k, n in par_fenetre.items() if n >= min_anomalies}
    burst = {int(e["ts"] // window) for e in logs if e.get("_truth") == "burst_500"}
    ok = signalees & vraies
    return {
        "fenetres": len(keys),
        "signalees": len(signalees),
        "vraies": len(vraies),
        "rappel": len(ok) / max(len(vraies), 1),
        "precision": len(ok) / max(len(signalees), 1),
        "burst": f"{len(burst & signalees)}/{len(burst)}",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("logfile", type=Path)
    ap.add_argument("--min-anomalies", type=int, default=1, help="nb min. de requêtes anormales par fenêtre")
    ap.add_argument("--z", type=float, default=6.0, help="seuil du z-score robuste (règle par requête)")
    ap.add_argument("--min-latency-ms", type=float, default=100.0, help="plancher de la règle par requête")
    args = ap.parse_args()
    logs = load(args.logfile)

    print("IsolationForest, niveau fenêtre")
    print(
        "| Fenêtre | Contamination | Fenêtres | Signalées | Réellement anormales | Rappel | Précision | Rafale 500 vue |"
    )
    print("|---|---|---|---|---|---|---|---|")
    for w, c in REGLAGES:
        r = evaluer(logs, w, c, args.min_anomalies)
        print(
            f"| {w} s | {c:.2f} | {r['fenetres']} | {r['signalees']} | {r['vraies']} | "
            f"{r['rappel']:.0%} | {r['precision']:.0%} | {r['burst']} |"
        )

    out = per_request_outliers(logs, threshold=args.z, min_latency_ms=args.min_latency_ms)
    vrais = sum(1 for o in out if o.get("_truth"))
    total = sum(1 for e in logs if e.get("_truth"))
    print(
        f"\nRègle par requête, seuil z = {args.z:g}, plancher {args.min_latency_ms:g} ms : "
        f"{len(out)} signalements, dont {vrais} vrais"
    )
    print(f"  rappel {vrais}/{total} = {vrais / max(total, 1):.0%} ; précision {vrais / max(len(out), 1):.0%}")
    faux = [o for o in out if not o.get("_truth")]
    for o in faux[:10]:
        print(f"  faux positif : {o['path']} {o['latency_ms']} ms (z = {o['robust_z']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
````
