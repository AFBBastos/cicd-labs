# Atelier 9 — Tests d'API (2 h) — déclinaison C#

**Module 3** · Tests API avec Postman, RestAssured (et xUnit)

## Objectif
Tester l'API MiniShop à trois niveaux : tests en code (xUnit + `WebApplicationFactory`), collection Postman exécutée en CI
(Newman), et tests de contrat / propriétés générés depuis le schéma OpenAPI.

## Partie A — xUnit + WebApplicationFactory (50 min)
Depuis `declinaisons/csharp/`, complétez `tests/MiniShop.Api.Tests/ApiSmokeTests.cs` (ou créez `ApiTests.cs`
à côté), puis `dotnet test --filter "Category=api"` :
- `/products/{id}` : 200 et 404 ;
- `/cart/quote` : 200 (vérifier le total), 404 produit inconnu, 422 quantité 0 / 100 / coupon inconnu / corps invalide ;
- `/orders` : 201 puis `GET /orders/{id}` renvoie la même commande ; 422 panier vide ;
- `/metrics` expose `minishop_http_requests_total`.

`WebApplicationFactory<Program>` démarre l'application **en mémoire**, dans le processus de test : rapide, pas
de serveur à lancer, pas de port. C'est l'équivalent du `TestClient` de FastAPI ; `factory.CreateClient()`
rend un `HttpClient` ordinaire.

Repères :
```csharp
using var response = await _client.PostAsJsonAsync("/cart/quote", new
{
    items = new[] { new { product_id = "mug", qty = 2 } },
    coupon = "WELCOME10",
});
Assert.Equal(HttpStatusCode.OK, response.StatusCode);
var json = await response.Content.ReadFromJsonAsync<JsonElement>();
```
- 422 se nomme `HttpStatusCode.UnprocessableEntity`.
- Pour un corps volontairement invalide, envoyez du JSON brut :
  `new StringContent("""{"items":"pas une liste"}""", Encoding.UTF8, "application/json")`.
- Les montants sont des **chaînes** dans les réponses (`"27.40"`) : comparez des chaînes, ne repassez pas par un `double`.
- Cas d'erreur en série : `[Theory]` + `[InlineData(corps, statut)]`.
- Mesurez la couverture de l'API (commandes de l'Atelier 2, étape 4) : quelles branches de `Program.cs` et de
  `BodyIssue.cs` vos tests n'atteignent-ils pas ? Étendez ensuite les seuils du pipeline à tout le code : dans
  `ci-csharp.yml`, retirez `"-assemblyfilters:+MiniShop"`. Les seuils (85 % des lignes, 90 % des branches)
  demandent alors de tester aussi la validation du corps et les réponses d'erreur.
- Tous les tests d'une classe partagent la même application (`IClassFixture`) : les commandes créées et les
  compteurs de `/metrics` survivent d'un test à l'autre.

Variante « serveur réel » : les mêmes tests avec un `HttpClient` pointé sur l'application lancée
(`docker compose up -d --build` depuis `declinaisons/csharp/`, ou `dotnet run --project src/MiniShop.Api`).
Le point de départ est `tests/MiniShop.Acceptance.Tests/ApiSmokeTests.cs`, dans le projet hors solution de
l'Atelier 8 ; il se lance depuis ce dossier (`dotnet test --filter "Category=api"`) et lit l'adresse dans
`BASE_URL` (défaut : `http://localhost:8000`). Qu'apporte chaque variante ? Laquelle mettre dans le pipeline
de l'Atelier 2, laquelle après un déploiement ?

## Partie B — Test de contrat (20 min)
Écrivez un test qui échoue si une route publique disparaît ou si un champ de réponse change de type
(lisez `/openapi.json` avec `_client.GetFromJsonAsync<JsonElement>(…)`, parcourez `paths` ; le type d'un champ
se lit avec `JsonElement.ValueKind`). Discussion : contrat **côté fournisseur** vs **côté consommateur** (Pact).

## Partie C — Postman / Newman (30 min)
Partie indépendante du langage, reprise telle quelle de l'énoncé d'origine : la collection du dépôt s'applique
sans modification à l'application C# lancée sur le port 8000. Commandes depuis la **racine** du dépôt.
1. Importez `tests/api/minishop.postman_collection.json` dans Postman, lancez-la.
2. Ajoutez 2 requêtes avec scripts de test (`pm.test(...)`), dont une qui enchaîne
   « créer une commande » → « la relire » (variable `pm.collectionVariables.set("orderId", ...)`).
3. En ligne de commande / CI :
   ```bash
   npx newman run tests/api/minishop.postman_collection.json --env-var baseUrl=http://localhost:8000 \
       -r cli,junit --reporter-junit-export reports/newman.xml
   ```

## Partie D — Tests générés depuis OpenAPI (20 min)
Partie indépendante du langage, reprise telle quelle (Schemathesis est un outil Python, déjà disponible
depuis l'Atelier 0 avec `pip`).
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

- Parties A et B : commandes `dotnet` identiques. Variante « serveur réel » sur une autre adresse :
  `$env:BASE_URL = "http://localhost:8000"; dotnet test --filter "Category=api"`.
- Parties C et D : voir la section « Sous Windows » de l'énoncé d'origine (`ateliers/atelier-09-tests-api.md`).
