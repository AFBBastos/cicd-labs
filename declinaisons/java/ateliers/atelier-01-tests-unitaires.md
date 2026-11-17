# Atelier 1 — Tests unitaires avec JUnit (1 h 15) — déclinaison Java

**Module 1** · Compétences C8 (TDD), C19 (Clean Code)

## Objectif
Écrire une suite de tests unitaires solide pour les règles de prix de MiniShop et mesurer la couverture.

## Contexte
Toutes les commandes se lancent depuis `declinaisons/java/`.
Lisez l'en-tête de `src/main/java/fr/minishop/Pricing.java` : il décrit les règles métier (remise volume,
coupons, livraison, arrondi). Le fichier `src/test/java/fr/minishop/PricingTest.java` contient 3 tests d'exemple
et une liste de TODO. (L'application web, dans `fr/minishop/api/`, s'appuie sur ces règles : elle sera
testée à partir de l'Atelier 8.)

## Étapes

### 1. Échauffement (10 min)
```bash
mvn test -Dgroups=unit
mvn verify
```
`mvn verify` lance toute la suite (tests unitaires et tests d'API en mémoire). Ouvrez
`target/site/jacoco/index.html`, paquet `fr.minishop`, et notez la couverture de départ de `Pricing`
(colonnes *Missed Branches* et *Cov.*). Cliquez sur la classe : quelles lignes (en rouge) ne sont jamais exécutées ?

### 2. Tests paramétrés (25 min)
Complétez les TODO. Utilisez `@ParameterizedTest` pour éviter le copier-coller :
```java
@ParameterizedTest
@ValueSource(ints = {0, -1, 100})
void quantiteInvalide(int qty) {
  assertThatThrownBy(() -> Pricing.lineTotal(new BigDecimal("10"), qty))
      .isInstanceOf(IllegalArgumentException.class);
}
```
Pour plusieurs colonnes, `@CsvSource({"20.00, WELCOME10, 2.00", "19.99, WELCOME10, 0.00"})` : JUnit convertit
chaque colonne vers le type du paramètre (`String`, `int`, `boolean`…).

Deux différences avec la version Python du cours :
- **Typage statique.** En Python on teste aussi les quantités `"2"` et `True`. En Java, la quantité est un
  `int` : ces appels ne compilent pas, le compilateur élimine cette classe de tests. Restent les bornes 0, -1 et 100.
- **Égalité des `BigDecimal`.** `new BigDecimal("25.0").equals(new BigDecimal("25.00"))` vaut `false`, car
  `equals` compare aussi l'échelle. Comparez les montants avec `compareTo`, c'est-à-dire en AssertJ
  `assertThat(total).isEqualByComparingTo("25.00")`. N'utilisez jamais `double` pour un montant.

Pensez **valeurs limites** : 9 vs 10 unités, 19,99 € vs 20 € pour WELCOME10, 49,99 € vs 50 € pour la livraison.

### 3. Un petit cycle TDD (20 min)
Nouvelle règle demandée par le métier :
> Coupon `STUDENT15` : -15 % sur le sous-total, sans minimum, **non cumulable** avec la remise volume
> (si une ligne a la remise volume, le coupon ne s'applique pas à cette ligne).

1. **Rouge** : écrivez d'abord 3 tests qui échouent.
2. **Vert** : implémentez le minimum dans `Pricing.java`.
3. **Refactor** : nettoyez sans casser les tests (`mvn spotless:apply` remet le code au format).

### 4. Couverture et qualité (15 min)
```bash
mvn verify -Djacoco.branches.min=0.90
```
Le build échoue tant que la couverture de **branches** de `Pricing` est sous 90 % (règle `check` de JaCoCo).
Le rapport est dans `target/site/jacoco/index.html` (`open` sous macOS, `xdg-open` sous Linux, `start` sous Windows).
Une fois l'objectif atteint, inscrivez le seuil dans le `pom.xml` (propriété `jacoco.branches.min`).

Question : 100 % de couverture garantit-il l'absence de bug ? Testez :
```bash
MINISHOP_BUG=rounding mvn test
```
Vos tests détectent-ils le bug d'arrondi injecté ?

Pour écrire un test qui *démontre* ce bug sans toucher à l'environnement du processus (Java ne permet pas de
modifier une variable d'environnement en cours d'exécution), utilisez le point d'injection prévu :
`Pricing.roundingMode("rounding")` renvoie le mode d'arrondi que donnerait la variable, et
`Pricing.money(montant, mode)` l'applique.

## Critères de réussite
- [ ] ≥ 15 tests (ligne `Tests run:` de Maven), dont au moins 3 méthodes paramétrées
- [ ] Couverture branches ≥ 90 % sur `Pricing`
- [ ] La suite échoue avec `MINISHOP_BUG=rounding`
- [ ] STUDENT15 implémenté en TDD (historique Git : commit des tests AVANT le code)

## Pour aller plus loin
- Tests de propriétés avec **jqwik** : « le total n'est jamais négatif », « ajouter un article ne baisse jamais le sous-total ».
- Tests de mutation avec **PIT** : `mvn test-compile org.pitest:pitest-maven:mutationCoverage`, rapport dans
  `target/pit-reports/index.html` (on y reviendra à l'Atelier 3).

## Sous Windows

Poste sous **WSL2** : rien à adapter. En **PowerShell**, voir aussi les règles générales de l'Atelier 0.

- Les commandes `mvn` sont identiques, mais mettez entre guillemets les options qui contiennent un point :
  `mvn verify "-Djacoco.branches.min=0.90"`.
- Rapport de couverture : `start target/site/jacoco/index.html`
- Bug d'arrondi injecté :
  ```powershell
  $env:MINISHOP_BUG = "rounding"; mvn test
  Remove-Item Env:MINISHOP_BUG      # indispensable, sinon le bug reste actif dans ce terminal
  ```
