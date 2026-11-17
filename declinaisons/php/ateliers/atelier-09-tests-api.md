# Atelier 9 — Tests d'API (2 h) — déclinaison PHP

**Module 3** · Tests API avec Postman, RestAssured (et PHPUnit)

## Objectif
Tester l'API MiniShop à trois niveaux : tests en code (PHPUnit), collection Postman exécutée en CI
(Newman), et tests de contrat / propriétés générés depuis le schéma OpenAPI.

## Préparation
L'API testée est celle de ce dossier (`src/Http/`, Slim 4). Depuis `declinaisons/php/` :
```bash
composer api                 # les 2 tests de fumée fournis, en mémoire
```
Pour les parties C et D (et la variante « serveur réel »), lancez l'application :
`docker compose up -d --build` depuis `declinaisons/php/`, puis http://localhost:8000.

## Partie A — PHPUnit, en mémoire (50 min)
Complétez `tests/Api/ApiSmokeTest.php` (ou créez `tests/Api/ApiTest.php`) :
- `/products/{id}` : 200 et 404 ;
- `/cart/quote` : 200 (vérifier le total), 404 produit inconnu, 422 quantité 0 / 100 / coupon inconnu / corps invalide ;
- `/orders` : 201 puis `GET /orders/{id}` renvoie la même commande ; 422 panier vide ;
- `/metrics` expose `minishop_http_requests_total`.

Un appel avec corps JSON :
```php
$response = $this->post('/cart/quote', [
    'items' => [['product_id' => 'mug', 'qty' => 2]],
    'coupon' => 'WELCOME10',
]);
self::assertSame(200, $response->getStatusCode());
self::assertSame('27.40', self::json($response)['total']);
```
Regroupez les cas d'erreur de `/cart/quote` dans un `#[DataProvider]`.

Étendez maintenant le seuil du pipeline à tout le code : dans `ci-php.yml`, retirez `--file=Pricing.php` de
l'étape « Seuil de couverture » (il reste `--min-lines=85`).
En PHP, la validation du corps est écrite à la main (`src/Http/CartRequest.php`) : pour tenir ce seuil de 85 %,
testez-la aussi — corps vide, JSON illisible, champ absent, mauvais type — ainsi que les
routes annexes (`/`, `/static/…`, route inconnue). `composer coverage` ne mesure que la suite unitaire ; la
commande du pipeline, `vendor/bin/phpunit --testsuite unit,api --coverage-text`, mesure les deux.

La classe `ApiTestCase` (dans `tests/Api/`) joue le rôle du `TestClient` de l'énoncé Python : `get()` et
`post()` construisent une requête PSR-7 et la passent directement à l'application (`$app->handle()`).
L'application est appelée **en mémoire** : rapide, pas de serveur à lancer, et chaque test repart d'une
application neuve (aucune commande, métriques à zéro).

Variante « serveur réel » : les mêmes tests par HTTP, avec Guzzle, contre l'application lancée dans Docker.
Le projet `boite-noire/` en contient le point de départ :
```bash
cd boite-noire && composer install
composer api                 # MINISHOP_URL, http://localhost:8000 par défaut
```
Le client Guzzle y est créé avec `'http_errors' => false` : un 404 ou un 422 est une réponse à vérifier, pas
une exception. Les commandes créées restent dans l'application tant que le conteneur tourne : ces tests ne
doivent pas en dépendre. Que détecte cette variante que les tests en mémoire ne voient pas ?

## Partie B — Test de contrat (20 min)
Écrivez un test qui échoue si une route publique disparaît ou si un champ de réponse change de type
(lisez `/openapi.json`). Discussion : contrat **côté fournisseur** vs **côté consommateur** (Pact).

## Partie C — Postman / Newman (30 min)
Partie indépendante du langage, **identique à l'énoncé d'origine** (commandes depuis la racine du dépôt) :
la collection fournie passe telle quelle sur l'application PHP.
1. Importez `tests/api/minishop.postman_collection.json` dans Postman, lancez-la.
2. Ajoutez 2 requêtes avec scripts de test (`pm.test(...)`), dont une qui enchaîne
   « créer une commande » → « la relire » (variable `pm.collectionVariables.set("orderId", ...)`).
3. En ligne de commande / CI :
   ```bash
   npx newman run tests/api/minishop.postman_collection.json --env-var baseUrl=http://localhost:8000 \
       -r cli,junit --reporter-junit-export reports/newman.xml
   ```

## Partie D — Tests générés depuis OpenAPI (20 min)
Partie **identique à l'énoncé d'origine** : Schemathesis est un outil en ligne de commande (installé avec
l'environnement Python de l'Atelier 0), il teste l'API quel que soit le langage de vos tests.
```bash
pip install schemathesis
schemathesis run http://localhost:8000/openapi.json --checks all
```
Schemathesis génère des centaines de requêtes (propriétés, cas limites). Trouve-t-il des réponses 500 ?
Lien avec le Module 2 : c'est de la génération de tests **à partir d'une spécification**, sans LLM.

## RestAssured (Java) — pour information
Si votre équipe est en Java, l'équivalent de la partie A :
```java
given().contentType(JSON).body("{\"items\":[{\"product_id\":\"mug\",\"qty\":2}],\"coupon\":\"WELCOME10\"}")
.when().post("/cart/quote")
.then().statusCode(200).body("total", equalTo("27.40"));
```

## Critères de réussite
- [ ] ≥ 12 tests d'API, codes d'erreur compris
- [ ] Test de contrat en place
- [ ] Collection Postman exécutée par Newman avec rapport JUnit
- [ ] Schemathesis lancé, résultats analysés

## Sous Windows

Poste sous **WSL2** : rien à adapter. En **PowerShell** :

- Parties A, B et D : commandes identiques. Variante « serveur réel » sur une autre adresse :
  `$env:MINISHOP_URL = "http://localhost:8000"; composer api`
- Partie C : `npx` demande Node.js (`winget install OpenJS.NodeJS.LTS`, puis rouvrez le terminal).
  La commande s'écrit sur une seule ligne :
  ```powershell
  npx newman run tests/api/minishop.postman_collection.json --env-var baseUrl=http://localhost:8000 -r cli,junit --reporter-junit-export reports/newman.xml
  ```
