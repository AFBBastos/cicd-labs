# Atelier 4 — L'IA dans la pipeline : génération et revue de PR (1 h 30) — déclinaison Java

**Module 2** · Intégration CI/CD de l'IA

## Objectif
Faire tourner les outils IA **dans** GitHub Actions en appelant une API de LLM (Claude, d'Anthropic) avec une clé
stockée en **secret** de dépôt :
génération de tests sur chaque PR et commentaire de revue automatique orienté tests.

Les outils IA du dépôt (`ai_tools/`) sont en Python, les tests générés en Java : le workflow installe donc
**Python** (pour les outils) **et Java** (pour exécuter les tests générés).

## Étapes

### 1. Appeler un LLM depuis un workflow (15 min)
Créez `.github/workflows/ai-tests-java.yml` (à la racine du dépôt) avec :
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
- Installer les deux environnements :
  ```yaml
      - uses: actions/setup-python@v5
        with: { python-version: "3.12", cache: pip }
      - run: pip install -r requirements-dev.txt
      - uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: "21"
          cache: maven
          cache-dependency-path: declinaisons/java/pom.xml
  ```
- Mesurer la couverture **avant** la génération (étape dans le projet Java : `working-directory: declinaisons/java`) :
  ```bash
  mvn -B -ntp -q verify -Dgroups=unit
  awk -F, '$3 == "Pricing" { printf "%d / %d branches", $7, $6 + $7 }' target/site/jacoco/jacoco.csv > avant.txt
  ```
- Lancer `ai_tools/generate_tests.py … --lang java` depuis la racine (commande de l'Atelier 3) avec
  `continue-on-error: true` (un test généré qui échoue est un **signal**, pas un blocage).
  Hors Python il n'y a **pas de repli offline** : sans secret (ou sur une PR venant d'un fork), l'étape
  échoue et aucun fichier n'est produit. Le job reste vert, lisez le log.
- Mesurer la couverture **après** et écrire les deux chiffres dans `$GITHUB_STEP_SUMMARY`
  (même `working-directory`) :
  ```bash
  mvn -B -ntp -q verify -Dgroups=unit -Dmaven.test.failure.ignore=true \
    && apres=$(awk -F, '$3 == "Pricing" { printf "%d / %d branches", $7, $6 + $7 }' target/site/jacoco/jacoco.csv) \
    || apres="les tests générés ne compilent pas"
  {
    echo "### Tests générés par IA (Java)"
    echo "- Avant : $(cat avant.txt)"
    echo "- Après : $apres"
  } >> "$GITHUB_STEP_SUMMARY"
  ```
  `-Dmaven.test.failure.ignore=true` laisse Maven aller jusqu'au rapport de couverture même si un test
  généré échoue. Une erreur de **compilation**, elle, arrête tout : c'est le signal d'une hallucination.
- Publier `declinaisons/java/src/test/java/fr/minishop/PricingAiTest.java` et
  `declinaisons/java/target/surefire-reports/` en artefact (l'humain décide d'intégrer les tests ou non).

### 3. Revue de PR par IA (30 min)
`review_pr.py` travaille sur le diff Git : il fonctionne tel quel sur du code Java. Seul Python est nécessaire.
- Job `ai-review` avec `fetch-depth: 0` (pour avoir le diff complet).
- `python ai_tools/review_pr.py --base origin/${{ github.base_ref }}`
- Poster le résultat : `gh pr comment <num> --body-file reports/ai-review.md --edit-last`
  (`GH_TOKEN` requis).
- Testez avec une PR piège : ajoutez dans `Pricing.java` une méthode qui utilise `double` pour un montant, sans test
  (ou une nouvelle route dans `ShopController.java`, sans test d'API).

### 4. Discussion : jusqu'où faire confiance ? (20 min)
Par groupe, répondez :
- La revue IA doit-elle pouvoir **bloquer** une PR ? (cf. option `--fail-on-high`)
- Que se passe-t-il si le diff contient un secret ? (avec une API en ligne, le diff part chez le
  fournisseur du modèle ; avec un modèle sur le runner, non — au prix de la qualité et de la durée)
- Coût, quota, latence : que faire si le modèle ne répond pas ou si le quota de la clé est atteint ?
  (la revue se replie sur un moteur offline ; la génération Java, non : que doit faire le pipeline ?)
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
