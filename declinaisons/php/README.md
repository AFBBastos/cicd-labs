# MiniShop — déclinaison PHP

L'application MiniShop complète portée en PHP, pour suivre les ateliers sans écrire de Python : règles de
prix et catalogue (`minishop/pricing.py`, `minishop/catalog.py`), API HTTP, page web, métriques Prometheus et
logs (`minishop/api.py`). Les règles, les valeurs, les routes, les codes et les messages d'erreur sont
**identiques** à la version Python ; la spécification `specs/pricing.feature` est commune.

L'application PHP est **interchangeable** avec l'application Python : même port (8000), mêmes réponses. Tout ce
qui teste MiniShop de l'extérieur (collection Postman, tests E2E, tests de charge, ZAP, monitoring) fonctionne
sans modification. Ne lancez qu'une des deux à la fois.

## Lancer l'application

```bash
cd declinaisons/php
docker compose up -d --build        # http://localhost:8000 ; docs : /docs ; arrêt : docker compose down
curl -sf http://localhost:8000/health
```
L'image embarque FrankenPHP (serveur web + PHP) et l'extension APCu. En PHP, chaque requête repart d'un état
vierge : c'est APCu, une mémoire partagée, qui garde les commandes et les métriques d'une requête à l'autre.

Sans Docker, avec le serveur intégré de PHP (développement uniquement, une requête à la fois) :
```bash
composer serve                      # http://localhost:8000 ; Ctrl+C pour arrêter
```
L'extension `apcu` doit alors être installée ; sans elle, l'application répond mais oublie les commandes et
remet les métriques à zéro à chaque requête.

Variables d'environnement : `MINISHOP_BUG=rounding` (arrondi bancaire) ou `slow` (300 à 800 ms d'attente sur
`/cart*`, les autres routes restant rapides) ; `MINISHOP_LOG_FILE=logs/app.jsonl` (une ligne JSON par requête, lue par `ai_tools/log_anomalies.py`).

Les tests qui visent l'application par HTTP sont dans le projet séparé `boite-noire/` : ils n'entrent ni dans
la suite unitaire, ni dans la couverture, ni dans les tests de mutation.

## Prérequis

| Outil | Version | Remarque |
|---|---|---|
| PHP (CLI) | 8.3 ou 8.4 | extensions `dom`, `mbstring`, `xml`, `xmlwriter`, `tokenizer` (présentes dans la plupart des installations) |
| Composer | 2.x | https://getcomposer.org |
| Xdebug **ou** pcov | — | pilote de couverture ; **Xdebug** est nécessaire pour la couverture de **branches** |
| Docker | — | pour lancer l'application (image du dossier) et pour le job `docker` de la CI |
| APCu | — | facultatif : seulement pour `composer serve` (l'image Docker l'embarque) |

Vérifiez : `php -v`, `composer --version`, `php -m` (cherchez `xdebug` ou `pcov`).

Sans PHP sur le poste, l'image officielle suffit pour les tests et le lint (pas pour la couverture, elle
n'embarque ni Xdebug ni pcov) :
```bash
docker run --rm -v "$PWD":/app -w /app composer:2 sh -c "composer install && composer test"
```

## Installation

Toutes les commandes se lancent depuis ce dossier :
```bash
cd declinaisons/php
composer install          # installe les versions figées dans composer.lock, dans vendor/
```

## Commandes

| Commande | Effet |
|---|---|
| `composer test` | tests unitaires (PHPUnit, suite `unit`) |
| `composer api` | tests d'API **en mémoire** (suite `api`) : requêtes passées directement à l'application, aucun serveur à lancer |
| `composer serve` | lance l'application avec le serveur intégré de PHP |
| `composer coverage` | tests + couverture de lignes : résumé à l'écran, HTML dans `reports/coverage/`, Cobertura et JUnit dans `reports/` |
| `composer coverage-branches` | idem avec la couverture de branches et de chemins (Xdebug obligatoire) |
| `php tools/coverage-check.php reports/cobertura.xml --min-lines=85` | seuil de couverture : code de retour 1 s'il n'est pas tenu |
| `composer lint` | style (PHP-CS-Fixer, sans rien modifier) puis analyse statique (PHPStan niveau 8) |
| `composer format` | corrige le style |
| `composer mutation` | tests de mutation (Infection), rapport dans `reports/infection.html` |
| `composer sast` | analyse de sécurité du code (Psalm, *taint analysis*) — Atelier 11 |
| `composer audit` | vulnérabilités connues des dépendances — Atelier 11 |

Tests boîte noire (Ateliers 8 et 9), depuis `boite-noire/` après un `composer install` dans ce dossier,
application lancée (`docker compose up -d --build`) :

| Commande | Effet |
|---|---|
| `composer api` | tests d'API par HTTP (Guzzle) contre `MINISHOP_URL`, `http://localhost:8000` par défaut |
| `composer e2e` | tests de bout en bout (Symfony Panther) ; demande Chrome/Chromium, chromedriver et l'extension `zip` |
| `composer selenium` | tests Selenium de l'Atelier 8, partie B (dossier vide au départ) |

Les outils s'appellent aussi directement : `vendor/bin/phpunit --filter testMoney`,
`vendor/bin/phpunit --group unit`, `vendor/bin/phpunit --testdox`…

PHP-CS-Fixer affiche un avertissement quand il tourne sur une version de PHP plus récente que le minimum
du projet (8.3) : il est sans conséquence ici.

## Plan du dossier

```
declinaisons/php/
├── composer.json, composer.lock   dépendances et scripts (composer test, composer lint…)
├── Dockerfile, docker-compose.yml image de l'application (FrankenPHP + APCu), service `minishop` sur le port 8000
├── docker/                        Caddyfile (serveur) et php.ini de l'image
├── public/index.php               point d'entrée HTTP
├── resources/                     static/ (page web, reprise telle quelle), openapi.json, docs.html
├── phpunit.xml.dist               suites de tests (unit, api, generated) et périmètre de la couverture
├── .php-cs-fixer.dist.php         règles de style (PSR-12 + Symfony)
├── phpstan.neon.dist              analyse statique
├── infection.json5                tests de mutation
├── psalm.xml                      analyse de sécurité (Atelier 11)
├── src/
│   ├── Pricing.php                règles de prix : money, lineTotal, couponDiscount, shippingCost, quote
│   ├── Quote.php, Line.php        devis et lignes ; Quote::toArray() équivaut à as_dict()
│   ├── Catalog.php, Product.php   catalogue en mémoire
│   ├── UnknownProductException.php
│   └── Http/                      API HTTP (Slim 4)
│       ├── Application.php            routes et réponses JSON
│       ├── CartRequest.php            validation du corps JSON d'un panier (erreurs 422)
│       ├── ObserveMiddleware.php      métriques, logs, bug « slow »
│       ├── Metrics.php                compteurs et histogramme Prometheus
│       └── OrderRepository.php, InMemoryOrderRepository.php, ApcuOrderRepository.php
├── tests/
│   ├── Unit/PricingTest.php       3 tests d'exemple + TODO (Atelier 1)
│   ├── Api/ApiSmokeTest.php       2 tests de fumée en mémoire + TODO (Atelier 9) ; ApiTestCase.php : le « client »
│   └── Generated/                 tests générés par IA (Ateliers 3 et 4)
├── tools/coverage-check.php       seuil de couverture et tableau Markdown pour la CI
├── boite-noire/                   projet Composer séparé : tests par HTTP et navigateur contre l'application lancée
│   ├── composer.json, composer.lock, phpunit.xml.dist
│   └── tests/
│       ├── Api/ApiSmokeTest.php        2 tests de fumée par HTTP + TODO (Atelier 9, variante « serveur réel »)
│       ├── E2e/ParcoursAchatTest.php   test de la page d'accueil + TODO (Atelier 8)
│       └── Selenium/                   Atelier 8, partie B
└── ateliers/                      énoncés déclinés (1 à 4, 8, 9, 11) et autres-ateliers.md (5 à 12)
```

## Python du cours → équivalent ici

| Python du cours | Ici (PHP) |
|---|---|
| `pip`, `venv`, `requirements-dev.txt` | Composer : `composer.json` + `composer.lock`, dépendances dans `vendor/` (pas d'environnement à activer) |
| `pytest` | PHPUnit 12 : `composer test` ou `vendor/bin/phpunit` |
| fonction `test_…` + `assert` | méthode `test…()` d'une classe `…Test extends TestCase` + `self::assertSame(...)` |
| `@pytest.mark.parametrize` | `#[DataProvider('nomDeLaMethode')]` + méthode statique qui fournit les cas |
| `pytest.raises(ValueError, match=…)` | `$this->expectException(...)` et `$this->expectExceptionMessage(...)` **avant** l'appel |
| marqueurs (`pytest.mark.unit`, `-m unit`) | `#[Group('unit')]` et `--group unit` ; suites `--testsuite unit` / `generated` |
| `monkeypatch.setenv` | `putenv('NOM=valeur')`, à rétablir dans un `finally` |
| `coverage` / `pytest --cov` | Xdebug ou pcov + `--coverage-text`, `--coverage-html`, `--coverage-cobertura` |
| `--cov-branch` | `--path-coverage` (Xdebug uniquement) |
| `--cov-fail-under=85` | `php tools/coverage-check.php reports/cobertura.xml --min-lines=85` |
| `--junitxml=…` | `--log-junit …` |
| `ruff check` | `vendor/bin/phpstan analyse` (analyse statique) |
| Playwright (`pytest -m e2e`) | Symfony Panther (`composer e2e` dans `boite-noire/`) |
| FastAPI, `uvicorn` | Slim 4 (PSR-7 / PSR-15), FrankenPHP dans l'image, `composer serve` en développement |
| `TestClient` (`pytest -m api`) | `ApiTestCase` : requête PSR-7 passée à `$app->handle()` (`composer api`) |
| `httpx` contre le serveur réel | Guzzle (`composer api` dans `boite-noire/`) |
| pydantic (validation du corps) | `MiniShop\Http\CartRequest`, écrit à la main, mêmes erreurs 422 |
| `prometheus_client` | `promphp/prometheus_client_php`, stockage APCu |
| dictionnaire `_ORDERS` en mémoire | `OrderRepository` : APCu sur le serveur, tableau PHP dans les tests |
| Bandit, `pip-audit` | Psalm *taint analysis* (`composer sast`), `composer audit` |
| `ruff format --check` / `ruff format` | `vendor/bin/php-cs-fixer check --diff` / `fix` |
| `Decimal`, `ROUND_HALF_UP` | `Brick\Math\BigDecimal`, `RoundingMode::HalfUp` (bibliothèque `brick/math`, aucune extension requise) |
| `Decimal("0.13") == …` | comparaison de chaînes : `(string) $montant === '0.13'` (ou `$a->isEqualTo($b)`) |
| `ValueError` | `InvalidArgumentException` |
| `KeyError` (produit inconnu) | `MiniShop\UnknownProductException` (hérite d'`OutOfBoundsException`) |
| `dataclass` `Quote`, `as_dict()` | classe `Quote`, `toArray()` (et `json_encode($quote)`) |
| `mutation_score.py`, `mutmut` | Infection : `composer mutation` |
| `pytest -n auto` (xdist) | ParaTest (`brianium/paratest`), non installé : la suite dure quelques millisecondes |

Deux différences à connaître :
- `lineTotal()` reçoit une quantité non typée (`mixed`) pour que la règle « la quantité doit être un entier »
  reste vérifiable et testable (`"2"`, `2.0`, `true`, `null`) comme en Python.
- Les fonctions sont des méthodes statiques : `Pricing::money(...)`, `Pricing::quote(...)`, `Catalog::getProduct(...)`.
- `/metrics` n'expose pas les métriques `python_*` et `process_*` propres au client Python ; les valeurs
  s'écrivent `1` et non `1.0`.

## Sous Windows

Les commandes `composer …` et `php …` sont identiques en PowerShell. Ce qui change :

- Variable d'environnement (bug d'arrondi injecté) :
  ```powershell
  $env:MINISHOP_BUG = "rounding"; composer test; Remove-Item Env:MINISHOP_BUG
  ```
  (`Remove-Item` est indispensable, sinon le bug reste actif dans ce terminal.)
- Rapport de couverture : `start reports/coverage/index.html`
- Appel direct d'un outil : `vendor\bin\phpunit` (Composer y dépose un lanceur `.bat`).
- Variante Docker : `docker run --rm -v "${PWD}:/app" -w /app composer:2 sh -c "composer install && composer test"`
