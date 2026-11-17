# Atelier 3 — Générer des tests avec un LLM (2 h 30) — déclinaison Java

**Module 2** · Génération automatique de cas de test avec des modèles NLP

## Objectif
Transformer une spécification en langage naturel en tests JUnit 5 exécutables, avec un LLM,
puis **évaluer objectivement** la qualité de ce qui a été généré.

## Prérequis
Atelier 0, étape 6 (accès IA) : l'outil de génération est celui du dépôt, en Python (`ai_tools/`).
Hors Python, il n'existe **ni moteur offline ni exécution automatique** : un LLM est requis
(`LLM_PROVIDER=anthropic` + `ANTHROPIC_API_KEY`) et vous lancez vous-même la suite avec Maven.

## Étapes

### 1. La spécification (15 min)
Lisez `specs/pricing.feature`, à la racine du dépôt (format Gherkin : *Étant donné / Quand / Alors*).
Elle est commune à tous les langages. Ajoutez **3 scénarios** absents (ex. coupon FIXED5 sur un panier d'au
moins 30 €, remise volume + WELCOME10, quantité 0). Calculez les montants attendus à la main, à partir des
règles — pas en lançant le code.

### 2. Moteur déterministe : lecture comparée (15 min, facultatif)
Le moteur déterministe ne produit que du Python. Depuis la racine du dépôt :
```bash
LLM_PROVIDER=offline python ai_tools/generate_tests.py specs/pricing.feature \
    --out tests/generated/test_pricing_offline.py
```
Lisez le code produit, même sans pratiquer Python : un test par scénario, rien de plus. Limite : il ne sait
traduire QUE la grammaire prévue, il n'invente aucun cas limite. Gardez-le comme point de comparaison.

### 3. Moteur LLM (30 min)
Depuis la **racine du dépôt** :
```bash
export LLM_PROVIDER=anthropic         # + ANTHROPIC_API_KEY
python ai_tools/generate_tests.py specs/pricing.feature --lang java \
    --source declinaisons/java/src/main/java/fr/minishop/Pricing.java \
             declinaisons/java/src/main/java/fr/minishop/Quote.java \
             declinaisons/java/src/main/java/fr/minishop/Item.java \
             declinaisons/java/src/main/java/fr/minishop/Catalog.java \
    --out declinaisons/java/src/test/java/fr/minishop/PricingAiTest.java
```
Si l'outil répond « Réponse tronquée », relancez avec `LLM_EFFORT=low` devant la commande (ou augmentez
`LLM_MAX_TOKENS`) : avec l'effort par défaut, la réponse dépasse souvent la limite pour ce langage.

(Seul le cœur métier est donné au modèle : la spécification porte sur les règles de prix, pas sur l'API.)
Les tests ne sont pas exécutés par l'outil. Lancez-les depuis `declinaisons/java/` :
```bash
mvn test -Dgroups=generated
```
(Le prompt demande au modèle d'annoter la classe avec `@Tag("generated")` et `@Tag("unit")`, et de nommer
la classe d'après le fichier de sortie. Si la classe générée ne s'appelle pas `PricingAiTest`, renommez le fichier.)

Lisez `ai_tools/prompts/generate_tests_java.md`. Puis, dans le fichier généré :
- Combien de tests ? Combien de tests `limite…` que la spec ne mentionnait pas ?
- Le fichier **compile**-t-il ? En Java, une fonction ou un paramètre inventé par le modèle est arrêté par le
  compilateur avant toute exécution — et bloque alors toute la suite, vos tests manuels compris.
- Des tests échouent-ils ? Pour chacun : **bug de l'appli** ou **hallucination** du modèle ?
- Le modèle compare-t-il les montants avec `equals` (piège de l'échelle, voir Atelier 1) ?

### 4. Prompt engineering (30 min)
Modifiez le prompt et comparez (gardez un tableau de résultats). Il n'existe pas d'option pour désigner
un autre prompt : éditez `ai_tools/prompts/generate_tests_java.md` (gardez une copie de l'original) et relancez
la commande de l'étape 3.
| Variante | Nb tests | Erreurs de compilation | Tests en échec | Couverture branches | Temps |
|---|---|---|---|---|---|
| Prompt fourni | | | | | |
| `--source` réduit à `Pricing.java` (sans `Quote`, `Item`, `Catalog`) | | | | | |
| + exemple de test « parfait » (few-shot) | | | | | |
| Effort de raisonnement réduit (`LLM_EFFORT=low` au lieu de `medium`) | | | | | |
| Autre modèle (`LLM_MODEL=...`) | | | | | |

(Avec Claude, la profondeur de raisonnement se règle par `LLM_EFFORT` : `low`, `medium` ou `high` ; la
température n'est pas transmise au modèle. Un seul essai ne prouve rien : relancez deux fois le prompt
fourni pour voir de combien les chiffres varient avant de comparer les variantes.)

### 5. Évaluer la qualité des tests générés (30 min)
La couverture ne suffit pas : un test sans assertion couvre du code sans rien vérifier.
Depuis `declinaisons/java/` :
- **Couverture** des seuls tests générés : `mvn verify -Dgroups=generated` puis `target/site/jacoco/index.html`
- **Tests de mutation** (le vrai juge) avec **PIT**, l'outil de référence en Java :
  ```bash
  mvn test-compile org.pitest:pitest-maven:mutationCoverage -Dpit.tests=fr.minishop.PricingAiTest   # tests générés
  mvn test-compile org.pitest:pitest-maven:mutationCoverage -Dpit.tests=fr.minishop.PricingTest     # vos tests de l'Atelier 1
  ```
  Rapport : `target/pit-reports/index.html`. Un mutant « survivant » = une modification du code que vos tests
  n'ont pas détectée. PIT exige une suite **verte** : corrigez ou retirez d'abord les tests générés en échec.
  (Équivalents : `mutmut` ou `cosmic-ray` en Python, Stryker en JS et en C#, Infection en PHP.)
- Comparez le **score de mutation** : tests manuels (Atelier 1) vs tests générés par LLM.

### 6. Règles d'équipe (20 min)
Rédigez dans `docs/strategie-de-test.md` (section 3) vos règles d'usage des tests générés :
relecture, étiquette `generated`, données sensibles dans les prompts, qui est responsable d'un test généré faux…

## Critères de réussite
- [ ] Un fichier de tests généré par LLM, relu, qui compile et qui passe
- [ ] Le tableau de comparaison des prompts rempli
- [ ] Score de mutation mesuré pour au moins 2 approches
- [ ] Section « règles IA » de la stratégie de test rédigée

## Pour aller plus loin
- Générer des tests **d'API** à partir de `/openapi.json` (donnez le schéma au LLM).
- Générer des **données de test** (paniers réalistes, cas tordus) plutôt que des tests.
- Outils : GitHub Copilot `/tests`, Qodo (ex-Codium), Diffblue (Java), Schemathesis (propriétés depuis OpenAPI).

## Sous Windows

Poste sous **WSL2** : rien à adapter. En **PowerShell**, voir aussi les règles générales de l'Atelier 0.

```powershell
# Étape 3 — moteur LLM (une seule ligne, depuis la racine du dépôt)
$env:LLM_PROVIDER = "anthropic"; $env:ANTHROPIC_API_KEY = "<clé>"
python ai_tools/generate_tests.py specs/pricing.feature --lang java --source declinaisons/java/src/main/java/fr/minishop/Pricing.java declinaisons/java/src/main/java/fr/minishop/Quote.java declinaisons/java/src/main/java/fr/minishop/Item.java declinaisons/java/src/main/java/fr/minishop/Catalog.java --out declinaisons/java/src/test/java/fr/minishop/PricingAiTest.java

# Étape 4 — effort de raisonnement, autre modèle
$env:LLM_EFFORT = "low"                   # Remove-Item Env:LLM_EFFORT pour revenir au réglage par défaut
$env:LLM_MODEL = "claude-sonnet-5-5"      # Remove-Item Env:LLM_MODEL pour revenir au modèle du cours

# Étape 5 — options Maven entre guillemets
mvn test-compile org.pitest:pitest-maven:mutationCoverage "-Dpit.tests=fr.minishop.PricingAiTest"
```
