# Atelier 8 — Tests fonctionnels UI de bout en bout (2 h 30) — déclinaison C#

**Module 3** · Tests UI avec Selenium, Cypress (et Playwright)

## Objectif
Automatiser les parcours utilisateur de MiniShop, les rendre fiables, et les exécuter dans la CI
sur plusieurs navigateurs avec des traces exploitables en cas d'échec.

## Préparation
L'application testée est l'application C# de ce dossier, lancée depuis `declinaisons/csharp/` :
```bash
docker compose up -d --build        # http://localhost:8000   (ou : dotnet run --project src/MiniShop.Api)
```
Sa page web (`src/MiniShop.Api/wwwroot/static/index.html`) est la même que celle de l'application Python.

Les tests sont dans `tests/MiniShop.Acceptance.Tests/`, un projet **hors de la solution** `MiniShop.slnx` :
il a besoin d'une application lancée, la suite unitaire, la couverture, Stryker et le pipeline de l'Atelier 2
ne le voient donc pas. Les commandes `dotnet` de cet atelier se lancent depuis ce dossier de tests. L'adresse de
l'application se lit dans la variable d'environnement `BASE_URL` (défaut : `http://localhost:8000`).

Installation des navigateurs (une fois ; le script est produit par la compilation et demande PowerShell, `pwsh`) :
```bash
dotnet build
pwsh bin/Debug/net10.0/playwright.ps1 install chromium firefox
```

## Partie A — Playwright (75 min)

L'outil est **Microsoft.Playwright** (même moteur et mêmes notions que la version Python du cours), avec le
paquet `Microsoft.Playwright.Xunit` : en héritant de `PageTest`, chaque test reçoit une page neuve (`Page`).

1. Lancer le test fourni : `dotnet test --filter "Category=e2e"` (avec la variable d'environnement
   `HEADED=1` pour voir le navigateur).
2. Enregistrer un parcours pour démarrer vite :
   ```bash
   pwsh bin/Debug/net10.0/playwright.ps1 codegen http://localhost:8000
   ```
   Le code généré est un **brouillon** : réécrivez-le proprement.
3. Écrire dans `ParcoursAchatTests.cs` :
   - parcours d'achat : 2 mugs + WELCOME10 → total `27.40` → commande confirmée ;
   - coupon invalide → message d'erreur (`Page.GetByRole(AriaRole.Alert)`) ;
   - bouton « Commander » désactivé tant que le panier est vide.
4. Bonnes pratiques à appliquer :
   - localisateurs par **rôle / texte / data-testid** (`GetByRole`, `GetByText`, `GetByTestId`), jamais par
     XPath ou classe CSS ;
   - assertions **web-first** (`await Expect(...).ToHaveTextAsync(...)`) : pas de `Thread.Sleep` ni de `Task.Delay` ;
   - l'équivalent de la fixture `shop` : redéfinir `InitializeAsync()` (appeler `base.InitializeAsync()` puis
     ouvrir la page) ; tests **indépendants** entre eux.
5. Page Object (15 min) : extrayez une classe `ShopPage` (`AddAsync(product)`, `ApplyCouponAsync(code)`,
   `Total`, `OrderAsync()`). Les tests deviennent lisibles par le métier.

## Partie B — Selenium, pour comparer (35 min)
```bash
dotnet add package Selenium.WebDriver
dotnet add package Selenium.Support        # WebDriverWait
```
Écrivez `SeleniumAccueilTests.cs` (trait `[Trait("Category", "selenium")]`) qui vérifie le titre et ajoute un
produit au panier, avec `ChromeDriver` (Selenium Manager télécharge le navigateur et le driver tout seul ;
option `--headless=new` pour s'en passer d'écran). Notez ce qui vous a manqué par rapport à Playwright
(attentes explicites `WebDriverWait`, pas de traces…). Optionnel : la même chose en **Cypress** (JS).

`dotnet add package` met à jour `packages.lock.json` : commitez-le avec le `.csproj`.

## Partie C — Dans la CI (40 min)
Créez `.github/workflows/e2e-csharp.yml` (à la racine du dépôt) :
- `defaults: run: working-directory: declinaisons/csharp/tests/MiniShop.Acceptance.Tests` ;
- matrice `browser: [chromium, firefox]` ; le navigateur se choisit par la variable d'environnement
  `BROWSER: ${{ matrix.browser }}` sur l'étape de test, et s'installe par
  `pwsh bin/Debug/net10.0/playwright.ps1 install --with-deps ${{ matrix.browser }}` (après `dotnet build`) ;
- démarrer l'appli en arrière-plan depuis `declinaisons/csharp` (`working-directory:` sur l'étape) et
  **attendre** qu'elle réponde : `docker compose up -d --build` puis
  `timeout 30 bash -c 'until curl -sf localhost:8000/health; do sleep 1; done'` ;
- `dotnet test --no-build --filter "Category=e2e" --logger "junit;LogFileName=e2e-${{ matrix.browser }}.xml" --results-directory reports`
- traces : Playwright pour .NET n'a pas d'option `--tracing retain-on-failure`, cela s'écrit dans la classe
  de tests. Démarrez l'enregistrement dans `InitializeAsync()` (`Context.Tracing.StartAsync`), arrêtez-le
  dans `DisposeAsync()` (`Context.Tracing.StopAsync`) en ne donnant un chemin de fichier que si le test a
  échoué (propriété `TestOk` de `PageTest`). Le dossier courant d'un test est `bin/Debug/net10.0/`.
- artefact du dossier de traces **en cas d'échec** (`if: failure()`, chemin depuis la racine du dépôt) ;
  ouvrez une trace avec `pwsh bin/Debug/net10.0/playwright.ps1 show-trace trace.zip`
  (ou https://trace.playwright.dev).
- Parallélisation : xUnit exécute en parallèle les **classes** de tests — attention aux tests qui partagent
  des données (commandes).

Cassez volontairement l'interface (renommez un `data-testid` dans `index.html`) et diagnostiquez **uniquement** avec la trace.

## Critères de réussite
- [ ] 3 parcours E2E verts, sans aucun `sleep`
- [ ] Page Object en place
- [ ] Exécution CI sur 2 navigateurs, traces récupérables en cas d'échec
- [ ] Comparatif Selenium / Playwright (/ Cypress) en 5 lignes

## Pour aller plus loin
- Grilles cloud **BrowserStack / Sauce Labs** : mêmes tests, navigateurs et mobiles réels (essais gratuits).
- Tests d'accessibilité : paquet `Deque.AxeCore.Playwright`.

## Sous Windows

Les commandes `dotnet` et `pwsh` sont identiques en PowerShell. Ce qui diffère :

```powershell
$env:HEADED = "1"; dotnet test --filter "Category=e2e"; Remove-Item Env:HEADED
$env:BROWSER = "firefox"; dotnet test --filter "Category=e2e"; Remove-Item Env:BROWSER
```

Partie C : le workflow s'exécute sur un runner Ubuntu, gardez `--with-deps` (réservé à Linux) et la boucle
`timeout 30 bash -c '…'` tels quels dans le YAML.
