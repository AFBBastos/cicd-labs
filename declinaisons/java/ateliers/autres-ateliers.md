# Ateliers 5 à 12 — ce qui change en Java

L'application MiniShop est portée en Java et interchangeable avec l'application Python : pour tous les
ateliers ci-dessous, lancez celle de ce dossier, depuis `declinaisons/java/` :
```bash
docker compose up -d --build        # http://localhost:8000
```
(Une seule application à la fois sur le port 8000 : arrêtez celle de la racine si elle tourne.)

Suivez ensuite l'énoncé d'origine (`ateliers/` à la racine) ; cette page ne liste que les différences.
Les outils d'analyse (`ai_tools/`, `scripts/`) restent en Python et s'utilisent tels quels, depuis la racine
du dépôt : ils lisent les logs et les métriques de l'application, quel que soit son langage.

Les ateliers 8, 9 et 11 ont leur propre énoncé décliné.

## Atelier 5 — Anomalies dans les logs et les exécutions de tests
Outils inchangés (lancés depuis la racine du dépôt). Seule l'étape A.4 « sur vos logs réels » change : une phase
normale qui sert de référence, puis une phase ralentie, dans le même journal (le fichier est complété, pas écrasé).
Depuis `declinaisons/java/` pour l'application, depuis la racine pour Locust et l'analyse :
```bash
# dans declinaisons/java
mvn -q package -DskipTests && rm -f logs/app.jsonl
MINISHOP_LOG_FILE=logs/app.jsonl java -jar target/minishop.jar &                     # phase normale
#   (racine) locust -f tests/perf/locustfile.py --host http://localhost:8000 --headless -u 20 -r 5 -t 60s
kill $!                                                                              # arrête l'application
MINISHOP_LOG_FILE=logs/app.jsonl MINISHOP_BUG=slow java -jar target/minishop.jar &   # phase ralentie
#   (racine) locust -f tests/perf/locustfile.py --host http://localhost:8000 --headless -u 20 -r 5 -t 60s
kill $!
#   (racine) python ai_tools/log_anomalies.py declinaisons/java/logs/app.jsonl --window 5
```
Attendez que l'application réponde (`curl -sf localhost:8000/health`) avant chaque Locust : la JVM met une dizaine
de secondes à démarrer. Le second Locust se termine en échec : ses propres seuils ne sont pas tenus, c'est attendu.
Seules les routes `/cart/*` sont ralenties. Bonus de la Partie C : `--fail-on-anomaly` fait échouer la commande
si une fenêtre dépasse un seuil absolu (5xx ≥ 5 % ou p95 ≥ 500 ms).

## Atelier 6 — Machine learning : zones à risque
Rien à porter : le modèle travaille sur l'historique Git simulé. Énoncé inchangé.

## Atelier 7 — Tests visuels
Outils inchangés : les captures et `ai_tools/visual_diff.py` s'appliquent à l'application lancée. La page est la même
(`src/main/resources/static/`) ; pour provoquer une régression visuelle, modifiez `style.css` dans ce dossier.

## Atelier 8 — Tests UI de bout en bout
Énoncé décliné : [atelier-08-tests-ui-e2e.md](atelier-08-tests-ui-e2e.md) (Playwright for Java, Selenium).

## Atelier 9 — Tests d'API
Énoncé décliné : [atelier-09-tests-api.md](atelier-09-tests-api.md) (MockMvc en mémoire, RestAssured contre le serveur).

## Atelier 10 — Performance et charge
Outils inchangés : Locust et JMeter chargent l'application lancée. `MINISHOP_BUG=slow docker compose up -d --build`
injecte 300 à 800 ms sur `/cart/*`.

## Atelier 11 — Tests de sécurité
Énoncé décliné : [atelier-11-securite.md](atelier-11-securite.md) (SpotBugs + FindSecBugs, OSV-Scanner).

## Atelier 12 — Reporting, documentation vivante et monitoring
Outils inchangés. L'application expose les mêmes métriques sur `/metrics` (`minishop_http_requests_total`,
`minishop_http_request_duration_seconds`, `minishop_orders_total`) : Prometheus scrape toujours `host.docker.internal:8000`,
les tableaux de bord fonctionnent tels quels.
