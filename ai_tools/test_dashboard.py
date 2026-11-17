"""Atelier 6, étape 5 — tableau de bord texte : où investir l'effort de test ?

Croise, pour chaque module :
  * la couverture                 (reports/coverage.json, produit par `coverage json`) ;
  * le score de mutation          (reports/mutation-<module>.txt, sortie de mutation_score.py) ;
  * l'historique Git              (data/git-history.csv : modifications et taux de casse) ;
  * les échecs de tests           (data/junit-history/*.xml, rattachés à un module par HISTORY_MAP) ;
  * le risque prédit par le modèle (reports/risk_model.pkl, pour un changement type).

Préparation (depuis la racine du dépôt) :
    python scripts/simulate_history.py
    python ai_tools/risk_model.py train data/git-history.csv
    pytest -m "not e2e and not visual" --cov && coverage json -o reports/coverage.json
    python ai_tools/mutation_score.py minishop/pricing.py tests/unit > reports/mutation-pricing.txt
    python ai_tools/mutation_score.py minishop/api.py tests/api      > reports/mutation-api.txt
    python ai_tools/mutation_score.py minishop/catalog.py tests/unit > reports/mutation-catalog.txt
Puis :
    python ai_tools/test_dashboard.py            # affiche et écrit reports/test-dashboard.md

Une donnée absente est affichée « n.d. » : c'est une information en soi (module non mesuré).
"""

from __future__ import annotations

import argparse
import csv
import json
import pickle  # noqa: S403 — modèle produit localement par risk_model.py
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ai_tools.test_history import load_runs  # noqa: E402

# Rattachement des tests de l'historique JUnit à un module (hypothèse de lecture, à adapter au projet).
# La clé la plus longue qui préfixe « classname::test » l'emporte.
HISTORY_MAP = {
    "tests.unit.test_pricing": "minishop/pricing.py",
    "tests.api.test_api": "minishop/api.py",
    "tests.api.test_api::test_recherche_produits": "minishop/search.py",
    "tests.e2e.test_parcours_achat": "minishop/static/index.html",
    "tests.integration.test_stock": "minishop/stock.py",
}
# Échecs à ne pas imputer au module : pannes d'environnement (voir Atelier 5, familles d'échecs).
INFRA = ("Connection refused", "could not connect")
# Changement type utilisé pour le risque prédit : mêmes valeurs que `risk_model.py predict --files <f>`.
CHANGE = {"added": 30, "deleted": 10, "files": 1, "author": "alice", "hour": 15}


def coverage_by_file(path: Path) -> dict[str, float]:
    if not path.exists():
        return {}
    files = json.loads(path.read_text(encoding="utf-8"))["files"]
    return {f.replace("\\", "/"): d["summary"]["percent_covered"] for f, d in files.items()}


def mutation_by_file(folder: Path, modules: list[str]) -> dict[str, tuple[int, int]]:
    out = {}
    for m in modules:
        f = folder / f"mutation-{Path(m).stem}.txt"
        if f.exists():
            found = re.search(r"Score de mutation : (\d+)/(\d+)", f.read_text(encoding="utf-8", errors="replace"))
            if found:
                out[m] = (int(found.group(1)), int(found.group(2)))
    return out


def git_stats(path: Path) -> dict[str, tuple[int, float]]:
    n, b = Counter(), Counter()
    with path.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            n[r["file"]] += 1
            b[r["file"]] += int(r["broke_ci"])
    return {f: (n[f], b[f] / n[f]) for f in n}


def history_failures(folder: Path) -> dict[str, dict[str, int]]:
    """Par module : échecs imputables au code ou au test (« code ») et pannes d'environnement (« infra »)."""
    out: dict[str, dict[str, int]] = defaultdict(lambda: {"code": 0, "infra": 0})
    keys = sorted(HISTORY_MAP, key=len, reverse=True)
    for run in load_runs(folder):
        for name, case in run["cases"].items():
            if not case["failed"]:
                continue
            module = next((HISTORY_MAP[k] for k in keys if name.startswith(k)), "(non rattaché)")
            out[module]["infra" if any(s in case["message"] for s in INFRA) else "code"] += 1
    return out


def predicted_risk(model_path: Path, files: list[str]) -> dict[str, float]:
    if not model_path.exists():
        return {}
    bundle = pickle.loads(model_path.read_bytes())  # noqa: S301
    m, st = bundle["model"], bundle["state"]
    ac, ab = st["author_commits"].get(CHANGE["author"], 0), st["author_breaks"].get(CHANGE["author"], 0)
    out = {}
    for f in files:
        fc, fb = st["file_commits"].get(f, 0), st["file_breaks"].get(f, 0)
        x = [
            CHANGE["added"],
            CHANGE["deleted"],
            CHANGE["files"],
            0,
            int(CHANGE["hour"] >= 20),
            fc,
            fb / fc if fc else 0.0,
            ab / ac if ac else 0.0,
            int(f.endswith((".py", ".html", ".js"))),
        ]
        out[f] = float(m.predict_proba(np.array([x], dtype=float))[0, 1])
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--git-history", type=Path, default=Path("data/git-history.csv"))
    ap.add_argument("--junit", type=Path, default=Path("data/junit-history"))
    ap.add_argument("--reports", type=Path, default=Path("reports"))
    ap.add_argument("--out", type=Path, default=Path("reports/test-dashboard.md"))
    args = ap.parse_args()

    git = git_stats(args.git_history)
    modules = sorted(f for f in git if f.startswith("minishop/"))
    cov = coverage_by_file(args.reports / "coverage.json")
    mut = mutation_by_file(args.reports, modules)
    fails = history_failures(args.junit)
    risk = predicted_risk(args.reports / "risk_model.pkl", modules)

    rows = []
    for m in modules:
        # Protection = ce que l'on sait de mieux sur la capacité des tests à détecter un bug dans ce module :
        # le score de mutation s'il existe, sinon la couverture, sinon 0 (rien de mesuré).
        if m in mut:
            protection = mut[m][0] / max(mut[m][1], 1)
        elif m in cov:
            protection = cov[m] / 100
        else:
            protection = 0.0
        rows.append((risk.get(m, 0.0) * (1 - protection), m))
    rows.sort(reverse=True)

    L = [
        "# Tableau de bord des tests par module",
        "",
        "| Module | Couverture | Score de mutation | Modifs (Git) | Taux de casse | Échecs historiques (code / infra) "
        "| Risque prédit | Priorité |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for prio, m in rows:
        c = f"{cov[m]:.0f} %" if m in cov else "n.d."
        s = f"{mut[m][0]}/{mut[m][1]} = {mut[m][0] / max(mut[m][1], 1):.0%}" if m in mut else "n.d."
        f = fails.get(m, {"code": 0, "infra": 0})
        r = f"{risk[m]:.1%}" if m in risk else "n.d."
        L.append(
            f"| `{m}` | {c} | {s} | {git[m][0]} | {git[m][1]:.1%} | {f['code']} / {f['infra']} | {r} | {prio:.3f} |"
        )
    L += [
        "",
        "Priorité = risque prédit × (1 − protection) ; protection = score de mutation, à défaut couverture, "
        "à défaut 0.",
        f"Risque prédit pour un changement type : {CHANGE['added']} lignes ajoutées, {CHANGE['deleted']} supprimées, "
        f"fichier seul dans son commit, {CHANGE['hour']} h.",
    ]
    autres = {m: f for m, f in fails.items() if m not in modules}
    if autres:
        L.append(f"Échecs non rattachés à un module suivi : {dict(autres)}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
