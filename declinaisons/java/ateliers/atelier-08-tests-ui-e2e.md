# Atelier 8 — Tests fonctionnels UI de bout en bout (2 h 30) — déclinaison Java

**Module 3** · Tests UI avec Selenium, Cypress (et Playwright)

## Objectif
Automatiser les parcours utilisateur de MiniShop, les rendre fiables, et les exécuter dans la CI
sur plusieurs navigateurs avec des traces exploitables en cas d'échec.

## Préparation
L'application testée est celle de ce dossier (Java), lancée dans Docker depuis `declinaisons/java/` :
```bash
docker compose up -d --build        # http://localhost:8000
```
(Si l'application de la racine du dépôt tourne déjà sur le port 8000, arrêtez-la d'abord : `docker compose down` à la racine.)

Les tests E2E vivent dans un projet Maven séparé, `declinaisons/java/tests-app/` : ils pilotent l'application
de l'extérieur et n'entrent ni dans la couverture ni dans les tests de mutation.
**Les commandes `mvn` de cet atelier se lancent depuis `tests-app/`.**

Installez les navigateurs une fois (`--with-deps` installe aussi les bibliothèques système : Linux et CI seulement) :
```bash
mvn test-compile exec:java -Dexec.mainClass=com.microsoft.playwright.CLI -Dexec.classpathScope=test \
    -Dexec.args="install --with-deps chromium firefox"
```
L'adresse de l'application se lit dans `-Dapp.url=…`, sinon dans la variable d'environnement `APP_URL`,
sinon `http://localhost:8000` (classe `AppUrl`).

## Partie A — Playwright for Java (75 min)

1. Lancer le test fourni : `mvn test -Dgroups=e2e -Dheaded=true -Dslowmo=300`
   (`ShopOptions.java` lit ces options ; `-Dbrowser=firefox` change de navigateur).
2. Enregistrer un parcours pour démarrer vite :
   ```bash
   mvn test-compile exec:java -Dexec.mainClass=com.microsoft.playwright.CLI -Dexec.classpathScope=test \
       -Dexec.args="codegen http://localhost:8000"
   ```
   Le code généré est un **brouillon** : réécrivez-le proprement.
3. Écrire dans `src/test/java/fr/minishop/app/e2e/ParcoursAchatTest.java` :
   - parcours d'achat : 2 mugs + WELCOME10 → total `27.40` → commande confirmée ;
   - coupon invalide → message d'erreur (`page.getByRole(AriaRole.ALERT)`) ;
   - bouton « Commander » désactivé tant que le panier est vide.
4. Bonnes pratiques à appliquer :
   - localisateurs par **rôle / texte / data-testid** (`getByRole`, `getByText`, `getByTestId`), jamais par XPath ou classe CSS ;
   - assertions **web-first** (`assertThat(locator).hasText(...)` de `PlaywrightAssertions`) : pas de `Thread.sleep` ;
   - une méthode `@BeforeEach` qui ouvre la page ; tests **indépendants** entre eux. Avec `@UsePlaywright`,
     chaque test reçoit une `Page` neuve en paramètre : c'est l'équivalent des fixtures de pytest.
5. Page Object (15 min) : extrayez une classe `ShopPage` (`add(product)`, `applyCoupon(code)`,
   `total()`, `order()`). Les tests deviennent lisibles par le métier.

## Partie B — Selenium, pour comparer (35 min)
Ajoutez la dépendance dans `tests-app/pom.xml` :
```xml
<dependency>
  <groupId>org.seleniumhq.selenium</groupId>
  <artifactId>selenium-java</artifactId>
  <version>4.52.0</version>
  <scope>test</scope>
</dependency>
```
Écrivez `src/test/java/fr/minishop/app/e2e/SeleniumAccueilTest.java` (étiquette `@Tag("selenium")`) qui vérifie
le titre et ajoute un produit au panier. Selenium Manager télécharge le navigateur et le driver tout seul :
```java
WebDriver driver = new ChromeDriver(new ChromeOptions().addArguments("--headless=new"));
driver.get(AppUrl.get());
```
Lancez-le avec `mvn test -Dgroups=selenium`. Notez ce qui vous a manqué par rapport à Playwright
(attentes explicites `WebDriverWait`, pas de traces…). Optionnel : la même chose en **Cypress** (JS).

## Partie C — Dans la CI (40 min)
Créez `.github/workflows/e2e-java.yml` (à la racine du dépôt), avec
`defaults.run.working-directory: declinaisons/java/tests-app` :
- matrice `browser: [chromium, firefox]` ; installation du navigateur avec la commande de la préparation
  (`-Dexec.args="install --with-deps ${{ matrix.browser }}"`) ;
- démarrer l'appli en arrière-plan (étape avec `working-directory: declinaisons/java`) et **attendre**
  qu'elle réponde : `docker compose up -d --build` puis
  `timeout 60 bash -c 'until curl -sf localhost:8000/health; do sleep 1; done'`
  (60 s plutôt que 30 : la JVM met une dizaine de secondes à démarrer) ;
- `mvn -B -ntp test -Dgroups=e2e -Dbrowser=${{ matrix.browser }}` ;
- `ShopOptions` conserve la trace des tests en échec dans `target/test-results/` : publiez
  `declinaisons/java/tests-app/target/test-results/` en artefact **en cas d'échec** (`if: failure()`) ;
  ouvrez `trace.zip` sur https://trace.playwright.dev (ou avec `-Dexec.args="show-trace trace.zip"`).
- Parallélisation : `-Djunit.jupiter.execution.parallel.enabled=true` — attention aux tests qui partagent
  des données (commandes).

Cassez volontairement l'interface (renommez un `data-testid` dans `src/main/resources/static/index.html`)
et diagnostiquez **uniquement** avec la trace.

## Critères de réussite
- [ ] 3 parcours E2E verts, sans aucun `sleep`
- [ ] Page Object en place
- [ ] Exécution CI sur 2 navigateurs, traces récupérables en cas d'échec
- [ ] Comparatif Selenium / Playwright (/ Cypress) en 5 lignes

## Pour aller plus loin
- Grilles cloud **BrowserStack / Sauce Labs** : mêmes tests, navigateurs et mobiles réels (essais gratuits).
- Tests d'accessibilité : `com.deque.html.axe-core:playwright`.

## Sous Windows

Poste sous **WSL2** : rien à adapter. En **PowerShell**, voir aussi les règles générales de l'Atelier 0.

- Mettez entre guillemets les options qui contiennent un point : `mvn test "-Dgroups=e2e" "-Dheaded=true"`,
  `"-Dexec.mainClass=com.microsoft.playwright.CLI"`.
- Navigateurs : `"-Dexec.args=install chromium firefox"`, **sans** `--with-deps` (réservé à Linux).
- Adresse de l'application : `$env:APP_URL = "http://localhost:8000"` (ou `"-Dapp.url=…"`).
- Partie C : le workflow s'exécute sur un runner Ubuntu, gardez `--with-deps` et la boucle
  `timeout 60 bash -c '…'` tels quels dans le YAML.
