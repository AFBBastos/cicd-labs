# Atelier 9 — Tests d'API (2 h) — déclinaison Java

**Module 3** · Tests API avec Postman, RestAssured (et pytest)

## Objectif
Tester l'API MiniShop à trois niveaux : tests en code (MockMvc, puis RestAssured), collection Postman
exécutée en CI (Newman), et tests de contrat / propriétés générés depuis le schéma OpenAPI.

## Partie A — MockMvc : l'API en mémoire (50 min)
Depuis `declinaisons/java/` :
```bash
mvn test -Dgroups=api
```
Complétez `src/test/java/fr/minishop/api/ApiSmokeTest.java` (ou créez `ApiTest.java` à côté) :
- `/products/{id}` : 200 et 404 ;
- `/cart/quote` : 200 (vérifier le total), 404 produit inconnu, 422 quantité 0 / 100 / coupon inconnu / corps invalide ;
- `/orders` : 201 puis `GET /orders/{id}` renvoie la même commande ; 422 panier vide ;
- `/metrics` expose `minishop_http_requests_total`.

```java
client.perform(post("/cart/quote").contentType(MediaType.APPLICATION_JSON)
        .content("{\"items\":[{\"product_id\":\"mug\",\"qty\":2}],\"coupon\":\"WELCOME10\"}"))
    .andExpect(status().isOk())
    .andExpect(jsonPath("$.total").value("27.40"));
```
`MockMvc` (avec `@SpringBootTest` et `@AutoConfigureMockMvc`) appelle l'application **en mémoire** : rapide,
pas de serveur à lancer, pas de port ouvert. C'est l'équivalent du `TestClient` de l'énoncé Python.
Pour relire un champ d'une réponse (l'identifiant d'une commande) : `JsonPath.read(corps, "$.id")`.

Variante « serveur réel » : les mêmes tests avec **RestAssured** contre l'application lancée dans Docker
(`docker compose up -d --build` depuis `declinaisons/java/`). Ils vivent dans le projet séparé `tests-app/` :
```bash
cd tests-app && mvn test -Dgroups=api        # adresse : -Dapp.url=…, sinon APP_URL, sinon http://localhost:8000
```
```java
given().contentType(ContentType.JSON)
    .body("{\"items\":[{\"product_id\":\"mug\",\"qty\":2}],\"coupon\":\"WELCOME10\"}")
.when().post("/cart/quote")
.then().statusCode(200).body("total", equalTo("27.40"));
```
Plus lents, dépendants d'un service lancé, et ils partagent son état (les commandes créées restent en
mémoire du serveur) — mais ils testent l'image réellement livrée. Quels tests mettre à quel niveau ?

## Partie B — Test de contrat (20 min)
Écrivez un test qui échoue si une route publique disparaît ou si un champ de réponse change de type
(lisez `/openapi.json` : `jsonPath("$.paths", hasKey("/cart/quote"))` avec MockMvc).
Discussion : contrat **côté fournisseur** vs **côté consommateur** (Pact).

## Partie C — Postman / Newman (30 min)
Identique à l'énoncé d'origine : cet outil ne dépend pas du langage. Application lancée
(`docker compose up -d --build` depuis `declinaisons/java/`) ; chemins relatifs à la **racine du dépôt**.
1. Importez `tests/api/minishop.postman_collection.json` dans Postman, lancez-la.
2. Ajoutez 2 requêtes avec scripts de test (`pm.test(...)`), dont une qui enchaîne
   « créer une commande » → « la relire » (variable `pm.collectionVariables.set("orderId", ...)`).
3. En ligne de commande / CI :
   ```bash
   npx newman run tests/api/minishop.postman_collection.json --env-var baseUrl=http://localhost:8000 \
       -r cli,junit --reporter-junit-export reports/newman.xml
   ```

## Partie D — Tests générés depuis OpenAPI (20 min)
Identique à l'énoncé d'origine (Schemathesis est un outil Python, déjà disponible depuis l'Atelier 0) :
```bash
pip install schemathesis
schemathesis run http://localhost:8000/openapi.json --checks all
```
Schemathesis génère des centaines de requêtes (propriétés, cas limites). Trouve-t-il des réponses 500 ?
Lien avec le Module 2 : c'est de la génération de tests **à partir d'une spécification**, sans LLM.

## Critères de réussite
- [ ] ≥ 12 tests d'API, codes d'erreur compris
- [ ] Test de contrat en place
- [ ] Collection Postman exécutée par Newman avec rapport JUnit
- [ ] Schemathesis lancé, résultats analysés

## Sous Windows

Poste sous **WSL2** : rien à adapter. En **PowerShell**, voir aussi les règles générales de l'Atelier 0.

- Parties A et B : `mvn test "-Dgroups=api"` ; pour la variante « serveur réel », adresse de l'application :
  `$env:APP_URL = "http://localhost:8000"`.
- Partie C : `npx` demande Node.js (`winget install OpenJS.NodeJS.LTS`, puis rouvrez le terminal).
  La commande s'écrit sur une seule ligne :
  ```powershell
  npx newman run tests/api/minishop.postman_collection.json --env-var baseUrl=http://localhost:8000 -r cli,junit --reporter-junit-export reports/newman.xml
  ```
- Partie D : commande identique.
