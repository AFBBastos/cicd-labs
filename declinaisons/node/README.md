# MiniShop — déclinaison Node.js

L'application MiniShop complète portée en JavaScript, pour suivre les ateliers sans écrire de Python :
règles de prix et catalogue, API HTTP (Fastify), page web, métriques Prometheus, logs JSON, image Docker.
Les règles, les valeurs, les routes et les messages d'erreur sont **identiques** à l'application Python
(`minishop/`) ; la spécification `specs/pricing.feature` est commune. Les deux applications sont
interchangeables : tout ce qui teste MiniShop de l'extérieur (tests E2E, collection Postman, JMeter,
Locust, ZAP, Prometheus, outils `ai_tools/`) fonctionne avec l'une comme avec l'autre.

## Prérequis

| Outil | Version | Remarque |
|---|---|---|
| Node.js | 20.19 minimum ; 22 ou 24 (LTS) conseillé | https://nodejs.org ; la CI teste les versions 20, 22 et 24 |
| npm | celui fourni avec Node.js (9, 10 ou 11) | pas de yarn ni de pnpm dans ce cours |
| Docker | — | image de l'application, job `docker` de la CI, outils des Ateliers 10 à 12 |

Vérifiez : `node -v`, `npm -v`.

Sans Node.js sur le poste, l'image officielle suffit :
```bash
docker run --rm -v "$PWD":/app -w /app node:22 sh -c "npm ci && npm run test:unit"
```

## Installation

Toutes les commandes se lancent depuis ce dossier :
```bash
cd declinaisons/node
npm ci          # installe exactement les versions figées dans package-lock.json, dans node_modules/
```

Utilisez bien `npm ci` (et non `npm install`) et ne supprimez pas `package-lock.json` : sans ce fichier,
npm 9 et npm 10 échouent sur Vitest 4.1 avec l'erreur `Cannot read properties of null (reading 'edgesOut')`.
Pour ajouter un paquet ensuite, `npm install -D <paquet>` fonctionne normalement.

## Lancer l'application

```bash
npm start                         # http://localhost:8000  —  API : http://localhost:8000/docs
npm run dev                       # idem, avec redémarrage à chaque sauvegarde
docker compose up -d --build      # ou dans Docker, depuis ce dossier (même port 8000)
```
Arrêtez l'application Python si elle tourne : les deux écoutent sur le port 8000 (autre port : `PORT=8001 npm start`).

| Route | Rôle |
|---|---|
| `GET /` , `/static/*` | page web de la boutique (`src/static/`, identique à celle de l'application Python) |
| `GET /health` | état et version |
| `GET /products`, `GET /products/{product_id}` | catalogue |
| `POST /cart/quote` | devis d'un panier `{"items":[{"product_id":"mug","qty":2}],"coupon":"WELCOME10"}` |
| `POST /orders`, `GET /orders/{order_id}` | commandes (en mémoire) |
| `GET /metrics` | métriques Prometheus (`minishop_http_requests_total`, `minishop_http_request_duration_seconds`, `minishop_orders_total`) ; l'étiquette `path` est le gabarit de la route (`/products/{product_id}`), ou `(route inconnue)` pour une URL sans route |
| `GET /openapi.json`, `/docs` | contrat OpenAPI généré depuis les schémas des routes, et sa page Swagger UI |

| Variable d'environnement | Effet |
|---|---|
| `MINISHOP_BUG=rounding` | arrondi bancaire au lieu de commercial (0,125 → 0,12) |
| `MINISHOP_BUG=slow` | 300 à 800 ms de latence sur `/cart/*` |
| `MINISHOP_LOG_FILE=logs/app.jsonl` | une ligne JSON par requête (lue par `ai_tools/log_anomalies.py`) |
| `PORT` | port d'écoute (défaut : 8000) |
| `MINISHOP_URL` | adresse visée par les tests boîte noire (défaut : `http://localhost:8000`) |

## Commandes

| Commande | Effet |
|---|---|
| `npm run test:unit` | tests unitaires (Vitest, dossier `tests/unit`) |
| `npm test` | tests unitaires, tests d'API en mémoire et tests générés (`tests/unit`, `tests/api`, `tests/generated`) : aucun serveur à lancer |
| `npm run test:api` | tests d'API **en mémoire** (`tests/api`, `app.inject()`), l'équivalent de `pytest -m api` |
| `npm run test:watch` | relance les tests à chaque sauvegarde (pratique en TDD) |
| `npm run coverage` | tests unitaires et d'API + couverture : tableau à l'écran, HTML dans `coverage/index.html`, Cobertura dans `coverage/cobertura-coverage.xml`, tableau texte dans `coverage/coverage.txt` |
| `npm run test:http` | tests d'API **par HTTP** (`tests/boite-noire`, Atelier 9) contre l'application lancée |
| `npm run test:e2e` | tests E2E (Playwright Test, `e2e/`, Atelier 8) dans Chromium, contre l'application lancée |
| `npm run lint` | analyse statique (ESLint) |
| `npm run lint:security` | analyse de sécurité de `src/` (`eslint-plugin-security`, Atelier 11) |
| `npm run format:check` | vérifie le style (Prettier) sans rien modifier |
| `npm run format` | corrige le style |
| `npm run mutation` | tests de mutation (Stryker) avec `tests/unit`, rapport dans `reports/mutation/unit.html` |
| `npm run mutation:generated` | idem avec `tests/generated`, rapport dans `reports/mutation/generated.html` |

Les outils s'appellent aussi directement avec `npx` :
```bash
npx vitest run tests/unit --reporter=verbose          # un test par ligne
npx vitest run -t "panier vide"                       # filtre sur le nom du test
npx vitest run tests/unit --reporter=default --reporter=junit --outputFile.junit=reports/junit.xml
```
Pour passer une option à un script npm, intercalez `--` : `npm run test:unit -- --reporter=verbose`.

Les tests boîte noire (`tests/boite-noire/`, `e2e/`) visent une application **lancée** (`npm start` ou Docker) ;
ils lisent son adresse dans la variable `MINISHOP_URL` (défaut : `http://localhost:8000`). Ils sont rangés à
part : ni `npm test`, ni la couverture, ni les tests de mutation, ni le pipeline `ci-node.yml` ne les lancent. Les tests E2E demandent en plus les navigateurs : `npx playwright install --with-deps chromium`
(Windows / macOS : sans `--with-deps`).

## Plan du dossier

```
declinaisons/node/
├── package.json, package-lock.json   dépendances et scripts (npm start, npm run test:unit, npm run lint…)
├── Dockerfile, .dockerignore         image de l'application (utilisateur non root, HEALTHCHECK)
├── docker-compose.yml                service minishop sur le port 8000
├── vitest.config.js                  fichiers de test, périmètre et formats de la couverture
├── eslint.config.js                  règles ESLint (configuration « plate »)
├── .prettierrc.json, .prettierignore style du code
├── eslint.security.config.js         règles de sécurité (Atelier 11)
├── playwright.config.js              tests E2E : dossier, adresse de l'application, navigateurs (Atelier 8)
├── stryker.config.json               tests de mutation avec tests/unit
├── stryker.generated.config.json     tests de mutation avec tests/generated
├── src/
│   ├── pricing.js                    règles de prix : money, lineTotal, couponDiscount, shippingCost, quote, Quote
│   ├── catalog.js                    catalogue en mémoire : listProducts, getProduct, UnknownProductError
│   ├── app.js                        API HTTP : buildApp() (routes, schémas, métriques, logs, bugs injectables)
│   ├── server.js                     point d'entrée : écoute sur le port 8000
│   └── static/                       page web (index.html, style.css)
├── tests/
│   ├── unit/pricing.test.js          3 tests d'exemple + TODO (Atelier 1)
│   ├── generated/                    tests générés par IA (Ateliers 3 et 4)
│   ├── api/api.test.js               tests d'API en mémoire : 2 tests de fumée + TODO (Ateliers 2 et 9)
│   └── boite-noire/api.test.js       tests d'API par HTTP : 2 tests de fumée + TODO (Atelier 9)
├── e2e/parcours-achat.spec.js        test E2E de la page d'accueil + TODO (Atelier 8)
└── ateliers/                         énoncés déclinés (1 à 4, 8, 9, 11) et autres-ateliers.md (5, 6, 7, 10, 12)
```

## Les montants : pourquoi `decimal.js` ?

JavaScript n'a pas de type décimal : `number` est un flottant binaire (IEEE 754).
```bash
node -e "console.log(0.1 + 0.2)"                 # 0.30000000000000004
node -e "console.log((1.005).toFixed(2))"        # 1.00 et non 1.01
```
Tous les montants sont donc des objets `Decimal` de la bibliothèque `decimal.js` (l'équivalent du
`Decimal` de Python). Trois réflexes :
- construire depuis une **chaîne** : `new Decimal('12.50')`, jamais `new Decimal(12.5 * 3)` ;
- calculer avec les **méthodes** (`plus`, `minus`, `times`, `greaterThanOrEqualTo`…) : les opérateurs
  `+`, `*`, `>=` ne fonctionnent pas sur des objets ;
- comparer dans les tests avec `toEqual` : `expect(money('0.125')).toEqual(new Decimal('0.13'))`
  (`toBe` compare les références et échouerait).

Un montant sérialisé reste une chaîne à 2 décimales : `total.toFixed(2)` donne `'27.40'`, et
`JSON.stringify(quote(...))` appelle `Quote.toJSON()`, l'équivalent de `as_dict()`.

## Python du cours → équivalent ici

| Python du cours | Ici (Node.js) |
|---|---|
| `pip`, `venv`, `requirements-dev.txt` | npm : `package.json` + `package-lock.json`, dépendances dans `node_modules/` (pas d'environnement à activer) ; `npm ci` |
| `pytest` | Vitest 4 : `npm run test:unit` ou `npx vitest run` |
| fonction `test_…` + `assert` | `test('nom', () => { expect(valeur).toEqual(attendu); })`, regroupés par `describe('…', () => { … })` |
| `@pytest.mark.parametrize` | `test.each([...])('nom %s', (a, b) => { … })` |
| `pytest.raises(ValueError, match=...)` | `expect(() => f()).toThrow(RangeError)` et `expect(() => f()).toThrow('message')` |
| marqueurs `-m unit`, `-m generated` | pas de marqueurs : un **dossier** par famille (`npx vitest run tests/unit`, `npx vitest run tests/generated`) ou un **filtre sur le nom** (`npx vitest run -t "unit"`, le nom complet inclut ceux des `describe`) |
| `monkeypatch.setenv` | `vi.stubEnv('MINISHOP_BUG', 'rounding')` (restauré après chaque test : `unstubEnvs` dans `vitest.config.js`) |
| `pytest -n auto` (xdist) | rien à ajouter : Vitest exécute déjà les **fichiers** de test en parallèle |
| `--junitxml=reports/junit.xml` | `--reporter=default --reporter=junit --outputFile.junit=reports/junit.xml` |
| `pytest --cov --cov-branch` (coverage.py) | `npx vitest run --coverage` (`@vitest/coverage-v8`) ; la colonne `% Branch` est toujours calculée |
| `--cov-fail-under=85` | `coverage.thresholds` dans `vitest.config.js` (seuil global ou par fichier) |
| `htmlcov/index.html`, `coverage.xml` | `coverage/index.html`, `coverage/cobertura-coverage.xml` |
| `coverage report --format=markdown` | `coverage/coverage.txt` (tableau texte, à placer dans un bloc de code Markdown) |
| `ruff check` | ESLint 10 : `npm run lint` |
| `ruff format --check` / `ruff format` | Prettier 3 : `npm run format:check` / `npm run format` |
| `Decimal`, `quantize(CENT, ROUND_HALF_UP)` | `decimal.js` : `new Decimal('0.125').toDecimalPlaces(2, Decimal.ROUND_HALF_UP)` |
| `str(montant)` | `montant.toFixed(2)` |
| `ValueError` (quantité non entière) | `TypeError` — message « La quantité doit être un entier » |
| `ValueError` (quantité hors limites, coupon inconnu) | `RangeError` — messages « Quantité hors limites (1..99) : … », « Coupon inconnu : … » |
| `KeyError` (produit inconnu) | `UnknownProductError` (classe de `src/catalog.js`) — message « Produit inconnu : … » |
| `Quote.as_dict()` | `Quote.toJSON()` (appelée par `JSON.stringify`) |
| `line_total`, `coupon_discount`, `shipping_cost` | `lineTotal`, `couponDiscount`, `shippingCost` (camelCase) |
| annotations de type | commentaires JSDoc (`@param`, `@returns`) : pas de TypeScript ici |
| `ai_tools/mutation_score.py` | Stryker : `npm run mutation` |
| `pytest -m e2e` (pytest-playwright) | Playwright Test : `npm run test:e2e` ou `npx playwright test` |
| `pytest -m api` (`TestClient`) | `app.inject()` de Fastify, sans serveur : `npm run test:api` |
| `httpx.Client(base_url=…)` contre le serveur réel | `fetch` + Vitest : `npm run test:http` |
| FastAPI, pydantic, `uvicorn minishop.api:app --reload` | Fastify et schémas JSON (`src/app.js`), `npm run dev` |
| `prometheus_client` | `prom-client` |
| `make run` | `npm start` |
| Bandit, `ruff --select S` | `eslint-plugin-security` : `npm run lint:security` |
| pip-audit | `npm audit` |
| Hypothesis | fast-check |

Deux différences à connaître, dues au langage :
- JavaScript ne distingue pas `2` de `2.0` (c'est le même nombre) : le cas `2.0` des tests Python devient
  `2.5`. Les quantités `'2'`, `true`, `null`, `undefined` et `NaN` sont refusées (`Number.isInteger`).
- Les clés des paniers et du devis gardent les noms de l'API (`product_id`, `qty`, `unit_price`) pour que
  le JSON soit le même dans tous les langages.

## Sous Windows

Poste sous **WSL2** : rien à adapter. En **PowerShell**, les commandes `npm` et `npx` sont identiques ; seules
les variables d'environnement s'écrivent autrement :
```powershell
$env:MINISHOP_BUG = "rounding"; npx vitest run tests/unit; Remove-Item Env:MINISHOP_BUG
```
(`Remove-Item` est indispensable, sinon le bug reste actif dans ce terminal.)

- Rapport de couverture : `start coverage/index.html`
- Si PowerShell refuse `npm` ou `npx` (« l'exécution de scripts est désactivée »), utilisez `npm.cmd` et
  `npx.cmd`, ou autorisez les scripts : `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
- Installation de Node.js : `winget install OpenJS.NodeJS.LTS`, puis rouvrez le terminal.
