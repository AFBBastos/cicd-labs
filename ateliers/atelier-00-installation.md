# Atelier 0 — Installation du poste (30 min, lundi 9h)

## Objectif
Avoir un poste prêt pour toute la semaine : dépôt forké, environnement Python, appli qui tourne.

## Prérequis
- Compte GitHub (gratuit)
- Git, Python 3.11+, VS Code (ou PyCharm), Docker Desktop / Docker Engine
- Navigateur Chrome ou Firefox

## Étapes

1. **Forker** le dépôt du formateur sur votre compte GitHub, puis le cloner :
   ```bash
   git clone git@github.com:<vous>/cicd-ia-labs.git && cd cicd-ia-labs
   git checkout -b <prenom>
   ```
2. **Environnement virtuel** :
   ```bash
   python -m venv .venv
   source .venv/bin/activate          # Windows : .venv\Scripts\activate
   pip install -r requirements-dev.txt
   python -m playwright install --with-deps chromium   # Windows/Mac : sans --with-deps
   ```
3. **Lancer l'application** : `make run` (ou `uvicorn minishop.api:app --reload`)
   - Boutique : http://localhost:8000
   - Documentation OpenAPI : http://localhost:8000/docs
4. **Lancer les tests** fournis : `pytest -m "not e2e and not visual"` → 5 tests verts.
5. **Activer les GitHub Actions** sur votre fork (onglet *Actions* → « I understand… enable »).
6. **Accès IA (pour le Module 2)** — au choix :
   - *Anthropic / Claude* (recommandé) : le formateur vous fournit une clé d'API à quota limité, puis
     `export LLM_PROVIDER=anthropic ANTHROPIC_API_KEY=<clé>` (ne la committez jamais, ne la partagez pas)
   - *Mistral* (API en ligne ; clé à créer sur https://console.mistral.ai) : `export LLM_PROVIDER=mistral MISTRAL_API_KEY=<clé>`
   - *Ollama* (100 % local, sans compte ni clé) : installez Ollama (https://ollama.com/download
     ou `docker run -d -p 11434:11434 --name ollama ollama/ollama`), puis
     `ollama pull qwen2.5-coder:1.5b` (~1 Go ; avec Docker : `docker exec ollama ollama pull qwen2.5-coder:1.5b`)
     et `export LLM_PROVIDER=ollama`. Machine puissante (16 Go de RAM ou GPU) : `ollama pull qwen2.5-coder:7b`
     puis `export LLM_MODEL=qwen2.5-coder:7b` pour de meilleurs résultats. Le modèle 1.5b sur CPU est lent
     (plusieurs minutes pour un fichier de tests) et se trompe souvent : c'est un bon sujet d'analyse.
   - Aucun accès : `LLM_PROVIDER=offline` (par défaut) — les outils utilisent un moteur simulé.
   Vérification : `python ai_tools/llm.py`
   (GitHub Models, l'accès gratuit des sessions précédentes, a été arrêté par GitHub le 30 juillet 2026.)

## Critères de réussite
- [ ] La boutique s'affiche, `/docs` aussi
- [ ] `pytest` passe
- [ ] Les Actions sont activées sur le fork

## Plan du dépôt
```
minishop/        application FastAPI (prix, catalogue, API, page web)
tests/           unit / api / e2e / visual / perf / generated
specs/           spécifications en langage naturel (entrée de l'IA)
ai_tools/        outils IA & ML (génération, revue, anomalies, risque, visuel, docs, métriques)
scripts/         simulation d'historique de CI pour les ateliers ML
monitoring/      Prometheus + Pushgateway + Grafana + Alertmanager (docker compose)
docs/            documentation MkDocs (docs-as-code)
security/        règles OWASP ZAP
ateliers/        les énoncés
```

## Sous Windows

Les énoncés sont écrits pour un shell Linux/macOS (bash). Deux façons de travailler sous Windows :

**Option 1 — WSL2 (recommandée).** Installez Ubuntu (`wsl --install` dans un PowerShell administrateur, puis
redémarrez), activez dans Docker Desktop *Settings → Resources → WSL integration* pour cette distribution,
et clonez le dépôt **dans** WSL (`~/cicd-ia-labs`, pas sous `/mnt/c/`). Toutes les commandes des ateliers
fonctionnent alors telles quelles, y compris `make`. Ouvrez le dossier avec VS Code (`code .`, extension *WSL*).

**Option 2 — PowerShell.** Chaque atelier se termine par une section « Sous Windows » qui donne les
commandes adaptées. Règles générales de traduction :

| Dans l'énoncé (bash) | En PowerShell |
|---|---|
| `source .venv/bin/activate` | `.venv\Scripts\Activate.ps1` |
| `export VAR=valeur` | `$env:VAR = "valeur"` (valable dans ce terminal uniquement) |
| `VAR=valeur commande` | `$env:VAR = "valeur"; commande` puis `Remove-Item Env:VAR` pour revenir à la normale |
| `\` en fin de ligne | tout écrire sur une seule ligne (ou accent grave `` ` `` en fin de ligne) |
| `cmd1 && cmd2` | `cmd1; cmd2` (le `&&` n'existe qu'à partir de PowerShell 7) |
| `commande &` (arrière-plan) | lancer la commande dans un deuxième terminal |
| `"$PWD"` dans un `docker run -v` | `"${PWD}"`, par exemple `-v "${PWD}:/w"` |
| `mkdir -p dossier` | `New-Item -ItemType Directory -Force dossier` |
| `chmod …` | inutile sous Windows |
| `make <cible>` | la commande correspondante du `Makefile` (tableau ci-dessous) |

À faire une fois sur le poste :

```powershell
setx PYTHONUTF8 1          # Python lit et écrit en UTF-8 partout ; rouvrez le terminal ensuite
git clone git@github.com:<vous>/cicd-ia-labs.git; cd cicd-ia-labs
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python -m playwright install chromium
```

- Si l'activation est refusée (« l'exécution de scripts est désactivée ») :
  `Set-ExecutionPolicy -Scope Process RemoteSigned`, puis réessayez.
- Sans `PYTHONUTF8=1`, les outils qui lisent la sortie de `git` ou affichent des accents peuvent échouer
  (`UnicodeDecodeError` / `UnicodeEncodeError`).
- Si `python` ouvre le Microsoft Store, utilisez `py` ou désactivez les « alias d'exécution d'application ».
- Docker Desktop doit être démarré, en mode **conteneurs Linux** (moteur WSL2).
- Accès IA (étape 6) : `$env:LLM_PROVIDER = "anthropic"; $env:ANTHROPIC_API_KEY = "<clé>"`, à refaire dans
  chaque nouveau terminal. Vérification : `python ai_tools/llm.py`.

`make` n'existe pas sous Windows. Équivalents :

| Cible | Commande |
|---|---|
| `make run` | `uvicorn minishop.api:app --reload` |
| `make test` | `pytest -m "not e2e and not visual"` |
| `make unit` / `api` / `e2e` / `visual` | `pytest -m unit` (resp. `api`, `e2e`, `visual`) |
| `make cov` | `pytest -m "not e2e and not visual" --cov --cov-report=term-missing --cov-report=html` |
| `make lint` | `ruff check .; ruff format --check .` |
| `make perf` | `locust -f tests/perf/locustfile.py --headless -u 20 -r 5 -t 30s --host http://localhost:8000` |
| `make security` | `bandit -r minishop -q -ll; pip-audit -r requirements.txt` |
| `make docs` | `python ai_tools/gen_test_docs.py; mkdocs serve` |
| `make monitoring` | `docker compose -f monitoring/docker-compose.yml up -d` |

**Git Bash** (fourni avec Git pour Windows) accepte la syntaxe bash des énoncés, avec trois différences :
`source .venv/Scripts/activate`, pas de `make`, et les commandes `docker run` qui montent un chemin de
conteneur (`/var/run/docker.sock`, `/zap/wrk`, `-w /w`) doivent être préfixées par `MSYS_NO_PATHCONV=1`.

Tout ce qui s'exécute dans GitHub Actions tourne sur des machines Ubuntu : les étapes `run:` des workflows
restent en bash, quel que soit votre poste. En cas d'écart entre une variante PowerShell et l'énoncé,
c'est le comportement sous WSL2 qui fait foi.
