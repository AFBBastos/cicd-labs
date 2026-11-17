# Atelier 1 — Tests unitaires avec PHPUnit (1 h 15) — déclinaison PHP

**Module 1** · Compétences C8 (TDD), C19 (Clean Code)

## Objectif
Écrire une suite de tests unitaires solide pour les règles de prix de MiniShop et mesurer la couverture.

## Contexte
Toutes les commandes se lancent depuis `declinaisons/php/` (après `composer install`, voir le `README.md`).
Lisez l'en-tête de `src/Pricing.php` : il décrit les règles métier (remise volume, coupons, livraison,
arrondi). Le fichier `tests/Unit/PricingTest.php` contient 3 tests d'exemple et une liste de TODO.

## Étapes

### 1. Échauffement (10 min)
```bash
composer test
composer coverage
```
Notez la couverture de départ de `MiniShop\Pricing` (le total est bas : la suite unitaire n'exécute pas la
couche HTTP de `src/Http/`, testée à l'Atelier 9). Ouvrez `reports/coverage/index.html` : quelles lignes de
`Pricing.php` ne sont jamais exécutées ?

### 2. Tests paramétrés (25 min)
Complétez les TODO. Utilisez `#[DataProvider]` pour éviter le copier-coller :
```php
/** @return iterable<string, array{mixed}> */
public static function quantitesInvalides(): iterable
{
    yield 'zéro' => [0];
    yield 'négative' => [-1];
    yield 'cent' => [100];
    yield 'chaîne' => ['2'];
    yield 'booléen' => [true];
}

#[DataProvider('quantitesInvalides')]
public function testQuantiteInvalide(mixed $qty): void
{
    $this->expectException(\InvalidArgumentException::class);

    Pricing::lineTotal(BigDecimal::of('10'), $qty);
}
```
(ajoutez `use PHPUnit\Framework\Attributes\DataProvider;` en tête de fichier.)

Pensez **valeurs limites** : 9 vs 10 unités, 19,99 € vs 20 € pour WELCOME10, 49,99 € vs 50 € pour la livraison.

### 3. Un petit cycle TDD (20 min)
Nouvelle règle demandée par le métier :
> Coupon `STUDENT15` : -15 % sur le sous-total, sans minimum, **non cumulable** avec la remise volume
> (si une ligne a la remise volume, le coupon ne s'applique pas à cette ligne).

1. **Rouge** : écrivez d'abord 3 tests qui échouent.
2. **Vert** : implémentez le minimum dans `src/Pricing.php`.
3. **Refactor** : nettoyez sans casser les tests (`composer lint` doit rester propre).

### 4. Couverture et qualité (15 min)
```bash
composer coverage-branches
php tools/coverage-check.php reports/cobertura.xml --file=Pricing.php --min-branches=90
```
La couverture de branches demande **Xdebug** (pcov ne mesure que les lignes). Ouvrez
`reports/coverage/index.html` dans le navigateur (`open` sous macOS, `xdg-open` sous Linux, `start` sous Windows).
Objectif : **≥ 90 % de couverture de branches** sur `Pricing.php`.
Question : 100 % de couverture garantit-il l'absence de bug ? Testez :
```bash
MINISHOP_BUG=rounding composer test
```
Vos tests détectent-ils le bug d'arrondi injecté ?

## Critères de réussite
- [ ] ≥ 15 tests, dont au moins 3 paramétrés
- [ ] Couverture branches ≥ 90 % sur `Pricing.php`
- [ ] La suite échoue avec `MINISHOP_BUG=rounding`
- [ ] STUDENT15 implémenté en TDD (historique Git : commit des tests AVANT le code)

## Pour aller plus loin
- Tests de propriétés : « le total n'est jamais négatif », « ajouter un article ne baisse jamais le sous-total »
  (un `DataProvider` qui tire des paniers au hasard suffit pour commencer).
- Tests de mutation : `composer mutation` (Infection ; on y reviendra à l'Atelier 3).

## Sous Windows

Poste sous **WSL2** : rien à adapter. En **PowerShell** :

- Les commandes `composer …` et `php tools/…` sont identiques.
- Rapport de couverture : `start reports/coverage/index.html`
- Bug d'arrondi injecté :
  ```powershell
  $env:MINISHOP_BUG = "rounding"; composer test
  Remove-Item Env:MINISHOP_BUG      # indispensable, sinon le bug reste actif dans ce terminal
  ```
