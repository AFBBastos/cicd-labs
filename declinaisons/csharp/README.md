# MiniShop — déclinaison C# / .NET

L'application MiniShop complète portée en C# : règles de prix et catalogue (bibliothèque `MiniShop`), API HTTP,
page web, métriques Prometheus et journal des requêtes (`MiniShop.Api`, ASP.NET Core), image Docker. Elle est
interchangeable avec l'application Python du dépôt : mêmes routes, mêmes réponses, même port. Tous les
ateliers peuvent donc se suivre sans écrire de Python ; seuls les outils d'analyse `ai_tools/` restent en Python.

## Prérequis
- **SDK .NET 10** (LTS) : `dotnet --version` doit afficher `10.0.x`. Installation : https://dotnet.microsoft.com/download
  (Windows : `winget install Microsoft.DotNet.SDK.10`).
- Docker pour l'image de l'application ; Python et les outils du dépôt (Atelier 0) pour les ateliers qui
  utilisent `ai_tools/`.

Sans SDK sur le poste, tout fonctionne aussi dans un conteneur :
```bash
docker run --rm -it -v "$PWD":/w -w /w mcr.microsoft.com/dotnet/sdk:10.0 bash
```

## Installation
Depuis `declinaisons/csharp/` :
```bash
dotnet tool restore      # outils locaux (dotnet-tools.json) : reportgenerator, Stryker.NET
dotnet restore           # paquets NuGet, versions figées par packages.lock.json
```

## Lancer l'application
Depuis `declinaisons/csharp/`, au choix :
```bash
dotnet run --project src/MiniShop.Api        # http://localhost:8000, Ctrl+C pour arrêter
docker compose up -d --build                 # la même, dans son image Docker (docker compose down pour arrêter)
```
Page web : http://localhost:8000 · documentation de l'API : http://localhost:8000/docs (schéma : `/openapi.json`) ·
métriques : http://localhost:8000/metrics.

L'application occupe le port 8000, comme l'application Python : n'en lancez qu'une à la fois.

Variables d'environnement reconnues : `MINISHOP_BUG=rounding` (arrondi bancaire), `MINISHOP_BUG=slow` (300 à
800 ms d'attente sur `/cart/*`), `MINISHOP_LOG_FILE=logs/app.jsonl` (une ligne JSON par requête).

## Commandes
| But | Commande |
|---|---|
| Tests unitaires | `dotnet test --filter "Category=unit"` |
| Tests d'API en mémoire | `dotnet test --filter "Category=api"` |
| Les deux (ce que lance la CI) | `dotnet test --filter "Category=unit\|Category=api"` |
| Détail test par test | `dotnet test --logger "console;verbosity=normal"` |
| Couverture des règles de prix (mesure) | `dotnet test tests/MiniShop.Tests --collect:"XPlat Code Coverage" --results-directory reports/tests` |
| Couverture (rapport) | `dotnet reportgenerator "-reports:reports/tests/*/coverage.cobertura.xml" -targetdir:reports/coverage "-reporttypes:Html;TextSummary"` |
| Seuil bloquant (Atelier 1) | ajouter `minimumCoverageThresholds:branchCoverage=90` à la commande précédente |
| Couverture et seuils du pipeline (Atelier 2) | mesure sur `dotnet test --filter "Category=unit\|Category=api"`, puis le rapport avec `"-classfilters:-*Generated*;-System.*" minimumCoverageThresholds:lineCoverage=85 minimumCoverageThresholds:branchCoverage=90` |
| Rapport JUnit | `dotnet test --logger "junit;LogFileName={assembly}.xml" --results-directory reports/tests` |
| Lint / format (vérifier) | `dotnet format --verify-no-changes` puis `dotnet build` |
| Format (corriger) | `dotnet format` |
| Tests de mutation (règles de prix) | `dotnet stryker` |
| Bug d'arrondi injecté | `MINISHOP_BUG=rounding dotnet test --filter "Category=unit"` |
| Tests E2E (Atelier 8) | depuis `tests/MiniShop.Acceptance.Tests` : `dotnet test --filter "Category=e2e"` |
| Tests d'API par HTTP (Atelier 9) | depuis `tests/MiniShop.Acceptance.Tests` : `dotnet test --filter "Category=api"` |
| Règles de sécurité (Atelier 11) | `dotnet build --no-incremental -p:AnalysisLevelSecurity=latest-all` |
| Dépendances vulnérables (Atelier 11) | `dotnet list package --vulnerable --include-transitive` |

Le rapport de couverture se lit dans `reports/coverage/Summary.txt` (texte) ou `reports/coverage/index.html`.
Supprimez `reports/` avant une nouvelle mesure : chaque exécution y ajoute un sous-dossier. La mesure désigne
`tests/MiniShop.Tests` pour ne compter que la bibliothèque `MiniShop` ; sans ce chemin, le rapport inclut
aussi l'API.

Les tests de `tests/MiniShop.Acceptance.Tests` (E2E, API par HTTP) demandent l'application lancée ; son adresse
se lit dans la variable d'environnement `BASE_URL` (défaut : `http://localhost:8000`). Les tests E2E demandent
aussi les navigateurs de Playwright (voir l'Atelier 8). Les tests de `tests/MiniShop.Api.Tests`, eux, démarrent
l'application en mémoire : rien à lancer.

## Plan du dossier
```
declinaisons/csharp/
├── MiniShop.slnx                  solution : 2 projets de code + 2 projets de tests
├── Directory.Build.props          réglages communs : net10.0, Nullable, analyseurs, avertissements = erreurs
├── .editorconfig                  règles de style et de mise en forme (dotnet format)
├── dotnet-tools.json              outils locaux : dotnet-stryker, reportgenerator
├── stryker-config.json            configuration des tests de mutation (bibliothèque MiniShop)
├── Dockerfile, .dockerignore      image de l'application (construction en deux étapes, utilisateur non root)
├── docker-compose.yml             service minishop, port 8000
├── src/MiniShop/                  cœur métier, sans dépendance web
│   ├── Pricing.cs                 règles de prix : Money, LineTotal, CouponDiscount, ShippingCost, Quote
│   └── Catalog.cs                 catalogue en mémoire : ListProducts, GetProduct
├── src/MiniShop.Api/              application web (ASP.NET Core, API minimale)
│   ├── Program.cs                 routes, gestion des erreurs, OpenAPI, /docs
│   ├── Contracts.cs               formes JSON des requêtes et des réponses
│   ├── JsonSetup.cs               snake_case, montants en chaînes
│   ├── BodyIssue.cs               erreurs de lecture du corps -> 422 + detail
│   ├── Observability.cs           métriques Prometheus, journal JSON, bug « slow »
│   └── wwwroot/static/            index.html et style.css (identiques à ceux de l'application Python)
├── tests/MiniShop.Tests/
│   ├── PricingTests.cs            tests unitaires de départ (Atelier 1)
│   └── xunit.runner.json          parallélisme entre classes désactivé (voir Atelier 1, étape 4)
├── tests/MiniShop.Api.Tests/
│   └── ApiSmokeTests.cs           tests d'API en mémoire de départ (Atelier 9)
├── tests/MiniShop.Acceptance.Tests/   projet HORS solution : tests contre l'application lancée
│   ├── ParcoursAchatTests.cs      test E2E de départ (Atelier 8)
│   ├── ApiSmokeTests.cs           tests d'API par HTTP de départ (Atelier 9, variante « serveur réel »)
│   └── AppUrl.cs                  adresse de l'application (BASE_URL)
└── ateliers/                      énoncés des ateliers 1 à 4, 8, 9 et 11 + ce qui change pour les autres
```
La spécification `specs/pricing.feature` (racine du dépôt) est commune à tous les langages.

## Python du cours → équivalent ici
| Python (cours) | C# (ce dossier) |
|---|---|
| `pip` + `venv`, `requirements-dev.txt` | NuGet : `dotnet restore`, `<PackageReference>` dans les `.csproj`, `packages.lock.json` |
| `pytest` | xUnit, lancé par `dotnet test` |
| `def test_…()` + `assert` | méthode `[Fact]` + `Assert.Equal(attendu, obtenu)` |
| `@pytest.mark.parametrize` | `[Theory]` + `[InlineData(…)]` |
| `pytest.raises(ValueError)` | `Assert.Throws<ArgumentOutOfRangeException>(…)` / `Assert.Throws<ArgumentException>(…)` |
| `pytest.raises(KeyError)` | `Assert.Throws<KeyNotFoundException>(…)` |
| marqueur `pytest.mark.unit`, `pytest -m unit` | `[Trait("Category", "unit")]`, `dotnet test --filter "Category=unit"` |
| `monkeypatch.setenv` | `Environment.SetEnvironmentVariable` + restauration dans un `finally` |
| `pytest --cov --cov-branch` (coverage.py) | coverlet (`--collect:"XPlat Code Coverage"`) + reportgenerator |
| `--cov-fail-under=90` | `minimumCoverageThresholds:branchCoverage=90` (reportgenerator) |
| `--junitxml=…` | `--logger "junit;LogFileName=…"` (paquet JunitXml.TestLogger) |
| `ruff check` | analyseurs Roslyn à la compilation (`dotnet build`, avertissements = erreurs) |
| `ruff format --check` / `ruff format` | `dotnet format --verify-no-changes` / `dotnet format` |
| `pyproject.toml` | `Directory.Build.props`, `.editorconfig`, `.csproj` |
| `Decimal("12.50")` | `12.50m` (type `decimal`) |
| `quantize(CENT, ROUND_HALF_UP)` | `Math.Round(x, 2, MidpointRounding.AwayFromZero)` |
| `str(montant)` | `montant.ToString("F2", CultureInfo.InvariantCulture)` |
| `ai_tools/mutation_score.py` | Stryker.NET (`dotnet stryker`) |
| Playwright pour Python, `pytest -m e2e` | Microsoft.Playwright.Xunit (`PageTest`), `dotnet test --filter "Category=e2e"` |
| FastAPI + `uvicorn` | ASP.NET Core en API minimale (`Program.cs`), `dotnet run` |
| modèles Pydantic | `record` C# + System.Text.Json (`Contracts.cs`, `JsonSetup.cs`) |
| `TestClient` (en mémoire) | `WebApplicationFactory<Program>` (`tests/MiniShop.Api.Tests`) |
| `httpx.Client` (serveur réel) | `HttpClient` (`tests/MiniShop.Acceptance.Tests`) |
| `prometheus_client` | `prometheus-net` |
| `bandit`, `ruff --select S` | analyseurs de sécurité Roslyn (`CA2xxx`, `CA3xxx`, `CA5xxx`) |
| `pip-audit` | audit NuGet (`dotnet restore`, `dotnet list package --vulnerable`) |
| `pytest-xdist` (`-n auto`) | parallélisme intégré à xUnit (désactivé ici, voir `xunit.runner.json`) |

Trois différences à connaître :
- **Typage** : la quantité est un `int`. Les cas « quantité `"2"` » ou « quantité `True` » de la version
  Python sont refusés par le compilateur ; le message « La quantité doit être un entier » n'existe donc pas ici.
- **Erreurs** : quantité hors limites → `ArgumentOutOfRangeException` ; coupon inconnu → `ArgumentException` ;
  produit inconnu → `KeyNotFoundException`. Les messages sont les mêmes qu'en Python (« Quantité hors limites
  (1..99) : … », « Coupon inconnu : … », « Produit inconnu : … ») ; pour la quantité, .NET y ajoute le nom du
  paramètre fautif.
- **Virgule décimale** : `Math.Round(10m, 2)` vaut `10`, pas `10.00`, et sur un poste en français
  `27.40m.ToString()` donne `27,40`. D'où `ToString("F2", CultureInfo.InvariantCulture)` dans
  `Quote.AsDictionary()` (l'équivalent de `as_dict()`), et `decimal.Parse(…, CultureInfo.InvariantCulture)`
  dans les tests.

## Sous Windows
Les commandes `dotnet` sont identiques en PowerShell (gardez les guillemets). Ce qui diffère :
```powershell
# Bug d'arrondi injecté
$env:MINISHOP_BUG = "rounding"; dotnet test --filter "Category=unit"; Remove-Item Env:MINISHOP_BUG

# Ouvrir le rapport de couverture, repartir de zéro
start reports/coverage/index.html
Remove-Item -Recurse reports
```
