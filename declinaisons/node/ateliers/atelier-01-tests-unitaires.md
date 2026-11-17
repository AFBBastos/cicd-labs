# Atelier 1 — Tests unitaires avec Vitest (1 h 15) — déclinaison Node.js

**Module 1** · Compétences C8 (TDD), C19 (Clean Code)

## Objectif
Écrire une suite de tests unitaires solide pour les règles de prix de MiniShop et mesurer la couverture.

## Contexte
Toutes les commandes se lancent depuis `declinaisons/node/` (après `npm ci`, voir le `README.md` du dossier).

Lisez l'en-tête de `src/pricing.js` : il décrit les règles métier (remise volume, coupons, livraison,
arrondi). Le fichier `tests/unit/pricing.test.js` contient 3 tests d'exemple et une liste de TODO.

Les montants sont des `Decimal` (bibliothèque `decimal.js`), jamais des nombres : JavaScript n'a pas de
type décimal et `0.1 + 0.2` vaut `0.30000000000000004`. Vérifiez-le : `node -e "console.log(0.1 + 0.2)"`.

## Étapes

### 1. Échauffement (10 min)
```bash
npx vitest run tests/unit --reporter=verbose
npx vitest run tests/unit --coverage
```
Notez la couverture de départ de `pricing.js`. Quelles lignes ne sont jamais exécutées (colonne
`Uncovered Line #s`) ? (`app.js` et `server.js`, l'API HTTP, restent à 0 % ici : ils sont testés par
`tests/api`, vus aux Ateliers 2 et 9.)

### 2. Tests paramétrés (25 min)
Complétez les TODO. Utilisez `test.each` pour éviter le copier-coller :
```js
test.each([0, -1, 100])('quantité hors limites : %s', (qty) => {
  expect(() => lineTotal(D('10'), qty)).toThrow(RangeError);
});

test.each([['2'], [true], [2.5], [null]])('quantité non entière : %o', (qty) => {
  expect(() => lineTotal(D('10'), qty)).toThrow(TypeError);
});
```
JavaScript est typé dynamiquement : rien n'empêche d'appeler `lineTotal` avec `'2'` ou `true`. Ces cas
gardent donc tout leur sens, et c'est aux tests de prouver qu'ils sont refusés.

Pensez **valeurs limites** : 9 vs 10 unités, 19,99 € vs 20 € pour WELCOME10, 49,99 € vs 50 € pour la livraison.

### 3. Un petit cycle TDD (20 min)
Nouvelle règle demandée par le métier :
> Coupon `STUDENT15` : -15 % sur le sous-total, sans minimum, **non cumulable** avec la remise volume
> (si une ligne a la remise volume, le coupon ne s'applique pas à cette ligne).

1. **Rouge** : écrivez d'abord 3 tests qui échouent.
2. **Vert** : implémentez le minimum dans `src/pricing.js`.
3. **Refactor** : nettoyez sans casser les tests.

`npm run test:watch` relance les tests à chaque sauvegarde.

### 4. Couverture et qualité (15 min)
```bash
npx vitest run tests/unit --coverage
```
Ouvrez `coverage/index.html` dans le navigateur (`open` sous macOS, `xdg-open` sous Linux, `start` sous Windows).
Objectif : **≥ 90 % de couverture de branches** (colonne `% Branch`) sur `pricing.js`.
Question : 100 % de couverture garantit-il l'absence de bug ? Testez :
```bash
MINISHOP_BUG=rounding npx vitest run tests/unit
```
Vos tests détectent-ils le bug d'arrondi injecté ?

## Critères de réussite
- [ ] ≥ 15 tests, dont au moins 3 paramétrés
- [ ] Couverture branches ≥ 90 % sur `pricing.js`
- [ ] La suite échoue avec `MINISHOP_BUG=rounding`
- [ ] STUDENT15 implémenté en TDD (historique Git : commit des tests AVANT le code)

## Pour aller plus loin
- Tests de propriétés avec **fast-check** (l'équivalent d'Hypothesis) : « le total n'est jamais négatif »,
  « ajouter un article ne baisse jamais le sous-total ».
- Tests de mutation : `npm run mutation` (Stryker ; on y reviendra à l'Atelier 3).

## Sous Windows

Poste sous **WSL2** : rien à adapter. En **PowerShell**, voir aussi les règles générales de l'Atelier 0.

- Les commandes `npx vitest` sont identiques.
- Rapport de couverture : `start coverage/index.html`
- Bug d'arrondi injecté :
  ```powershell
  $env:MINISHOP_BUG = "rounding"; npx vitest run tests/unit
  Remove-Item Env:MINISHOP_BUG      # indispensable, sinon le bug reste actif dans ce terminal
  ```
