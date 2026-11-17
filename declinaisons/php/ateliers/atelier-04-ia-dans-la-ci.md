# Atelier 4 — L'IA dans la pipeline : génération et revue de PR (1 h 30) — déclinaison PHP

**Module 2** · Intégration CI/CD de l'IA

## Objectif
Faire tourner les outils IA **dans** GitHub Actions en appelant une API de LLM (Claude, d'Anthropic) avec une clé
stockée en **secret** de dépôt :
génération de tests sur chaque PR et commentaire de revue automatique orienté tests.

Les outils IA du dépôt (`ai_tools/`) sont en Python, quel que soit le langage testé : le workflow installe
donc **Python** pour les outils **et PHP** pour exécuter les tests générés.

## Étapes

### 1. Appeler un LLM depuis un workflow (15 min)
Créez `.github/workflows/ai-tests-php.yml` (à la racine du dépôt) avec :
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
et ces étapes d'installation :
```yaml
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r requirements-dev.txt        # outils ai_tools/ (SDK anthropic compris)
      - uses: shivammathur/setup-php@v2
        with: { php-version: "8.4", coverage: pcov }
      - run: composer install --no-interaction --no-progress
        working-directory: declinaisons/php
```
Sans secret, `llm.py` échoue avec « Variable ANTHROPIC_API_KEY manquante ». La revue de PR se replie sur
le moteur offline (le job reste vert : lisez le log pour savoir quel moteur a répondu) ; la **génération
de tests PHP, elle, n'a pas de repli** : sans LLM, `generate_tests.py --lang php` s'arrête avec un code d'erreur.

Variante sans clé ni compte — Ollama sur le runner, avec `LLM_PROVIDER: ollama` (le code ne quitte pas
le runner, mais sur CPU un petit modèle est lent et se trompe souvent) :
```yaml
      - name: Démarrer Ollama et charger le modèle
        run: |
          docker run -d --name ollama -p 11434:11434 ollama/ollama
          timeout 60 bash -c 'until curl -sf localhost:11434/api/tags; do sleep 1; done'
          docker exec ollama ollama pull qwen2.5-coder:1.5b
```
(GitHub Models, qui permettait d'appeler un LLM avec le jeton automatique, a été arrêté le 30 juillet 2026.)

### 2. Génération de tests sur chaque PR (25 min)
- Lancer la génération depuis la racine, avec `continue-on-error: true` (un test généré qui échoue est
  un **signal**, pas un blocage) :
  ```bash
  python ai_tools/generate_tests.py specs/pricing.feature --lang php \
      --source declinaisons/php/src/Pricing.php declinaisons/php/src/Catalog.php \
      --out declinaisons/php/tests/Generated/PricingAiTest.php
  ```
- Mesurer la couverture **avant / après** ajout des tests générés et l'écrire dans `$GITHUB_STEP_SUMMARY`
  (étapes avec `working-directory: declinaisons/php`) :
  ```bash
  vendor/bin/phpunit --testsuite unit --coverage-cobertura reports/avant.xml     # avant
  vendor/bin/phpunit --testsuite unit,generated --coverage-cobertura reports/apres.xml   # après
  php tools/coverage-check.php reports/avant.xml --markdown >> "$GITHUB_STEP_SUMMARY"
  php tools/coverage-check.php reports/apres.xml --markdown >> "$GITHUB_STEP_SUMMARY"
  ```
- Publier `declinaisons/php/tests/Generated/` en artefact (l'humain décide de les intégrer ou non).

### 3. Revue de PR par IA (30 min)
`review_pr.py` travaille sur un diff : il fonctionne tel quel sur du PHP.
- Job `ai-review` avec `fetch-depth: 0` (pour avoir le diff complet) ; Python suffit pour ce job.
- `python ai_tools/review_pr.py --base origin/${{ github.base_ref }}`
- Poster le résultat : `gh pr comment <num> --body-file reports/ai-review.md --edit-last`
  (`GH_TOKEN` requis).
- Testez avec une PR piège : ajoutez dans `src/Pricing.php` une méthode qui utilise `float` pour un montant,
  sans test.

### 4. Discussion : jusqu'où faire confiance ? (20 min)
Par groupe, répondez :
- La revue IA doit-elle pouvoir **bloquer** une PR ? (cf. option `--fail-on-high`)
- Que se passe-t-il si le diff contient un secret ? (avec une API en ligne, le diff part chez le
  fournisseur du modèle ; avec un modèle sur le runner, non — au prix de la qualité et de la durée)
- Coût, quota, latence : que faire si le modèle ne répond pas ou si le quota de la clé est atteint ?
  (regardez le repli offline de `review_pr.py`, et l'absence de repli de la génération PHP)
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

Rien à adapter pour le workflow : il s'exécute sur un runner Ubuntu, les étapes `run:` restent en bash
(y compris la variante Ollama avec `timeout … bash -c`).

Pour essayer la revue en local avant de pousser (PowerShell, `PYTHONUTF8=1` requis, voir Atelier 0) :

```powershell
$env:LLM_PROVIDER = "anthropic"; $env:ANTHROPIC_API_KEY = "<clé>"
python ai_tools/review_pr.py --base origin/main
```

Le secret `ANTHROPIC_API_KEY` se crée dans l'interface web de GitHub, ou avec `gh secret set ANTHROPIC_API_KEY`
(la CLI `gh` existe pour Windows : `winget install GitHub.cli`).
