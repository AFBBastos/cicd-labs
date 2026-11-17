# Ateliers 5 à 12 — ce qui change en Node.js

Les Ateliers 8, 9 et 11 ont leur énoncé décliné dans ce dossier. Pour les autres, les énoncés de référence
restent ceux du dossier `ateliers/` à la racine : cette page indique ce qui s'utilise tel quel.

Dans tous ces ateliers, l'application testée est celle de ce dossier : même port, mêmes routes, mêmes
métriques et mêmes logs que l'application Python, que les outils fournis ne distinguent pas.
```bash
npm start                           # ou, dans Docker : docker compose up -d --build
curl -sf http://localhost:8000/health
```
Partout où un énoncé écrit `make run` ou `uvicorn minishop.api:app`, lisez `npm start` (depuis
`declinaisons/node/`) ; les variables `MINISHOP_BUG` et `MINISHOP_LOG_FILE` se placent devant de la même façon.
Les outils Python (`ai_tools/`, `scripts/`) se lancent toujours depuis la racine du dépôt.

Les tests Node.js boîte noire (Ateliers 8 et 9) lisent l'adresse dans la variable `MINISHOP_URL` (valeur par
défaut : `http://localhost:8000`). N'utilisez pas le nom `BASE_URL` : Vitest (via Vite) le réserve et lui
donne la valeur `/`.

Les commandes `npm` et `npx` se lancent depuis `declinaisons/node/`.

## Atelier 5 — Anomalies dans les logs et les exécutions de tests
Les outils fournis (`scripts/simulate_history.py`, `ai_tools/log_anomalies.py`, `ai_tools/test_history.py`)
s'utilisent tels quels. Seule l'étape A.4 (« sur vos logs réels ») change : c'est l'application de ce dossier
qui écrit le journal. Comme dans l'énoncé, il faut une phase normale qui sert de référence, puis une phase
ralentie, dans le même journal (le fichier est complété, pas écrasé). Tout se lance depuis la **racine du
dépôt** (après `npm ci` dans `declinaisons/node/`) :
```bash
rm -f logs/app.jsonl
MINISHOP_LOG_FILE=logs/app.jsonl node declinaisons/node/src/server.js &                     # phase normale
locust -f tests/perf/locustfile.py --host http://localhost:8000 --headless -u 20 -r 5 -t 60s
kill $!                                                                                      # arrête l'application
MINISHOP_LOG_FILE=logs/app.jsonl MINISHOP_BUG=slow node declinaisons/node/src/server.js &   # phase ralentie
locust -f tests/perf/locustfile.py --host http://localhost:8000 --headless -u 20 -r 5 -t 60s
kill $!
python ai_tools/log_anomalies.py logs/app.jsonl --window 5
```
(Le second Locust se termine en échec : ses propres seuils ne sont pas tenus, c'est attendu. On lance
`node …/server.js` plutôt que `npm start` pour que `kill $!` arrête bien le serveur, et non npm.)
Le format du journal est celui de l'application Python : une ligne JSON par requête (`ts`, `method`, `path`,
`status`, `latency_ms`). Les questions de l'énoncé sont inchangées, ainsi que le bonus de la partie C
(`log_anomalies.py --fail-on-anomaly` : seuil absolu, 5xx ≥ 5 % ou p95 ≥ 500 ms).
Pour comparer avec vos propres exécutions de tests, Vitest produit le même format JUnit que pytest
(`--reporter=junit --outputFile.junit=reports/junit.xml`).

## Atelier 6 — Machine learning : zones à risque
Rien à porter. Le modèle (`ai_tools/risk_model.py`) s'entraîne sur l'historique Git simulé, indépendant du
langage. La priorisation des tests se transpose avec un chemin ou un filtre de nom
(`npx vitest run tests/unit -t "coupon"`).

## Atelier 7 — Tests visuels
Les captures et la comparaison d'images (`tests/visual`, `ai_tools/visual_diff.py`) sont faites par les
outils Python fournis, sur l'application qui tourne : lancez celle de ce dossier (`npm start`), la page est
la même (`src/static/`). Pour provoquer une régression visuelle, modifiez `src/static/style.css`.

## Atelier 8 — Tests UI de bout en bout
Énoncé décliné : [atelier-08-tests-ui-e2e.md](atelier-08-tests-ui-e2e.md) (Playwright Test, Selenium, workflow `e2e-node.yml`).

## Atelier 9 — Tests d'API
Énoncé décliné : [atelier-09-tests-api.md](atelier-09-tests-api.md) (`fetch` + Vitest contre le serveur réel, contrat OpenAPI).

## Atelier 10 — Performance et charge
JMeter et Locust (`tests/perf`) visent l'application qui tourne sur le port 8000 : lancez celle de ce dossier.
Régression injectée : `MINISHOP_BUG=slow npm start`. Prometheus scrape toujours `/metrics` sur
`host.docker.internal:8000` : les noms de métriques et leurs étiquettes sont identiques, les tableaux de bord
fournis fonctionnent sans changement.

## Atelier 11 — Sécurité
Énoncé décliné : [atelier-11-securite.md](atelier-11-securite.md) (`eslint-plugin-security`, `npm audit`, workflow `security-node.yml`).

## Atelier 12 — Reporting, documentation, monitoring
Les métriques (`/metrics`) et les logs JSON (`MINISHOP_LOG_FILE`) de l'application de ce dossier ont le
même format que ceux de l'application Python. Pour alimenter les rapports avec la suite Node.js, Vitest écrit du JUnit
(`--reporter=junit`) et une liste lisible des tests (`--reporter=verbose`).
Allure, MkDocs, Prometheus et Grafana s'utilisent comme dans l'énoncé.

## Sous Windows

Poste sous **WSL2** : rien à adapter. En **PowerShell**, pas de `&` pour l'arrière-plan : l'étape A.4 de
l'Atelier 5 demande deux terminaux, ouverts à la racine du dépôt.
```powershell
# Terminal 1 — l'application avec journal, phase normale (Ctrl+C pour l'arrêter)
Remove-Item logs/app.jsonl -ErrorAction SilentlyContinue
$env:MINISHOP_LOG_FILE = "logs/app.jsonl"
node declinaisons/node/src/server.js

# Terminal 2 — la charge de référence
locust -f tests/perf/locustfile.py --host http://localhost:8000 --headless -u 20 -r 5 -t 60s

# Terminal 1 — Ctrl+C, puis l'application avec le ralentissement injecté
$env:MINISHOP_BUG = "slow"
node declinaisons/node/src/server.js

# Terminal 2 — la même charge, puis l'analyse
locust -f tests/perf/locustfile.py --host http://localhost:8000 --headless -u 20 -r 5 -t 60s
python ai_tools/log_anomalies.py logs/app.jsonl --window 5
```
Fermez le terminal 1 à la fin : les deux variables d'environnement disparaissent avec lui.
