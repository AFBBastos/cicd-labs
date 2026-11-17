# Ateliers 5 à 12 — ce qui change en C#

L'application complète est portée en C# (`src/MiniShop.Api`). Pour tous les ateliers ci-dessous, lancez-la à
la place de l'application Python, depuis `declinaisons/csharp/` :
```bash
docker compose up -d --build                 # http://localhost:8000
dotnet run --project src/MiniShop.Api        # ou directement, sans Docker
```
Elle expose les mêmes routes, la même page, les mêmes métriques et le même journal que l'application Python :
les outils du dépôt (`ai_tools/`, `scripts/`, Locust, JMeter, Prometheus, Grafana) s'y appliquent sans
modification. Suivez l'énoncé d'origine (`ateliers/` à la racine) ; cette page ne liste que les différences.
Les ateliers 8, 9 et 11 ont leur propre énoncé dans ce dossier.

Partout où l'énoncé d'origine écrit `uvicorn minishop.api:app` (ou `make run`), lisez
`dotnet run --project src/MiniShop.Api`, lancé depuis `declinaisons/csharp/`. Les variables d'environnement
sont les mêmes (`MINISHOP_BUG`, `MINISHOP_LOG_FILE`).

## Atelier 5 — Anomalies dans les logs et les exécutions de tests
Les outils d'analyse sont inchangés. Pour l'étape A.4 (« sur vos logs réels »), le journal vient de
l'application C# : une phase normale qui sert de référence, puis une phase ralentie, dans le **même** fichier
(l'application le complète, elle ne l'écrase pas).
```bash
# terminal 1, depuis declinaisons/csharp — phase normale
rm -f src/MiniShop.Api/logs/app.jsonl
MINISHOP_LOG_FILE=logs/app.jsonl dotnet run --project src/MiniShop.Api
# terminal 2, depuis la racine du dépôt
locust -f tests/perf/locustfile.py --host http://localhost:8000 --headless -u 20 -r 5 -t 60s
# terminal 1 : Ctrl+C, puis phase ralentie
MINISHOP_LOG_FILE=logs/app.jsonl MINISHOP_BUG=slow dotnet run --project src/MiniShop.Api
# terminal 2 : la même commande locust, puis l'analyse (terminal 1 : Ctrl+C)
locust -f tests/perf/locustfile.py --host http://localhost:8000 --headless -u 20 -r 5 -t 60s
python ai_tools/log_anomalies.py declinaisons/csharp/src/MiniShop.Api/logs/app.jsonl --window 5
```
(Le second Locust se termine en échec : ses propres seuils ne sont pas tenus, c'est attendu.)
Un chemin relatif dans `MINISHOP_LOG_FILE` part du dossier du projet, `src/MiniShop.Api` : c'est le dossier de
travail que `dotnet run` donne à l'application. Les questions de l'énoncé et le bonus de la partie C
(`log_anomalies.py --fail-on-anomaly`) s'appliquent tels quels à ce journal.

## Atelier 6 — Machine learning : zones à risque
Rien à porter : le modèle travaille sur les données simulées du dépôt. Énoncé inchangé.

## Atelier 7 — Tests visuels
Les captures et `ai_tools/visual_diff.py` s'appliquent à l'application C# lancée sur le port 8000. La feuille
de style à modifier pour provoquer une différence est `src/MiniShop.Api/wwwroot/static/style.css` (relancez
l'application, ou reconstruisez l'image, après la modification).

## Atelier 8 — Tests UI de bout en bout
Énoncé décliné : [atelier-08-tests-ui-e2e.md](atelier-08-tests-ui-e2e.md) (Microsoft.Playwright, Selenium).

## Atelier 9 — Tests d'API
Énoncé décliné : [atelier-09-tests-api.md](atelier-09-tests-api.md) (`HttpClient` + xUnit contre le serveur réel).

## Atelier 10 — Performance
Locust et JMeter chargent l'application C# sur le port 8000 ; régression injectée avec `MINISHOP_BUG=slow`
(`MINISHOP_BUG=slow docker compose up -d`, ou la variable devant `dotnet run`). Pour le monitoring, Prometheus
lit toujours `host.docker.internal:8000/metrics` : lancée par `docker compose`, l'application y répond déjà ;
lancée par `dotnet run`, elle n'écoute que `localhost` — ajoutez `--urls http://0.0.0.0:8000`.

## Atelier 11 — Sécurité
Énoncé décliné : [atelier-11-securite.md](atelier-11-securite.md) (analyseurs Roslyn, audit NuGet ; Trivy et ZAP inchangés).

## Atelier 12 — Reporting, documentation et monitoring
Allure et la documentation des tests s'appuient sur les tests Python du dépôt : énoncé inchangé. Le monitoring
(Prometheus, Grafana) lit les métriques de l'application C#, qui portent les mêmes noms. Pour vos tests C#,
`dotnet test --logger "junit;LogFileName={assembly}.xml"` produit des rapports au format JUnit XML, comme
`pytest --junitxml`.
