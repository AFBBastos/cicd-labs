# Atelier 1 — Tests unitaires avec xUnit (1 h 15) — déclinaison C#

**Module 1** · Compétences C8 (TDD), C19 (Clean Code)

## Objectif
Écrire une suite de tests unitaires solide pour les règles de prix de MiniShop et mesurer la couverture.

## Contexte
Toutes les commandes se lancent depuis `declinaisons/csharp/`. Lisez l'en-tête de `src/MiniShop/Pricing.cs` :
il décrit les règles métier (remise volume, coupons, livraison, arrondi). Cet atelier ne porte que sur la
bibliothèque `MiniShop` ; l'API (`src/MiniShop.Api`) sera testée à l'Atelier 9. Le fichier
`tests/MiniShop.Tests/PricingTests.cs` contient 3 tests d'exemple et une liste de TODO.

## Étapes

### 1. Échauffement (10 min)
```bash
dotnet tool restore                    # une fois : reportgenerator et Stryker (dotnet-tools.json)
dotnet test --filter "Category=unit" --logger "console;verbosity=normal"
dotnet test tests/MiniShop.Tests --collect:"XPlat Code Coverage" --results-directory reports/tests
dotnet reportgenerator "-reports:reports/tests/*/coverage.cobertura.xml" -targetdir:reports/coverage "-reporttypes:Html;TextSummary"
```
Lisez `reports/coverage/Summary.txt` et notez la couverture de départ de `MiniShop.Pricing`. Ouvrez
`reports/coverage/index.html` : quelles lignes ne sont jamais exécutées ?

La mesure désigne le projet `tests/MiniShop.Tests` pour ne compter que la bibliothèque `MiniShop` (sans ce
chemin, le rapport inclut aussi l'API). Chaque exécution avec `--collect` écrit un nouveau sous-dossier dans
`reports/tests/` et le rapport les fusionne tous : supprimez `reports/` avant de mesurer à nouveau.

### 2. Tests paramétrés (25 min)
Complétez les TODO. Utilisez `[Theory]` et `[InlineData]` pour éviter le copier-coller :
```csharp
[Theory]
[InlineData(0)]
[InlineData(-1)]
[InlineData(100)]
public void Quantite_invalide(int qty)
{
    Assert.Throws<ArgumentOutOfRangeException>(() => Pricing.LineTotal(10m, qty));
}
```
Deux différences avec l'énoncé Python :
- La quantité est typée `int`. Les cas `"2"` et `True` de la version Python ne compilent pas : le compilateur
  joue ici le rôle de ces tests. Gardez les bornes 0, -1 et 100 (et les bornes valides 1 et 99).
- Un `decimal` n'est pas une constante d'attribut : `[InlineData(0.125m)]` ne compile pas. Passez des chaînes
  et convertissez-les avec `decimal.Parse(valeur, CultureInfo.InvariantCulture)`.

Pensez **valeurs limites** : 9 vs 10 unités, 19,99 € vs 20 € pour WELCOME10, 49,99 € vs 50 € pour la livraison.

Le piège de la virgule : sur un poste réglé en français, `27.40m.ToString()` donne `27,40` et
`decimal.Parse("27.40")` échoue ou se trompe. Précisez toujours `CultureInfo.InvariantCulture` quand un
montant devient une chaîne ou l'inverse. `Quote.AsDictionary()` le fait : écrivez un test qui le prouve en
forçant `CultureInfo.CurrentCulture = new CultureInfo("fr-FR")` (et en restaurant la culture ensuite).

### 3. Un petit cycle TDD (20 min)
Nouvelle règle demandée par le métier :
> Coupon `STUDENT15` : -15 % sur le sous-total, sans minimum, **non cumulable** avec la remise volume
> (si une ligne a la remise volume, le coupon ne s'applique pas à cette ligne).

1. **Rouge** : écrivez d'abord 3 tests qui échouent.
2. **Vert** : implémentez le minimum dans `Pricing.cs`.
3. **Refactor** : nettoyez sans casser les tests.

### 4. Couverture et qualité (15 min)
```bash
dotnet test tests/MiniShop.Tests --collect:"XPlat Code Coverage" --results-directory reports/tests
dotnet reportgenerator "-reports:reports/tests/*/coverage.cobertura.xml" -targetdir:reports/coverage "-reporttypes:Html;TextSummary"
```
Ouvrez `reports/coverage/index.html` dans le navigateur (`open` sous macOS, `xdg-open` sous Linux, `start` sous Windows).
Objectif : **≥ 90 % de couverture de branches** sur `MiniShop.Pricing`.
Question : 100 % de couverture garantit-il l'absence de bug ? Testez :
```bash
MINISHOP_BUG=rounding dotnet test --filter "Category=unit"
```
Vos tests détectent-ils le bug d'arrondi injecté ?

Pour l'écrire noir sur blanc, ajoutez un test qui positionne lui-même la variable
(`Environment.SetEnvironmentVariable("MINISHOP_BUG", "rounding")`), vérifie que `Money(0.125m)` ne vaut plus
`0.13`, puis **restaure** l'ancienne valeur dans un `finally`. Attention : une variable d'environnement est
globale au processus, et xUnit exécute en parallèle les classes de tests différentes. Le fichier
`tests/MiniShop.Tests/xunit.runner.json` désactive ce parallélisme pour que ce test ne perturbe pas les autres.

## Critères de réussite
- [ ] ≥ 15 tests, dont au moins 3 paramétrés (`[Theory]`)
- [ ] Couverture branches ≥ 90 % sur `MiniShop.Pricing`
- [ ] La suite échoue avec `MINISHOP_BUG=rounding`
- [ ] STUDENT15 implémenté en TDD (historique Git : commit des tests AVANT le code)

## Pour aller plus loin
- Tests de propriétés avec **FsCheck** (`FsCheck.Xunit`) : « le total n'est jamais négatif », « ajouter un
  article ne baisse jamais le sous-total ».
- Tests de mutation : `dotnet stryker` (on y reviendra à l'Atelier 3) ; `stryker-config.json` limite les
  mutations à la bibliothèque `MiniShop`.

## Sous Windows

Poste sous **WSL2** : rien à adapter. En **PowerShell**, voir aussi les règles générales de l'Atelier 0.

- Les commandes `dotnet` sont identiques (gardez les guillemets autour de `-reports:…` et `-reporttypes:…`).
- Rapport de couverture : `start reports/coverage/index.html` ; remise à zéro : `Remove-Item -Recurse reports`
- Bug d'arrondi injecté :
  ```powershell
  $env:MINISHOP_BUG = "rounding"; dotnet test --filter "Category=unit"
  Remove-Item Env:MINISHOP_BUG      # indispensable, sinon le bug reste actif dans ce terminal
  ```
