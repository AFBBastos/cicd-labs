# Atelier 3 — Générer des tests avec un LLM (2 h 30) — déclinaison Node.js

**Module 2** · Génération automatique de cas de test avec des modèles NLP

## Objectif
Transformer une spécification en langage naturel en tests Vitest exécutables, avec un LLM,
puis **évaluer objectivement** la qualité de ce qui a été généré.

## Prérequis
Atelier 0, étape 6 (accès IA) : l'outil de génération est celui du dépôt, en Python
(`ai_tools/generate_tests.py`), installé à l'Atelier 0. Il se lance **depuis la racine du dépôt**.

Hors Python, il n'existe **ni moteur offline ni exécution automatique** : un LLM est requis
(`LLM_PROVIDER=anthropic` + `ANTHROPIC_API_KEY`) et c'est vous qui lancez ensuite la suite avec Vitest.

## Étapes

### 1. La spécification (15 min)
Lisez `specs/pricing.feature` (format Gherkin : *Étant donné / Quand / Alors*), commune à tous les langages.
Ajoutez **3 scénarios** absents (ex. coupon FIXED5 sur un panier d'au moins 30 €, remise volume + WELCOME10,
quantité 0). Calculez les montants attendus à la main, à partir des règles — pas en lançant le code.

### 2. Moteur déterministe : lecture comparée (15 min, facultatif)
Le moteur déterministe ne produit que du Python. Il reste utile comme point de comparaison :
```bash
LLM_PROVIDER=offline python ai_tools/generate_tests.py specs/pricing.feature \
    --out tests/generated/test_pricing_offline.py
```
Lisez le code produit (inutile de l'exécuter). Limite : il ne sait traduire QUE la grammaire prévue,
il n'invente aucun cas limite. Gardez-le sous les yeux pour l'étape suivante.

### 3. Moteur LLM (30 min)
Depuis la racine du dépôt :
```bash
export LLM_PROVIDER=anthropic         # + ANTHROPIC_API_KEY ; ou mistral, ollama (lent sur CPU)
python ai_tools/generate_tests.py specs/pricing.feature --lang node \
    --source declinaisons/node/src/pricing.js declinaisons/node/src/catalog.js \
    --out declinaisons/node/tests/generated/pricing.ai.test.js
```
Si l'outil répond « Réponse tronquée », relancez avec `LLM_EFFORT=low` devant la commande (ou augmentez
`LLM_MAX_TOKENS`) : avec l'effort par défaut, la réponse dépasse souvent la limite pour ce langage.

L'outil écrit le fichier et s'arrête là. Lancez vous-même les tests générés :
```bash
cd declinaisons/node
npx vitest run tests/generated --reporter=verbose
```
Lisez `ai_tools/prompts/generate_tests_node.md`. Puis, dans le fichier généré :
- Combien de tests ? Combien de `limite : …` que la spec ne mentionnait pas ?
- Les imports sont-ils justes ? Depuis `tests/generated/`, le code est dans `../../src/pricing.js`.
- Des tests échouent-ils ? Pour chacun : **bug de l'appli** ou **hallucination** du modèle ?
- Le modèle a-t-il inventé une fonction ou un paramètre inexistant ? Compare-t-il des montants en
  nombres flottants ?
- Le fichier passe-t-il `npm run lint` et `npm run format:check` ?

### 4. Prompt engineering (30 min)
Modifiez le prompt et comparez (gardez un tableau de résultats). Il n'existe pas d'option pour désigner
un autre prompt : éditez `ai_tools/prompts/generate_tests_node.md` (gardez une copie de l'original) et relancez
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

Changez le nom du fichier `--out` à chaque variante (`pricing.v2.test.js`…) : le nom doit se terminer
par `.test.js` pour que Vitest le prenne en compte.

### 5. Évaluer la qualité des tests générés (30 min)
La couverture ne suffit pas : un test sans `expect` couvre du code sans rien vérifier.
- **Couverture** : `npx vitest run tests/generated --coverage`
- **Tests de mutation** (le vrai juge), avec **Stryker** :
  ```bash
  npm run mutation:generated      # tests/generated ; 15 à 30 s
  npm run mutation                # tests/unit : vos tests de l'Atelier 1
  ```
  Un mutant « survivant » (`Survived`) = une modification du code que vos tests n'ont pas détectée ;
  `NoCoverage` = une modification qu'aucun test n'exécute. Stryker liste chaque survivant avec le
  diff appliqué ; le rapport HTML est dans `reports/mutation/`.
  (Les mutants des constantes de module sont ignorés — option `ignoreStatic` de `stryker.config.json` :
  le lanceur Vitest ne sait pas les évaluer correctement. Stryker refuse de démarrer si un test échoue :
  corrigez ou retirez d'abord les tests générés faux.)
- Comparez le **score de mutation** : tests manuels (Atelier 1) vs LLM, et d'une variante de prompt à l'autre.

### 6. Règles d'équipe (20 min)
Rédigez dans `docs/strategie-de-test.md` (section 3) vos règles d'usage des tests générés :
relecture, rangement (dossier `tests/generated/` et bloc `describe('generated', …)`, qui remplacent le
marqueur `generated` de pytest), données sensibles dans les prompts, qui est responsable d'un test généré faux…

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
python ai_tools/generate_tests.py specs/pricing.feature --lang node --source declinaisons/node/src/pricing.js declinaisons/node/src/catalog.js --out declinaisons/node/tests/generated/pricing.ai.test.js

# Étape 4 — autre modèle
$env:LLM_MODEL = "claude-sonnet-5-5"      # Remove-Item Env:LLM_MODEL pour revenir au modèle du cours
```

Les commandes de l'étape 5 (`npx vitest … --coverage`, `npm run mutation`) sont identiques.
