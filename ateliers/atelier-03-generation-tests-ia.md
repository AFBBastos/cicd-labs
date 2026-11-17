# Atelier 3 — Générer des tests avec un LLM (2 h 30)

**Module 2** · Génération automatique de cas de test avec des modèles NLP

## Objectif
Transformer une spécification en langage naturel en tests pytest exécutables, avec un LLM,
puis **évaluer objectivement** la qualité de ce qui a été généré.

## Prérequis
Atelier 0, étape 6 (accès IA). Sans accès : `LLM_PROVIDER=offline` (moteur déterministe).

## Étapes

### 1. La spécification (15 min)
Lisez `specs/pricing.feature` (format Gherkin : *Étant donné / Quand / Alors*).
Ajoutez **3 scénarios** absents (ex. coupon FIXED5 sur un panier d'au moins 30 €, remise volume + WELCOME10,
quantité 0). Calculez les montants attendus à la main, à partir des règles — pas en lançant le code.

### 2. Moteur déterministe : la référence (15 min)
```bash
LLM_PROVIDER=offline python ai_tools/generate_tests.py specs/pricing.feature \
    --out tests/generated/test_pricing_offline.py
```
Lisez le code produit. Limite : il ne sait traduire QUE la grammaire prévue, il n'invente aucun cas limite.

### 3. Moteur LLM (30 min)
```bash
export LLM_PROVIDER=anthropic         # + ANTHROPIC_API_KEY ; ou mistral, ollama (lent sur CPU)
python ai_tools/generate_tests.py specs/pricing.feature \
    --source minishop/pricing.py --out tests/generated/test_pricing_ai.py
```
Lisez `ai_tools/prompts/generate_tests.md`. Puis, dans le fichier généré :
- Combien de tests ? Combien de `test_limite_*` que la spec ne mentionnait pas ?
- Des tests échouent-ils ? Pour chacun : **bug de l'appli** ou **hallucination** du modèle ?
- Le modèle a-t-il inventé une fonction ou un paramètre inexistant ?

### 4. Prompt engineering (30 min)
Modifiez le prompt et comparez (gardez un tableau de résultats). Il n'existe pas d'option pour désigner
un autre prompt : éditez `ai_tools/prompts/generate_tests.md` (gardez une copie de l'original) et relancez
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
La couverture ne suffit pas : un test sans `assert` couvre du code sans rien vérifier.
- **Couverture** : `pytest tests/generated --cov=minishop.pricing --cov-branch`
- **Tests de mutation** (le vrai juge) :
  ```bash
  python ai_tools/mutation_score.py minishop/pricing.py tests/generated   # 30 s à 1 min
  python ai_tools/mutation_score.py minishop/pricing.py tests/unit        # vos tests de l'Atelier 1
  ```
  Un mutant « survivant » = une modification du code que vos tests n'ont pas détectée.
  (Outil pédagogique fourni ; en production : `mutmut`, `cosmic-ray`, PIT en Java, Stryker en JS.)
- Comparez le **score de mutation** : tests manuels (Atelier 1) vs offline vs LLM.

### 6. Règles d'équipe (20 min)
Rédigez dans `docs/strategie-de-test.md` (section 3) vos règles d'usage des tests générés :
relecture, marqueur `generated`, données sensibles dans les prompts, qui est responsable d'un test généré faux…

## Critères de réussite
- [ ] Un fichier de tests généré par LLM, relu, qui passe
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
# Étape 2 — moteur déterministe
$env:LLM_PROVIDER = "offline"
python ai_tools/generate_tests.py specs/pricing.feature --out tests/generated/test_pricing_offline.py

# Étape 3 — moteur LLM
$env:LLM_PROVIDER = "anthropic"; $env:ANTHROPIC_API_KEY = "<clé>"
python ai_tools/generate_tests.py specs/pricing.feature --source minishop/pricing.py --out tests/generated/test_pricing_ai.py

# Étape 4 — prompt sans le code source : un fichier vide pour --source
New-Item vide.py -ItemType File
python ai_tools/generate_tests.py specs/pricing.feature --source vide.py --out tests/generated/test_pricing_ai.py

# Étape 4 — effort de raisonnement réduit
$env:LLM_EFFORT = "low"                   # Remove-Item Env:LLM_EFFORT pour revenir au réglage par défaut

# Étape 4 — autre modèle
$env:LLM_MODEL = "claude-sonnet-5-5"      # Remove-Item Env:LLM_MODEL pour revenir au modèle du cours
```

Les commandes de l'étape 5 (`pytest … --cov`, `mutation_score.py`) sont identiques.
