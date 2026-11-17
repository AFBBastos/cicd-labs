# Atelier 9 — Tests d'API (2 h) — déclinaison Node.js

**Module 3** · Tests API avec Postman, RestAssured (et Vitest)

## Objectif
Tester l'API MiniShop à trois niveaux : tests en code (Vitest), collection Postman exécutée en CI
(Newman), et tests de contrat / propriétés générés depuis le schéma OpenAPI.

## Partie A — Vitest + app.inject() (50 min)
Complétez `tests/api/api.test.js` (2 tests de fumée fournis, `npm run test:api`) :
- `/products/{id}` : 200 et 404 ;
- `/cart/quote` : 200 (vérifier le total), 404 produit inconnu, 422 quantité 0 / 100 / coupon inconnu / corps invalide ;
- `/orders` : 201 puis `GET /orders/{id}` renvoie la même commande ; 422 panier vide ;
- `/metrics` expose `minishop_http_requests_total`.

`app.inject()` (Fastify) appelle l'application **en mémoire** : rapide, pas de serveur à lancer, pas de port
à réserver. C'est l'équivalent du `TestClient` de l'énoncé Python :
```js
const res = await app.inject({
  method: 'POST',
  url: '/cart/quote',
  payload: { items: [{ product_id: 'mug', qty: 2 }], coupon: 'WELCOME10' },
});
expect(res.statusCode).toBe(200);
expect(res.json().total).toBe('27.40');
```
Les cas d'erreur de `/cart/quote` se prêtent à `test.each`. Ces tests font partie de `npm test` et du
pipeline `ci-node.yml`, et comptent dans la couverture de `src/app.js`.

Variante « serveur réel » : les mêmes tests avec `fetch` contre l'application lancée (`npm start` ou
Docker), dans `tests/boite-noire/api.test.js` (2 tests de fumée fournis, `npm run test:http`) :
```js
const res = await fetch(`${APP_URL}/cart/quote`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ items: [{ product_id: 'mug', qty: 2 }], coupon: 'WELCOME10' }),
});
expect(res.status).toBe(200);
```
`fetch` ne lève pas d'exception sur un 404 ou un 422 ; l'adresse se lit dans `MINISHOP_URL` (défaut
`http://localhost:8000`) — pas `BASE_URL`, que Vitest réserve. Que détecte la variante « serveur réel »
que la variante en mémoire ne voit pas (image Docker, port, en-têtes) ? Et l'inverse ?

## Partie B — Test de contrat (20 min)
Écrivez un test qui échoue si une route publique disparaît ou si un champ de réponse change de type
(lisez `/openapi.json`). Discussion : contrat **côté fournisseur** vs **côté consommateur** (Pact).

## Partie C — Postman / Newman (30 min)
Partie identique à l'énoncé d'origine (Newman est déjà un outil Node.js). L'application de ce dossier doit
tourner (`npm start`) ; les commandes se lancent depuis la **racine du dépôt**, où se trouve la collection.
1. Importez `tests/api/minishop.postman_collection.json` dans Postman, lancez-la.
2. Ajoutez 2 requêtes avec scripts de test (`pm.test(...)`), dont une qui enchaîne
   « créer une commande » → « la relire » (variable `pm.collectionVariables.set("orderId", ...)`).
3. En ligne de commande / CI :
   ```bash
   npx newman run tests/api/minishop.postman_collection.json --env-var baseUrl=http://localhost:8000 \
       -r cli,junit --reporter-junit-export reports/newman.xml
   ```

## Partie D — Tests générés depuis OpenAPI (20 min)
Partie identique à l'énoncé d'origine : Schemathesis est un outil Python, il teste l'API de l'extérieur,
à partir du contrat `/openapi.json` que Fastify génère depuis les schémas des routes (`src/app.js`).
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

- Parties A, B et D : commandes identiques.
- Partie C : la commande s'écrit sur une seule ligne :
  ```powershell
  npx newman run tests/api/minishop.postman_collection.json --env-var baseUrl=http://localhost:8000 -r cli,junit --reporter-junit-export reports/newman.xml
  ```
