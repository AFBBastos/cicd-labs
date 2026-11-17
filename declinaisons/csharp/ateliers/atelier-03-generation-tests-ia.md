# Atelier 3 — Générer des tests avec un LLM (2 h 30) — déclinaison C#

**Module 2** · Génération automatique de cas de test avec des modèles NLP

## Objectif
Transformer une spécification en langage naturel en tests xUnit exécutables, avec un LLM,
puis **évaluer objectivement** la qualité de ce qui a été généré.

## Prérequis
Atelier 0, étape 6 (accès IA) : la génération passe par l'outil Python du dépôt, déjà installé.
En C#, il n'y a **pas de moteur offline** : un LLM est obligatoire (`LLM_PROVIDER=anthropic` +
`ANTHROPIC_API_KEY`). L'outil écrit le fichier mais ne l'exécute pas : c'est vous qui lancez `dotnet test`.

Les commandes `python ai_tools/…` se lancent depuis la **racine** du dépôt, les commandes `dotnet` depuis
`declinaisons/csharp/`.

## Étapes

### 1. La spécification (15 min)
Lisez `specs/pricing.feature` à la racine (format Gherkin : *Étant donné / Quand / Alors*). Elle est commune
à tous les langages.
Ajoutez **3 scénarios** absents (ex. coupon FIXED5 sur un panier d'au moins 30 €, remise volume + WELCOME10,
quantité 0). Calculez les montants attendus à la main, à partir des règles — pas en lançant le code.

### 2. Moteur déterministe : la référence (15 min, facultatif)
Le moteur déterministe n'existe que pour Python. Lisez un fichier qu'il produit pour savoir à quoi comparer
le travail du LLM :
```bash
LLM_PROVIDER=offline python ai_tools/generate_tests.py specs/pricing.feature \
    --out tests/generated/test_pricing_offline.py
```
Limite : il ne sait traduire QUE la grammaire prévue, il n'invente aucun cas limite.

### 3. Moteur LLM (30 min)
Depuis la racine du dépôt :
```bash
export LLM_PROVIDER=anthropic         # + ANTHROPIC_API_KEY ; ou mistral, ollama (lent sur CPU)
python ai_tools/generate_tests.py specs/pricing.feature --lang csharp \
    --source declinaisons/csharp/src/MiniShop/Pricing.cs declinaisons/csharp/src/MiniShop/Catalog.cs \
    --out declinaisons/csharp/tests/MiniShop.Tests/Generated/PricingGeneratedTests.cs
```
Si l'outil répond « Réponse tronquée », relancez avec `LLM_EFFORT=low` devant la commande (ou augmentez
`LLM_MAX_TOKENS`) : avec l'effort par défaut, la réponse dépasse souvent la limite pour ce langage.

Puis, depuis `declinaisons/csharp/` :
```bash
dotnet test -p:TreatWarningsAsErrors=false --filter "Category=generated"
```
Le projet traite les avertissements comme des erreurs : un `using` inutile dans le fichier généré suffit à
bloquer la compilation, d'où `-p:TreatWarningsAsErrors=false` pour cette première exécution.

Lisez `ai_tools/prompts/generate_tests_csharp.md`. Puis, dans le fichier généré :
- Combien de tests ? Combien de `Limite_*` que la spec ne mentionnait pas ?
- Le fichier compile-t-il ? En C#, une fonction ou un paramètre inventé par le modèle se voit dès la
  compilation, avant le moindre test. Une classe nommée `PricingTests` dans le même espace de noms que la
  vôtre provoque aussi une erreur : renommez-la.
- Des tests échouent-ils ? Pour chacun : **bug de l'appli** ou **hallucination** du modèle ?

### 4. Prompt engineering (30 min)
Modifiez le prompt et comparez (gardez un tableau de résultats). Il n'existe pas d'option pour désigner
un autre prompt : éditez `ai_tools/prompts/generate_tests_csharp.md` (gardez une copie de l'original) et relancez
la commande de l'étape 3. Pour ne pas envoyer le code source, passez un fichier vide à `--source`.
| Variante | Nb tests | Erreurs de compilation | Tests en échec | Couverture branches | Temps |
|---|---|---|---|---|---|
| Prompt fourni | | | | | |
| Sans le code source (spec seule) | | | | | |
| + exemple de test « parfait » (few-shot) | | | | | |
| Effort de raisonnement réduit (`LLM_EFFORT=low` au lieu de `medium`) | | | | | |
| Autre modèle (`LLM_MODEL=...`) | | | | | |

(Avec Claude, la profondeur de raisonnement se règle par `LLM_EFFORT` : `low`, `medium` ou `high` ; la
température n'est pas transmise au modèle. Un seul essai ne prouve rien : relancez deux fois le prompt
fourni pour voir de combien les chiffres varient avant de comparer les variantes.)

### 5. Évaluer la qualité des tests générés (30 min)
La couverture ne suffit pas : un test sans `Assert` couvre du code sans rien vérifier.
- Mettez d'abord le fichier généré aux normes du projet : `dotnet format` corrige ce qui peut l'être,
  `dotnet build` doit passer sans `-p:TreatWarningsAsErrors=false`.
- **Couverture** des seuls tests générés :
  ```bash
  dotnet test tests/MiniShop.Tests --filter "Category=generated" \
      --collect:"XPlat Code Coverage" --results-directory reports/generated
  dotnet reportgenerator "-reports:reports/generated/*/coverage.cobertura.xml" \
      -targetdir:reports/coverage-generated "-reporttypes:Html;TextSummary"
  ```
- **Tests de mutation** (le vrai juge), avec **Stryker.NET** à la place de `mutation_score.py` :
  ```bash
  dotnet stryker --test-case-filter "Category=generated"                    # 30 s à 1 min
  dotnet stryker --test-case-filter "Category=unit&Category!=generated"     # vos tests de l'Atelier 1
  ```
  Stryker ne mute que la bibliothèque `MiniShop` (`stryker-config.json`) ; le second filtre écarte aussi
  les tests d'API, qui tueraient des mutants à la place de vos tests unitaires.
  Un mutant « survivant » = une modification du code que vos tests n'ont pas détectée. Lisez la colonne
  `% score` du tableau, puis le rapport `StrykerOutput/<date>/reports/mutation-report.html` : il montre chaque
  mutant dans le code.
- Comparez le **score de mutation** : tests manuels (Atelier 1) vs LLM.

### 6. Règles d'équipe (20 min)
Rédigez dans `docs/strategie-de-test.md` (section 3, à la racine) vos règles d'usage des tests générés :
relecture, trait `generated`, données sensibles dans les prompts, qui est responsable d'un test généré faux…

## Critères de réussite
- [ ] Un fichier de tests généré par LLM, relu, qui compile et qui passe
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
python ai_tools/generate_tests.py specs/pricing.feature --lang csharp --source declinaisons/csharp/src/MiniShop/Pricing.cs declinaisons/csharp/src/MiniShop/Catalog.cs --out declinaisons/csharp/tests/MiniShop.Tests/Generated/PricingGeneratedTests.cs

# Étape 4 — autre modèle
$env:LLM_MODEL = "claude-sonnet-5-5"      # Remove-Item Env:LLM_MODEL pour revenir au modèle du cours
```

Les commandes `dotnet` des étapes 3 et 5 sont identiques (gardez les guillemets autour des filtres et des
options `-reports:…` / `-reporttypes:…`).
