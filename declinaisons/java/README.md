# MiniShop — déclinaison Java

L'application MiniShop complète portée en Java : règles de prix, catalogue, API HTTP (Spring Boot), page web,
métriques Prometheus, logs JSON, bugs injectables et image Docker. Elle est **interchangeable** avec
l'application Python du dépôt (mêmes routes, mêmes réponses, même port 8000) : tout ce qui teste MiniShop de
l'extérieur fonctionne sur l'une comme sur l'autre. Cette déclinaison sert aux stagiaires qui préfèrent
travailler en Java plutôt qu'en Python.

Les outils d'analyse du cours (`ai_tools/`, `scripts/`) restent en Python et s'utilisent tels quels sur les
logs et les métriques de cette application.

## Prérequis
- **JDK 21** (Temurin conseillé) : `java -version`
- **Maven 3.9** ou plus récent : `mvn -version`
- **Docker** pour lancer l'application en conteneur.
- Python et les outils de l'Atelier 0 restent nécessaires à partir de l'Atelier 3 (`ai_tools/`).

Sans JDK sur le poste, tout peut se lancer dans un conteneur, depuis ce dossier (le volume `minishop-m2`
garde les dépendances téléchargées d'un lancement à l'autre) :
```bash
docker run --rm -v "$PWD":/w -v minishop-m2:/root/.m2 -w /w maven:3.9-eclipse-temurin-21 mvn test
```
Sous Linux, le dossier `target/` créé ainsi appartient à `root` : supprimez-le par la même voie
(`… maven:3.9-eclipse-temurin-21 mvn clean`).

## Installation
Rien à installer à la main : Maven télécharge les dépendances au premier lancement (une à deux minutes).
```bash
cd declinaisons/java
mvn test
```

## Lancer l'application
Depuis `declinaisons/java/` :
```bash
docker compose up -d --build        # http://localhost:8000  —  API : http://localhost:8000/docs
docker compose down
```
ou, sans conteneur : `mvn spring-boot:run` (arrêt par Ctrl+C).

N'utilisez qu'une application à la fois sur le port 8000 : arrêtez celle de la racine du dépôt
(`docker compose down` à la racine) avant de lancer celle-ci.

| Adresse | Contenu |
|---|---|
| `/` et `/static/*` | page web de la boutique |
| `/health`, `/products`, `/products/{product_id}`, `/cart/quote`, `/orders`, `/orders/{order_id}` | API JSON |
| `/metrics` | métriques Prometheus (`minishop_http_requests_total`, `minishop_http_request_duration_seconds`, `minishop_orders_total`) |
| `/openapi.json`, `/docs` | contrat OpenAPI et documentation interactive |

| Variable d'environnement | Effet |
|---|---|
| `MINISHOP_BUG=rounding` | arrondi bancaire au lieu de commercial (0,125 → 0,12) |
| `MINISHOP_BUG=slow` | 300 à 800 ms de latence sur `/cart/*` |
| `MINISHOP_LOG_FILE=logs/app.jsonl` | une ligne JSON par requête (format lu par `ai_tools/log_anomalies.py`) |

Avec Docker : `MINISHOP_BUG=slow docker compose up -d --build`.

## Commandes
| Besoin | Commande |
|---|---|
| Tests (unitaires + API en mémoire) | `mvn test` |
| Tests portant une étiquette | `mvn test -Dgroups=unit` · `mvn test -Dgroups=api` |
| Une classe, une méthode | `mvn test -Dtest=PricingTest` · `mvn test -Dtest='PricingTest#quotePanierVide'` |
| Tests + couverture | `mvn verify` puis ouvrir `target/site/jacoco/index.html` |
| Couverture avec seuil bloquant | `mvn verify -Djacoco.branches.min=0.90` |
| Vérifier le format | `mvn spotless:check` |
| Corriger le format | `mvn spotless:apply` |
| Tests de mutation | `mvn test-compile org.pitest:pitest-maven:mutationCoverage` puis `target/pit-reports/index.html` |
| Analyse statique de sécurité (Atelier 11) | `mvn compile spotbugs:check` |
| Construire le jar exécutable | `mvn package` puis `java -jar target/minishop.jar` |
| Tout nettoyer | `mvn clean` |

Tests « boîte noire » de l'application lancée (ateliers 8 et 9), depuis `tests-app/` :

| Besoin | Commande |
|---|---|
| Installer les navigateurs (une fois) | `mvn test-compile exec:java -Dexec.mainClass=com.microsoft.playwright.CLI -Dexec.classpathScope=test -Dexec.args="install --with-deps chromium firefox"` |
| Tests d'API par HTTP | `mvn test -Dgroups=api` |
| Tests E2E | `mvn test -Dgroups=e2e` (options : `-Dbrowser=firefox`, `-Dheaded=true`, `-Dslowmo=300`) |
| Autre adresse d'application | `-Dapp.url=http://hote:port`, ou variable d'environnement `APP_URL` (défaut : `http://localhost:8000`) |

Rapports produits dans `target/` (à ne pas committer) : `surefire-reports/` (JUnit XML),
`site/jacoco/` (HTML, `jacoco.xml`, `jacoco.csv`), `pit-reports/`.

## Plan du dossier
```
declinaisons/java/
├── pom.xml                          dépendances, tests, couverture, format, mutation, SpotBugs
├── Dockerfile, docker-compose.yml   image de l'application (construction en deux étapes, JRE seul à l'exécution)
├── spotbugs-exclude.xml             alertes SpotBugs écartées, avec leur justification
├── src/main/java/fr/minishop/
│   ├── Pricing.java                 règles de prix : money, lineTotal, couponDiscount, shippingCost, quote
│   ├── Quote.java, Line.java, Item.java   devis, ligne de devis, article demandé
│   ├── Catalog.java, Product.java   catalogue en mémoire
│   └── api/                         application web (Spring Boot)
│       ├── MiniShopApplication.java   point d'entrée
│       ├── ShopController.java        routes de l'API
│       ├── Cart.java, CartItem.java   corps des requêtes et leurs règles de validation
│       ├── ApiErrors.java, ApiException.java   erreurs au format {"detail": …}
│       ├── ObservabilityFilter.java   métriques, logs JSON, bug de lenteur
│       └── MetricsConfig.java         registre Prometheus
├── src/main/resources/
│   ├── application.properties       port 8000, chemins /static, /openapi.json, /docs
│   └── static/                      index.html, style.css (identiques à ceux de l'application Python)
├── src/test/java/fr/minishop/
│   ├── PricingTest.java             3 tests unitaires d'exemple + TODO (Atelier 1)
│   └── api/ApiSmokeTest.java        2 tests d'API en mémoire + TODO (Atelier 9)
├── tests-app/                       projet Maven séparé : tests de l'application lancée (par HTTP, par navigateur)
│   ├── pom.xml                      Playwright for Java, RestAssured
│   └── src/test/java/fr/minishop/app/
│       ├── AppUrl.java              adresse de l'application (-Dapp.url, APP_URL, défaut localhost:8000)
│       ├── e2e/ShopOptions.java     réglages Playwright (navigateur, mode visible, traces)
│       ├── e2e/ParcoursAchatTest.java   test de la page d'accueil + TODO (Atelier 8)
│       └── api/ApiSmokeTest.java    2 tests de fumée par HTTP + TODO (Atelier 9, variante « serveur réel »)
└── ateliers/                        énoncés déclinés (1 à 4, 8, 9, 11) et notes pour les autres ateliers
```
`tests-app/` est volontairement indépendant : ses tests demandent une application lancée et ne comptent ni dans
la couverture ni dans les tests de mutation. Les tests de `src/test/` n'ont besoin de rien : ceux de l'API
appellent l'application **en mémoire** (MockMvc).

La spécification `specs/pricing.feature` (à la racine du dépôt) est commune à tous les langages.

## Python du cours → équivalent ici
| Python du cours | Java |
|---|---|
| `pip` + `venv`, `requirements-dev.txt` | Maven, `pom.xml` (dépôt local `~/.m2`) |
| `pytest` | JUnit (Jupiter) lancé par Maven Surefire (`mvn test`) |
| `assert a == b` | AssertJ : `assertThat(a).isEqualTo(b)` |
| `pytest.raises(ValueError)` | `assertThatThrownBy(() -> …).isInstanceOf(IllegalArgumentException.class)` |
| `@pytest.mark.parametrize` | `@ParameterizedTest` + `@ValueSource` / `@CsvSource` / `@MethodSource` |
| marqueurs `@pytest.mark.unit`, `pytest -m unit` | `@Tag("unit")`, `mvn test -Dgroups=unit` |
| `pytest -m "unit and not generated"` | `mvn test "-Dgroups=unit & !generated"` |
| `--junitxml=reports/junit.xml` | automatique : `target/surefire-reports/TEST-*.xml` |
| `pytest --cov --cov-branch`, `htmlcov/` | JaCoCo : `mvn verify`, `target/site/jacoco/` |
| `--cov-fail-under=85` | règle `check` de JaCoCo : `-Djacoco.branches.min=0.90` |
| `ruff check`, `ruff format --check` | Spotless + google-java-format : `mvn spotless:check` |
| `ruff format` | `mvn spotless:apply` |
| `Decimal("12.50")`, `ROUND_HALF_UP` | `new BigDecimal("12.50")`, `RoundingMode.HALF_UP` |
| `ValueError` | `IllegalArgumentException` |
| `KeyError` (produit inconnu) | `NoSuchElementException` |
| `Quote.as_dict()` | `Quote.asMap()` |
| `dict` `{"product_id": "mug", "qty": 2}` | `new Item("mug", 2)` |
| `ai_tools/mutation_score.py` | PIT (`pitest-maven`) |
| Playwright Python (`page`, `expect`) | Playwright for Java (`@UsePlaywright`, `assertThat`) dans `tests-app/` |
| FastAPI, `uvicorn` | Spring Boot (`mvn spring-boot:run`) |
| `TestClient` (API en mémoire) | MockMvc (`@SpringBootTest` + `@AutoConfigureMockMvc`) |
| `httpx` contre le serveur réel | RestAssured, dans `tests-app/` |
| `prometheus_client` | Micrometer + registre Prometheus |
| Bandit, `ruff --select S` | SpotBugs + FindSecBugs |
| pip-audit | OSV-Scanner (ou OWASP Dependency-Check) |
| `monkeypatch.setenv` | pas d'équivalent propre : passer la valeur en paramètre (voir Atelier 1) |

## Deux différences à connaître
- **Égalité des décimaux.** `new BigDecimal("25.0").equals(new BigDecimal("25.00"))` vaut `false` : `equals`
  compare aussi l'échelle (le nombre de décimales). Comparez les montants avec `compareTo`
  (AssertJ : `isEqualByComparingTo("25.00")`). Tous les montants renvoyés par `Pricing` sont à l'échelle 2.
- **Typage statique.** La quantité est un `int` : `lineTotal(prix, "2")` ou `lineTotal(prix, true)` ne compilent
  pas. Les tests Python de ces cas, et le message « La quantité doit être un entier », n'ont donc pas d'équivalent.

## Sous Windows
Les commandes `mvn` sont identiques en PowerShell. Les différences :

- Mettez entre guillemets les options qui contiennent un point ou un caractère spécial :
  `mvn verify "-Djacoco.branches.min=0.90"`, `mvn test "-Dgroups=unit & !generated"`.
- Variable d'environnement (bug d'arrondi injecté) :
  ```powershell
  $env:MINISHOP_BUG = "rounding"; mvn test; Remove-Item Env:MINISHOP_BUG
  ```
  Sans le `Remove-Item`, le bug reste actif dans ce terminal.
- Rapport de couverture : `start target/site/jacoco/index.html`
- Conteneur : `docker run --rm -v "${PWD}:/w" -v minishop-m2:/root/.m2 -w /w maven:3.9-eclipse-temurin-21 mvn test`
