# Atelier 8 — Tests fonctionnels UI de bout en bout (2 h 30) — déclinaison Node.js

**Module 3** · Tests UI avec Selenium, Cypress (et Playwright)

## Objectif
Automatiser les parcours utilisateur de MiniShop, les rendre fiables, et les exécuter dans la CI
sur plusieurs navigateurs avec des traces exploitables en cas d'échec.

## Préparation
L'application testée est celle de ce dossier. Lancez-la dans un premier terminal (`npm start`) ou dans
Docker, depuis `declinaisons/node/` :
```bash
docker compose up -d --build
curl -sf http://localhost:8000/health
```
Les commandes `npm` et `npx` se lancent depuis `declinaisons/node/`. L'outil est **Playwright Test**
(`@playwright/test`, déjà dans `package.json`) : Playwright est né en Node.js et apporte son propre lanceur
de tests — ce n'est pas Vitest. Les tests E2E sont dans `e2e/*.spec.js`, la configuration dans
`playwright.config.js`. Installez les navigateurs une fois :
```bash
npx playwright install --with-deps chromium        # Windows / macOS : sans --with-deps
```
L'adresse de l'application se lit dans `MINISHOP_URL` (défaut : `http://localhost:8000`).

## Partie A — Playwright (75 min)

1. Lancer le test fourni : `npx playwright test --project=chromium --headed`
   (ralenti : ajoutez `launchOptions: { slowMo: 300 }` dans le bloc `use` de `playwright.config.js`).
2. Enregistrer un parcours pour démarrer vite :
   ```bash
   npx playwright codegen http://localhost:8000
   ```
   Le code généré est un **brouillon** : réécrivez-le proprement.
3. Écrire dans `e2e/parcours-achat.spec.js` :
   - parcours d'achat : 2 mugs + WELCOME10 → total `27.40` → commande confirmée ;
   - coupon invalide → message d'erreur (`page.getByRole('alert')`) ;
   - bouton « Commander » désactivé tant que le panier est vide.
4. Bonnes pratiques à appliquer :
   - localisateurs par **rôle / texte / data-testid**, jamais par XPath ou classe CSS ;
   - assertions **web-first** (`await expect(...).toHaveText(...)`) : pas de `setTimeout` ni de
     `page.waitForTimeout` ;
   - une fixture `shop` qui ouvre la page (`test.extend`) ; tests **indépendants** entre eux ;
   - un `await` devant chaque action et chaque `expect` : un `await` oublié donne un test qui passe à tort.
5. Page Object (15 min) : extrayez une classe `ShopPage` dans `e2e/shop-page.js` (`add(product)`,
   `applyCoupon(code)`, `total()`, `order()`). Les tests deviennent lisibles par le métier.

## Partie B — Selenium, pour comparer (35 min)
```bash
npm install -D selenium-webdriver@4.46
```
(La version 4.46 est la dernière qui accepte Node.js 20 ; avec Node.js 22 ou 24, la dernière version convient.)

Écrivez `tests/selenium/accueil.test.js` — avec Vitest, cette fois (`npx vitest run tests/selenium`) — qui
vérifie le titre et ajoute un produit au panier (Selenium Manager télécharge le driver tout seul). Pour démarrer :
```js
import { Browser, Builder, By, until } from 'selenium-webdriver';
import chrome from 'selenium-webdriver/chrome.js';

const options = new chrome.Options().addArguments('--headless=new');
const driver = await new Builder().forBrowser(Browser.CHROME).setChromeOptions(options).build();
// … driver.get(url), driver.wait(until.elementLocated(By.css('…')), 5000), driver.quit()
```
Ouvrez le navigateur dans un `beforeAll` (avec un délai généreux : le premier lancement télécharge le
driver) et fermez-le dans un `afterAll`. Notez ce qui vous a manqué par rapport à Playwright (attentes
explicites `driver.wait(until…)`, pas de traces…). Optionnel : la même chose en **Cypress**.

## Partie C — Dans la CI (40 min)
Créez `.github/workflows/e2e-node.yml` (à la racine du dépôt) :
- matrice `browser: [chromium, firefox]`, `npx playwright install --with-deps ${{ matrix.browser }}` ;
- démarrer l'appli en arrière-plan (`npm start &`, ou l'image Docker du dossier)
  et **attendre** qu'elle réponde :
  `timeout 30 bash -c 'until curl -sf localhost:8000/health; do sleep 1; done'` ;
- `npx playwright test --project=${{ matrix.browser }}` ; les traces et les vidéos se règlent dans
  `playwright.config.js` : `trace: 'retain-on-failure'`, `video: 'retain-on-failure'`,
  `screenshot: 'only-on-failure'` (bloc `use`), sortie dans `test-results/` ;
- artefact `declinaisons/node/test-results/` **en cas d'échec** ; ouvrez une trace avec
  `npx playwright show-trace trace.zip` (ou https://trace.playwright.dev).
- Parallélisation : `npx playwright test --workers=2` — attention aux tests qui partagent des données (commandes).

Cassez volontairement l'interface (renommez un `data-testid`) et diagnostiquez **uniquement** avec la trace.

## Critères de réussite
- [ ] 3 parcours E2E verts, sans aucun `sleep`
- [ ] Page Object en place
- [ ] Exécution CI sur 2 navigateurs, traces récupérables en cas d'échec
- [ ] Comparatif Selenium / Playwright (/ Cypress) en 5 lignes

## Pour aller plus loin
- Grilles cloud **BrowserStack / Sauce Labs** : mêmes tests, navigateurs et mobiles réels (essais gratuits).
- Tests d'accessibilité : `npm install -D @axe-core/playwright`.

## Sous Windows

Poste sous **WSL2** : rien à adapter. En **PowerShell** :

- Parties A et B : commandes identiques. L'application doit tourner dans un autre terminal (`npm start`).
- Navigateurs : `npx playwright install chromium firefox`, **sans** `--with-deps` (réservé à Linux).
- Autre adresse pour l'application : `$env:MINISHOP_URL = "http://localhost:8001"` avant la commande,
  `Remove-Item Env:MINISHOP_URL` ensuite.
- Partie C : le workflow s'exécute sur un runner Ubuntu, gardez `--with-deps` et la boucle
  `timeout 30 bash -c '…'` tels quels dans le YAML.
