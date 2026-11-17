# Atelier 8 — Tests fonctionnels UI de bout en bout (2 h 30) — déclinaison PHP

**Module 3** · Tests UI avec Selenium, Cypress (et Playwright)

## Objectif
Automatiser les parcours utilisateur de MiniShop, les rendre fiables, et les exécuter dans la CI
sur plusieurs navigateurs avec des captures exploitables en cas d'échec.

## Préparation
L'application testée est celle de ce dossier, lancée dans Docker depuis `declinaisons/php/` :
```bash
docker compose up -d --build
curl -sf http://localhost:8000/health
```
Les tests boîte noire vivent dans un projet Composer séparé, `declinaisons/php/boite-noire/`, pour ne pas
alourdir la suite unitaire. Toutes les commandes de cet atelier se lancent depuis ce dossier :
```bash
cd declinaisons/php/boite-noire
composer install
```
Il faut en plus l'extension PHP `zip`, un navigateur **Chrome ou Chromium** et son pilote **chromedriver**
dans le `PATH` (Debian/Ubuntu : `sudo apt install chromium chromium-driver`). L'adresse de l'application se
lit dans `MINISHOP_URL` (`http://localhost:8000` par défaut).

## Partie A — Symfony Panther (75 min)

Panther pilote un vrai navigateur depuis PHPUnit ; c'est l'équivalent PHP de Playwright dans cet atelier.

1. Lancer le test fourni : `composer e2e`, puis avec le navigateur visible : `PANTHER_NO_HEADLESS=1 composer e2e`
2. Panther n'a **pas d'enregistreur** de parcours (pas d'équivalent de `playwright codegen`). Pour démarrer vite,
   repérez les éléments dans les outils de développement du navigateur : la page expose des attributs
   `data-testid` (`add-mug`, `coupon`, `quote-btn`, `total`, `order-btn`, `confirmation`…).
3. Écrire dans `tests/E2e/ParcoursAchatTest.php` :
   - parcours d'achat : 2 mugs + WELCOME10 → total `27.40` → commande confirmée ;
   - coupon invalide → message d'erreur (élément `[role="alert"]`) ;
   - bouton « Commander » désactivé tant que le panier est vide (`->isEnabled()`).

   Les gestes de base :
   ```php
   $crawler = $client->getCrawler();
   $crawler->filter('[data-testid="add-mug"]')->click();
   $crawler->filter('[data-testid="coupon"]')->sendKeys('WELCOME10');
   $client->waitForElementToContain('[data-testid="total"]', '27.40');
   ```
4. Bonnes pratiques à appliquer :
   - localisateurs par **`data-testid` ou rôle** (`[role="alert"]`), jamais par XPath ou classe CSS ;
   - **attentes explicites** de Panther (`waitFor`, `waitForVisibility`, `waitForElementToContain`) avant chaque
     assertion sur un contenu produit par JavaScript : pas de `sleep()` ;
   - une méthode privée `shop()` qui ouvre la page et rend le client (équivalent d'une fixture) ; tests
     **indépendants** entre eux.
5. Page Object (15 min) : extrayez une classe `ShopPage` (`add(string $product)`, `applyCoupon(string $code)`,
   `total()`, `order()`) qui enveloppe le client Panther. Les tests deviennent lisibles par le métier.

## Partie B — Selenium, pour comparer (35 min)
Panther s'appuie sur la bibliothèque `php-webdriver/webdriver`, le client Selenium pour PHP : elle est donc
déjà installée. Utilisez-la directement, sans Panther. Lancez le pilote dans un autre terminal :
```bash
chromedriver --port=4444
```
(pas le port 9515 : Panther le réserve pour son propre chromedriver.)

Écrivez `tests/Selenium/SeleniumAccueilTest.php` qui vérifie le titre et ajoute un produit au panier, à partir de :
```php
$options = new ChromeOptions();
$options->addArguments(['--headless=new', '--window-size=1280,900']);
$capabilities = DesiredCapabilities::chrome();
$capabilities->setCapability(ChromeOptions::CAPABILITY, $options);
$driver = RemoteWebDriver::create('http://localhost:4444', $capabilities);
```
(classes de l'espace de noms `Facebook\WebDriver`), puis lancez `composer selenium`.
Notez ce qui vous a manqué par rapport à Panther (démarrage du pilote à la main, attentes explicites
`$driver->wait(5)->until(...)`, `quit()` à ne pas oublier, pas de capture en cas d'échec…).
Optionnel : la même chose en **Cypress** (JS).

## Partie C — Dans la CI (40 min)
Créez `.github/workflows/e2e-php.yml` (à la racine du dépôt) :
- `defaults: run: working-directory: declinaisons/php/boite-noire` ; `shivammathur/setup-php@v2` avec
  `extensions: zip` ;
- matrice `browser: [chrome, firefox]`, transmise au test par la variable `MINISHOP_BROWSER` (le test fourni la
  lit déjà ; les runners Ubuntu embarquent les deux navigateurs et leurs pilotes) ;
- démarrer l'appli en arrière-plan (`docker compose up -d --build`, avec `working-directory: declinaisons/php`) et **attendre**
  qu'elle réponde : `timeout 30 bash -c 'until curl -sf localhost:8000/health; do sleep 1; done'` ;
- `vendor/bin/phpunit --testsuite e2e --log-junit reports/e2e-${{ matrix.browser }}.xml` avec la variable
  `PANTHER_ERROR_SCREENSHOT_DIR: captures` : Panther y dépose une capture d'écran par test en échec ;
- artefact `captures/` et `reports/` **en cas d'échec** (chemins complets depuis la racine : `path:` ne suit pas
  `working-directory`).
- Panther n'a ni traces ni vidéo : la capture et le message d'erreur sont vos seuls indices. Parallélisation :
  les deux navigateurs tournent dans deux jobs — attention aux tests qui partagent des données (commandes).

Cassez volontairement l'interface (renommez un `data-testid`) et diagnostiquez **uniquement** avec la capture
et le rapport.

## Critères de réussite
- [ ] 3 parcours E2E verts, sans aucun `sleep`
- [ ] Page Object en place
- [ ] Exécution CI sur 2 navigateurs, captures récupérables en cas d'échec
- [ ] Comparatif Selenium / Panther (/ Cypress) en 5 lignes

## Pour aller plus loin
- Grilles cloud **BrowserStack / Sauce Labs** : mêmes tests, navigateurs et mobiles réels (essais gratuits).
- Traces, vidéo, enregistreur : c'est ce qu'apporte Playwright (Python ou Node.js) par rapport à Panther.

## Sous Windows

Poste sous **WSL2** : rien à adapter. En **PowerShell**, les commandes `composer …` sont identiques ; une
variable d'environnement se pose avant la commande et se retire ensuite :
```powershell
$env:PANTHER_NO_HEADLESS = "1"; composer e2e; Remove-Item Env:PANTHER_NO_HEADLESS
```
`chromedriver.exe` doit être dans le `PATH` (ou dans un dossier `drivers/` du projet). Partie C : le workflow
s'exécute sur un runner Ubuntu, gardez la syntaxe bash.
