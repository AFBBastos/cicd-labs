# Atelier 3 — Générer des tests avec un LLM (2 h 30) — déclinaison PHP

**Module 2** · Génération automatique de cas de test avec des modèles NLP

## Objectif
Transformer une spécification en langage naturel en tests PHPUnit exécutables, avec un LLM,
puis **évaluer objectivement** la qualité de ce qui a été généré.

## Prérequis
Atelier 0, étape 6 (accès IA) : la génération passe par l'outil Python du dépôt, déjà installé.
Hors Python, il n'y a **pas de moteur offline** : un LLM est obligatoire
(`LLM_PROVIDER=anthropic` + `ANTHROPIC_API_KEY`), et c'est vous qui lancez la suite générée avec PHPUnit.

Les commandes `python ai_tools/…` se lancent depuis la **racine du dépôt** ; les commandes `composer …`,
`vendor/bin/…` et `php tools/…` depuis `declinaisons/php/`.

## Étapes

### 1. La spécification (15 min)
Lisez `specs/pricing.feature` (format Gherkin : *Étant donné / Quand / Alors*), commune à tous les langages.
Ajoutez **3 scénarios** absents (ex. coupon FIXED5 sur un panier d'au moins 30 €, remise volume + WELCOME10,
quantité 0). Calculez les montants attendus à la main, à partir des règles — pas en lançant le code.

### 2. Moteur déterministe : la référence (15 min, facultatif)
Le moteur déterministe ne produit que du pytest. Lisez, à titre de comparaison, ce qu'il génère :
```bash
LLM_PROVIDER=offline python ai_tools/generate_tests.py specs/pricing.feature \
    --out tests/generated/test_pricing_offline.py
```
Limite : il ne sait traduire QUE la grammaire prévue, il n'invente aucun cas limite.

### 3. Moteur LLM (30 min)
```bash
export LLM_PROVIDER=anthropic         # + ANTHROPIC_API_KEY
python ai_tools/generate_tests.py specs/pricing.feature --lang php \
    --source declinaisons/php/src/Pricing.php declinaisons/php/src/Catalog.php \
    --out declinaisons/php/tests/Generated/PricingAiTest.php
```
Si l'outil répond « Réponse tronquée », relancez avec `LLM_EFFORT=low` devant la commande (ou augmentez
`LLM_MAX_TOKENS`) : avec l'effort par défaut, la réponse dépasse souvent la limite pour ce langage.

L'outil écrit le fichier mais ne l'exécute pas. Lancez la suite vous-même :
```bash
cd declinaisons/php
vendor/bin/phpunit --testsuite generated
```
Lisez `ai_tools/prompts/generate_tests_php.md`. Puis, dans le fichier généré :
- Combien de tests ? Combien de `testLimite…` que la spec ne mentionnait pas ?
- Des tests échouent-ils ? Pour chacun : **bug de l'appli** ou **hallucination** du modèle ?
- Le modèle a-t-il inventé une méthode ou un paramètre inexistant ? (`composer lint` : PHPStan les signale
  avant même l'exécution.)
- Le nom de la classe correspond-il au nom du fichier (`PricingAiTest`) ? Sinon PHPUnit ne la trouve pas.

### 4. Prompt engineering (30 min)
Modifiez le prompt et comparez (gardez un tableau de résultats). Il n'existe pas d'option pour désigner
un autre prompt : éditez `ai_tools/prompts/generate_tests_php.md` (gardez une copie de l'original) et relancez
la commande de l'étape 3. Pour ne pas envoyer le code source, passez un fichier vide à `--source`.
| Variante | Nb tests | Tests en échec | Couverture branches | Temps |
|---|---|---|---|---|
| Prompt fourni | | | | |
| Sans le code source (spec seule) | | | | |
| + exemple de test « parfait » (few-shot) | | | | |
| Effort de raisonnement réduit (`LLM_EFFORT=low` au lieu de `medium`) | | | | |
| Autre modèle (`LLM_MODEL=...`) | | | | |

(Avec Claude, la profondeur de raisonnement se règle par `LLM_EFFORT` : `low`, `medium` ou `high` ; la
température n'est pas transmise au modèle. Un seul essai ne prouve rien : relancez deux fois le prompt
fourni pour voir de combien les chiffres varient avant de comparer les variantes.)

### 5. Évaluer la qualité des tests générés (30 min)
La couverture ne suffit pas : un test sans assertion couvre du code sans rien vérifier
(PHPUnit le signale comme « risky », et la configuration du projet en fait un échec).
- **Couverture** (Xdebug) :
  ```bash
  XDEBUG_MODE=coverage php -d memory_limit=-1 -d pcov.enabled=0 vendor/bin/phpunit \
      --testsuite generated --path-coverage --coverage-text
  ```
- **Tests de mutation** (le vrai juge), avec Infection :
  ```bash
  vendor/bin/infection --threads=max --test-framework-options="--testsuite=generated"   # tests générés
  composer mutation                                                                      # vos tests de l'Atelier 1
  ```
  Un mutant « survivant » (*not detected*) = une modification du code que vos tests n'ont pas détectée.
  Le détail est dans `reports/infection.html`. Infection exige une suite **verte** : écartez ou corrigez
  d'abord les tests générés qui échouent.
  (Équivalents : `mutmut` en Python, PIT en Java, Stryker en JS et en C#.)
- Comparez le **score de mutation** (*Covered Code MSI*) : tests manuels (Atelier 1) vs tests générés.

### 6. Règles d'équipe (20 min)
Rédigez dans `docs/strategie-de-test.md` (section 3) vos règles d'usage des tests générés :
relecture, groupe `generated`, données sensibles dans les prompts, qui est responsable d'un test généré faux…

## Critères de réussite
- [ ] Un fichier de tests généré par LLM, relu, qui passe
- [ ] Le tableau de comparaison des prompts rempli
- [ ] Score de mutation mesuré pour au moins 2 approches
- [ ] Section « règles IA » de la stratégie de test rédigée

## Pour aller plus loin
- Générer des tests **d'API** à partir de `/openapi.json` (donnez le schéma au LLM).
- Générer des **données de test** (paniers réalistes, cas tordus) plutôt que des tests.
- Outils : GitHub Copilot `/tests`, Qodo (ex-Codium), Schemathesis (propriétés depuis OpenAPI).

## Sous Windows

Poste sous **WSL2** : rien à adapter. En **PowerShell**, voir aussi les règles générales de l'Atelier 0.

```powershell
# Étape 3 — moteur LLM (depuis la racine du dépôt, sur une seule ligne)
$env:LLM_PROVIDER = "anthropic"; $env:ANTHROPIC_API_KEY = "<clé>"
python ai_tools/generate_tests.py specs/pricing.feature --lang php --source declinaisons/php/src/Pricing.php declinaisons/php/src/Catalog.php --out declinaisons/php/tests/Generated/PricingAiTest.php

# Étape 4 — autre modèle
$env:LLM_MODEL = "claude-sonnet-5-5"      # Remove-Item Env:LLM_MODEL pour revenir au modèle du cours

# Étape 5 — couverture des tests générés (depuis declinaisons/php)
$env:XDEBUG_MODE = "coverage"
php -d memory_limit=-1 -d pcov.enabled=0 vendor/bin/phpunit --testsuite generated --path-coverage --coverage-text
Remove-Item Env:XDEBUG_MODE
```

Les commandes Infection de l'étape 5 sont identiques.
