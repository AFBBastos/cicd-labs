# Atelier 4 — L'IA dans la pipeline : génération et revue de PR (1 h 30) — déclinaison C#

**Module 2** · Intégration CI/CD de l'IA

## Objectif
Faire tourner les outils IA **dans** GitHub Actions en appelant une API de LLM (Claude, d'Anthropic) avec une clé
stockée en **secret** de dépôt :
génération de tests sur chaque PR et commentaire de revue automatique orienté tests.

Les outils IA (`ai_tools/`) restent en Python : le workflow installe **Python** pour les lancer **et .NET**
pour compiler et exécuter les tests C# générés.

## Étapes

### 1. Appeler un LLM depuis un workflow (15 min)
Créez `.github/workflows/ai-tests-csharp.yml` (à la racine du dépôt) avec :
```yaml
permissions:
  contents: read
  pull-requests: write  # pour commenter la PR
```
Enregistrez votre clé dans Settings → Secrets and variables → Actions → *New repository secret*,
sous le nom `ANTHROPIC_API_KEY` (jamais dans le dépôt, jamais dans un `echo`).
Premier job : un simple `python ai_tools/llm.py` avec ces variables d'environnement :
```yaml
    env:
      LLM_PROVIDER: anthropic
      LLM_MODEL: claude-haiku-5-5       # modèle économique du cours
      LLM_EFFORT: low                   # sans cela, la réponse peut dépasser LLM_MAX_TOKENS : rien n'est généré
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```
Sans secret, `llm.py` échoue avec « Variable ANTHROPIC_API_KEY manquante ».
Le job doit installer le SDK : `pip install -r requirements-dev.txt` (ou au minimum `pip install anthropic`).

La variante sans clé de l'énoncé d'origine (Ollama sur le runner, `LLM_PROVIDER: ollama`) fonctionne aussi.

### 2. Génération de tests sur chaque PR (25 min)
Les étapes du job, dans l'ordre :
```yaml
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12", cache: pip }
      - run: pip install -r requirements-dev.txt
      - uses: actions/setup-dotnet@v4
        with: { dotnet-version: "10.0.x" }
      - name: Générer les tests C# depuis la spécification
        id: gen
        continue-on-error: true
        run: |
          python ai_tools/generate_tests.py specs/pricing.feature --lang csharp \
            --source declinaisons/csharp/src/MiniShop/Pricing.cs declinaisons/csharp/src/MiniShop/Catalog.cs \
            --out declinaisons/csharp/tests/MiniShop.Tests/Generated/PricingGeneratedTests.cs
```
- `continue-on-error: true` : un test généré qui échoue (ou qui ne compile pas) est un **signal**, pas un
  blocage. Mettez-le aussi sur l'étape qui exécute les tests générés.
- Différence avec Python : pour `--lang csharp` il n'y a **pas de repli offline**. Sans secret (PR venant
  d'un fork, quota épuisé), la génération échoue avec un code de retour non nul et aucun fichier n'est écrit :
  le job reste vert grâce à `continue-on-error`, mais la couverture « après » est égale à la couverture « avant ».
- Mesurer la couverture **avant / après** ajout des tests générés et l'écrire dans `$GITHUB_STEP_SUMMARY`.
  Depuis `declinaisons/csharp` (`working-directory:` sur l'étape) : une exécution **avant** la génération,
  une **après**, chacune dans son dossier.
  ```bash
  dotnet tool restore
  dotnet test tests/MiniShop.Tests -p:TreatWarningsAsErrors=false --filter "Category=unit" \
      --collect:"XPlat Code Coverage" --results-directory reports/avant
  dotnet reportgenerator "-reports:reports/avant/*/coverage.cobertura.xml" \
      -targetdir:reports/coverage-avant -reporttypes:TextSummary
  grep -E "Line coverage|Branch coverage" reports/coverage-avant/Summary.txt
  ```
- Publier `declinaisons/csharp/tests/MiniShop.Tests/Generated/` en artefact (l'humain décide de les intégrer ou non).
  Un fichier intégré devra passer le job `lint` de l'Atelier 2 comme n'importe quel code.

### 3. Revue de PR par IA (30 min)
`review_pr.py` travaille sur le diff : il relit du C# comme du Python, rien à adapter.
- Job `ai-review` avec `fetch-depth: 0` (pour avoir le diff complet).
- `python ai_tools/review_pr.py --base origin/${{ github.base_ref }}`
- Poster le résultat : `gh pr comment <num> --body-file reports/ai-review.md --edit-last`
  (`GH_TOKEN` requis).
- Testez avec une PR piège : ajoutez dans `Pricing.cs` une méthode qui utilise `double` pour un montant, sans test.

### 4. Discussion : jusqu'où faire confiance ? (20 min)
Par groupe, répondez :
- La revue IA doit-elle pouvoir **bloquer** une PR ? (cf. option `--fail-on-high`)
- Que se passe-t-il si le diff contient un secret ? (avec une API en ligne, le diff part chez le
  fournisseur du modèle ; avec un modèle sur le runner, non — au prix de la qualité et de la durée)
- Coût, quota, latence : que faire si le modèle ne répond pas ou si le quota de la clé est atteint ?
  (la revue se replie sur le moteur offline ; la génération C#, elle, n'a pas de repli)
- Comment éviter qu'un contributeur externe déclenche des appels IA sur votre quota ?
  (indice : `pull_request` vs `pull_request_target`, environnements protégés)

## Critères de réussite
- [ ] Le workflow appelle un LLM (log : `moteur : anthropic`, et non `repli sur le moteur offline`)
- [ ] Une PR reçoit un commentaire de revue IA, mis à jour à chaque push
- [ ] Le résumé du run montre la couverture avant/après les tests générés

## Pour aller plus loin
- Comparer Claude, l'API Mistral (`LLM_PROVIDER: mistral`) et un modèle local (`qwen2.5-coder:1.5b` via Ollama) : qualité, durée, coût.
- Équivalent GitLab : job `ia:review-mr` dans `.gitlab-ci.yml` (note de MR via l'API).

## Sous Windows

Rien à adapter pour le workflow : il s'exécute sur un runner Ubuntu, les étapes `run:` restent en bash.

Pour essayer la revue en local avant de pousser (PowerShell, `PYTHONUTF8=1` requis, voir Atelier 0) :

```powershell
$env:LLM_PROVIDER = "anthropic"; $env:ANTHROPIC_API_KEY = "<clé>"
python ai_tools/review_pr.py --base origin/main
```

Le secret `ANTHROPIC_API_KEY` se crée dans l'interface web de GitHub, ou avec `gh secret set ANTHROPIC_API_KEY`
(la CLI `gh` existe pour Windows : `winget install GitHub.cli`).
