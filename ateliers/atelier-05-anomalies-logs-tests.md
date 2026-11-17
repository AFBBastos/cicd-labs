# Atelier 5 — Détecter les anomalies dans les logs et les exécutions de tests (2 h)

**Module 2** · Détection automatique des anomalies (apprentissage non supervisé)

## Objectif
Repérer automatiquement ce qu'un humain ne voit pas dans des milliers de lignes : pics de latence,
rafales d'erreurs, tests instables (*flaky*), tests qui ralentissent, familles d'échecs.

## Préparation
```bash
python scripts/simulate_history.py
```
Vous obtenez `data/app-logs.jsonl` (5 000 requêtes), `data/junit-history/` (60 runs de CI).
Les données sont simulées mais réalistes ; la colonne `_truth` des logs permet de **mesurer** la détection.

## Partie A — Logs applicatifs (50 min)

1. Ouvrez quelques lignes de `data/app-logs.jsonl`. Que chercheriez-vous « à la main » ?
2. Lancez la détection :
   ```bash
   python ai_tools/log_anomalies.py data/app-logs.jsonl
   ```
   Lisez `reports/anomalies.md`. Deux techniques sont combinées :
   - **IsolationForest** sur des fenêtres de 30 s (volume, taux de 5xx/4xx, latences p50/p95/max) ;
   - **z-score robuste** (médiane / MAD) par route, requête par requête, avec un plancher de 100 ms.
3. Expérimentez. La section « Évaluation » du rapport mesure chaque technique à part : au niveau
   **fenêtre** (IsolationForest) et au niveau **requête** (z-score). Notez rappel / précision :
   | Paramètre | Fenêtres signalées | Rappel (fenêtres) | Précision (fenêtres) | Rappel (requêtes) | Précision (requêtes) |
   |---|---|---|---|---|---|
   | défaut (`--window 30 --contamination 0.02`) | | | | | |
   | `--contamination 0.10` | | | | | |
   | `--window 5` | | | | | |
   | `--window 5 --contamination 0.10` | | | | | |
   | `--z-threshold 3 --min-latency-ms 0` (au lieu de 6 et 100 ms) | | | | | |
   Quels paramètres agissent sur quelles colonnes ? Que règle vraiment `--contamination` ?
   Conclusion : quel compromis choisir pour une alerte qui réveille quelqu'un la nuit ?
4. Sur **vos** logs réels : une phase normale qui sert de référence, puis une phase ralentie, dans le
   même journal (le fichier est complété, pas écrasé).
   ```bash
   rm -f logs/app.jsonl
   MINISHOP_LOG_FILE=logs/app.jsonl uvicorn minishop.api:app &                     # phase normale
   locust -f tests/perf/locustfile.py --host http://localhost:8000 --headless -u 20 -r 5 -t 60s
   kill $!                                                                          # arrête l'application
   MINISHOP_LOG_FILE=logs/app.jsonl MINISHOP_BUG=slow uvicorn minishop.api:app &   # phase ralentie
   locust -f tests/perf/locustfile.py --host http://localhost:8000 --headless -u 20 -r 5 -t 60s
   kill $!
   python ai_tools/log_anomalies.py logs/app.jsonl --window 5
   ```
   (Le second Locust se termine en échec : ses propres seuils ne sont pas tenus, c'est attendu.)
   Le ralentissement injecté sur `/cart/*` est-il détecté ? Par laquelle des deux techniques, et sur
   quelles routes ? Pourquoi la phase normale est-elle nécessaire (que donnerait la phase ralentie seule) ?

## Partie B — Historique des exécutions de tests (50 min)

1. ```bash
   python ai_tools/test_history.py data/junit-history
   ```
2. Pour chaque section du rapport, expliquez l'algorithme utilisé (lisez le code) :
   - **Flaky** : échecs isolés (un échec entouré de succès), score = échecs isolés / échecs
   - **Ralentissement** : pente d'une régression linéaire sur la durée
   - **Familles d'échecs** : TF-IDF sur les messages + clustering hiérarchique
3. Classez chaque famille : bug applicatif, test fragile, ou problème d'infrastructure ?
   Quelle action pour chacune (corriger, mettre en quarantaine, relancer automatiquement) ?
4. Avec un LLM configuré : `python ai_tools/test_history.py data/junit-history --explain`
   Les explications du LLM rejoignent-elles votre classement ?

## Partie C — Quality gate (20 min)
Ajoutez à votre pipeline (job séparé, planifié chaque jour) l'analyse de l'historique, avec le rapport
dans `$GITHUB_STEP_SUMMARY`. Bonus : `log_anomalies.py --fail-on-anomaly` après un test de charge
(le job échoue si une fenêtre dépasse un seuil absolu : 5xx ≥ 5 % ou p95 ≥ 500 ms, réglables par
`--gate-5xx-rate` et `--gate-p95-ms`). Pourquoi ne pas faire échouer le job sur les fenêtres « atypiques » ?

## Critères de réussite
- [ ] Tableau rappel/précision rempli et compromis argumenté
- [ ] Les 4 familles d'échecs identifiées et classées
- [ ] Le test flaky et le test qui ralentit sont identifiés
- [ ] Analyse quotidienne ajoutée à la CI

## Pour aller plus loin
- Remplacer IsolationForest par un autre détecteur (`LocalOutlierFactor`, `OneClassSVM`) et comparer.
- Stocker l'historique JUnit en vrai : artefacts de chaque run (`actions/download-artifact` + API GitHub).
- Outils du marché : Datadog Test Visibility, BuildPulse, Trunk Flaky Tests, Launchable.

## Sous Windows

Poste sous **WSL2** : rien à adapter. En **PowerShell**, voir aussi les règles générales de l'Atelier 0.

Les commandes `python scripts/…` et `python ai_tools/…` sont identiques. Seule l'étape A.4 change :
PowerShell ne lance pas une commande en arrière-plan avec `&`, il faut deux terminaux.

```powershell
# Terminal 1 — l'application avec journal, phase normale (Ctrl+C pour l'arrêter)
Remove-Item logs/app.jsonl -ErrorAction SilentlyContinue
$env:MINISHOP_LOG_FILE = "logs/app.jsonl"
uvicorn minishop.api:app

# Terminal 2 — la charge de référence
locust -f tests/perf/locustfile.py --host http://localhost:8000 --headless -u 20 -r 5 -t 60s

# Terminal 1 — Ctrl+C, puis l'application avec le ralentissement injecté
$env:MINISHOP_BUG = "slow"
uvicorn minishop.api:app

# Terminal 2 — la même charge, puis l'analyse
locust -f tests/perf/locustfile.py --host http://localhost:8000 --headless -u 20 -r 5 -t 60s
python ai_tools/log_anomalies.py logs/app.jsonl --window 5
```

Arrêtez l'application (Ctrl+C) et fermez le terminal 1 à la fin : les deux variables d'environnement
disparaissent avec lui.
