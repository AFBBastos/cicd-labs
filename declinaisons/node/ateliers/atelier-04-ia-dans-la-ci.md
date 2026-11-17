# Atelier 4 — L'IA dans la pipeline : génération et revue de PR (1 h 30) — déclinaison Node.js

**Module 2** · Intégration CI/CD de l'IA

## Objectif
Faire tourner les outils IA **dans** GitHub Actions en appelant une API de LLM (Claude, d'Anthropic) avec une clé
stockée en **secret** de dépôt :
génération de tests sur chaque PR et commentaire de revue automatique orienté tests.

Les outils IA du dépôt (`ai_tools/`) sont en Python, le code testé en JavaScript : le workflow installe
donc **les deux** — Python pour générer et relire, Node.js pour exécuter les tests générés.

## Étapes

### 1. Appeler un LLM depuis un workflow (15 min)
Créez `.github/workflows/ai-tests-node.yml` (à la racine du dépôt) avec :
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
Sans secret, `llm.py` échoue avec « Variable ANTHROPIC_API_KEY manquante ». La revue de PR, elle, se replie
sur le moteur offline (le job reste vert : lisez le log pour savoir quel moteur a répondu). La génération
avec `--lang node` n'a **pas** de repli : sans LLM, elle s'arrête avec un code de retour 2.
Le job doit installer le SDK : `pip install -r requirements-dev.txt` (ou au minimum `pip install anthropic`).

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
- Installer les deux environnements. Ici, pas de `defaults.run.working-directory` : les outils Python se
  lancent depuis la racine, les commandes npm dans `declinaisons/node` (`working-directory:` étape par étape) :
  ```yaml
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - uses: actions/setup-node@v4
        with: { node-version: 22 }
      - run: pip install -r requirements-dev.txt
      - run: npm ci
        working-directory: declinaisons/node
  ```
- Lancer `ai_tools/generate_tests.py … --lang node` (commande de l'Atelier 3), puis
  `npx vitest run tests/generated` ; `continue-on-error: true` sur ces deux étapes (un test généré qui
  échoue est un **signal**, pas un blocage).
- Mesurer la couverture **avant / après** ajout des tests générés et l'écrire dans `$GITHUB_STEP_SUMMARY` :
  `npx vitest run tests/unit tests/api --coverage` avant, `npx vitest run tests/unit tests/api tests/generated --coverage` après ;
  le tableau est à chaque fois dans `coverage/coverage.txt`. Ajoutez `--coverage.reportOnFailure` : sans cette
  option, Vitest n'écrit pas la couverture quand un test échoue — or un test généré peut échouer.
- Publier `declinaisons/node/tests/generated/` en artefact (l'humain décide de les intégrer ou non).

### 3. Revue de PR par IA (30 min)
- Job `ai-review` avec `fetch-depth: 0` (pour avoir le diff complet).
- `python ai_tools/review_pr.py --base origin/${{ github.base_ref }}` — l'outil relit un diff, quel que
  soit le langage : rien à adapter. Ce job n'a besoin que de Python.
- Poster le résultat : `gh pr comment <num> --body-file reports/ai-review.md --edit-last`
  (`GH_TOKEN` requis).
- Testez avec une PR piège : ajoutez dans `src/pricing.js` une fonction qui utilise `Number` ou
  `parseFloat` pour un montant, sans test.

### 4. Discussion : jusqu'où faire confiance ? (20 min)
Par groupe, répondez :
- La revue IA doit-elle pouvoir **bloquer** une PR ? (cf. option `--fail-on-high`)
- Que se passe-t-il si le diff contient un secret ? (avec une API en ligne, le diff part chez le
  fournisseur du modèle ; avec un modèle sur le runner, non — au prix de la qualité et de la durée)
- Coût, quota, latence : que faire si le modèle ne répond pas ou si le quota de la clé est atteint ?
  (regardez le repli offline de `review_pr.py`, et l'absence de repli de la génération `--lang node`)
- Comment éviter qu'un contributeur externe déclenche des appels IA sur votre quota ?
  (indice : `pull_request` vs `pull_request_target`, environnements protégés)

## Critères de réussite
- [ ] Le workflow appelle un LLM (log : `moteur : anthropic`, et non `repli sur le moteur offline`)
- [ ] Une PR reçoit un commentaire de revue IA, mis à jour à chaque push
- [ ] Le résumé du run montre la couverture avant/après les tests générés

## Pour aller plus loin
- Comparer Claude, l'API Mistral (`LLM_PROVIDER: mistral`) et un modèle local (`qwen2.5-coder:1.5b` via Ollama) : qualité, durée, coût.
- Ajouter le score de mutation des tests générés au résumé : `npm run mutation:generated`.
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
