# Ateliers 5 à 12 — ce qui change en PHP

Les Ateliers 8, 9 et 11 ont leur énoncé décliné dans ce dossier. Pour les autres, l'énoncé de référence reste
celui du dossier `ateliers/` à la racine ; cette page indique ce qui s'utilise tel quel.

Pour tous ces ateliers, l'application testée est celle de ce dossier, lancée dans Docker :
```bash
cd declinaisons/php
docker compose up -d --build
curl -sf http://localhost:8000/health
```
Elle répond sur http://localhost:8000 comme l'application Python, avec le même contrat (routes, métriques,
logs) : les outils Python fournis (`ai_tools/`, `scripts/`, `tests/perf`, `tests/visual`) s'utilisent tels
quels, depuis la racine du dépôt. N'ayez pas les deux applications lancées en même temps (même port).
Les tests PHP du projet `boite-noire/` lisent l'adresse dans `MINISHOP_URL` (défaut : `http://localhost:8000`).

## Atelier 5 — Anomalies dans les logs et les exécutions de tests
Les outils fournis (`scripts/simulate_history.py`, `ai_tools/log_anomalies.py`, `ai_tools/test_history.py`)
analysent des journaux et des historiques : ils s'utilisent tels quels. L'application PHP écrit le même
journal que l'application Python (une ligne JSON par requête) quand `MINISHOP_LOG_FILE` est défini.

Seule l'étape A.4 (« sur vos logs réels ») change : l'application tourne dans un conteneur, le journal sort
par un dossier monté. Comme dans l'énoncé, il faut une phase normale qui sert de référence, **puis** une phase
ralentie, dans le même journal (le fichier est complété, pas écrasé). Depuis la racine du dépôt, image
construite au préalable (`docker build -t minishop-php declinaisons/php`) :
```bash
mkdir -p logs && chmod 777 logs && rm -f logs/app.jsonl
docker run -d --name app -p 8000:8000 -e MINISHOP_LOG_FILE=/logs/app.jsonl \
    -v "$PWD/logs":/logs minishop-php                                            # phase normale
locust -f tests/perf/locustfile.py --host http://localhost:8000 --headless -u 20 -r 5 -t 60s
docker rm -f app
docker run -d --name app -p 8000:8000 -e MINISHOP_LOG_FILE=/logs/app.jsonl -e MINISHOP_BUG=slow \
    -v "$PWD/logs":/logs minishop-php                                            # phase ralentie
locust -f tests/perf/locustfile.py --host http://localhost:8000 --headless -u 20 -r 5 -t 60s
docker rm -f app
python ai_tools/log_anomalies.py logs/app.jsonl --window 5
```
(Le second Locust se termine en échec : ses propres seuils ne sont pas tenus, c'est attendu.) Mêmes questions
que dans l'énoncé. Pour la partie C, la barrière `--fail-on-anomaly` (critère absolu : 5xx ≥ 5 % ou p95 ≥ 500 ms
sur une fenêtre) s'applique telle quelle à ce journal. Pour verser vos propres exécutions de tests dans la
partie B, PHPUnit produit le même format JUnit que pytest (`--log-junit`).

## Atelier 6 — Machine learning : zones à risque
Rien à porter. Le modèle (`ai_tools/risk_model.py`) s'entraîne sur l'historique Git simulé, indépendant du
langage. La priorisation des tests se transpose avec `vendor/bin/phpunit --filter` ou `--group`.

## Atelier 7 — Tests visuels
Rien à porter. Les captures et la comparaison d'images (`tests/visual`, `ai_tools/visual_diff.py`) visent
l'application qui tourne ; la page servie par l'application PHP est le même fichier que celle de Python.

## Atelier 8 — Tests UI de bout en bout
Énoncé décliné : [`atelier-08-tests-ui-e2e.md`](atelier-08-tests-ui-e2e.md) (Symfony Panther, projet `boite-noire/`).

## Atelier 9 — Tests d'API
Énoncé décliné : [`atelier-09-tests-api.md`](atelier-09-tests-api.md) (tests en mémoire, variante Guzzle dans `boite-noire/`).

## Atelier 10 — Performance et charge
Rien à porter. JMeter, Locust (`tests/perf`) et le monitoring visent l'application qui tourne sur le port 8000.
Le bug de performance s'injecte de la même façon : `MINISHOP_BUG=slow docker compose up -d`.

## Atelier 11 — Sécurité
Énoncé décliné : [`atelier-11-securite.md`](atelier-11-securite.md) (Psalm, `composer audit`, Trivy sur l'image PHP, ZAP).

## Atelier 12 — Reporting, documentation, monitoring
Rien à porter. Pour alimenter les rapports avec la suite PHP, PHPUnit écrit du JUnit
(`--log-junit reports/junit.xml`) et une liste lisible des tests (`--testdox`, `--testdox-html`).
Allure, MkDocs, Prometheus et Grafana s'utilisent comme dans l'énoncé : l'application PHP expose `/metrics`
avec les mêmes noms de métriques et les mêmes étiquettes, et Prometheus la scrape toujours sur
`host.docker.internal:8000`.
