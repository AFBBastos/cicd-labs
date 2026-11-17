"""Atelier 5 — balayage des réglages de log_anomalies.py en une seule commande.

`log_anomalies.py` évalue un réglage à la fois (niveau fenêtre et niveau requête). Ce script reprend
les mêmes définitions et affiche d'un coup plusieurs couples (fenêtre, contamination), pour remplir
le tableau de l'étape A.3 et discuter le compromis. Une fenêtre est « réellement anormale » si elle
contient au moins une requête étiquetée dans `_truth` ; `--min-anomalies` permet de ne compter que
les incidents massifs.

Usage (depuis la racine du dépôt, après `python scripts/simulate_history.py`) :
    python ai_tools/eval_fenetres.py data/app-logs.jsonl
    python ai_tools/eval_fenetres.py data/app-logs.jsonl --min-anomalies 5
    python ai_tools/eval_fenetres.py data/app-logs.jsonl --z 3 --min-latency-ms 0
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.ensemble import IsolationForest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ai_tools.log_anomalies import load, per_request_outliers, windows  # noqa: E402

REGLAGES = [(30, 0.02), (30, 0.10), (5, 0.02), (5, 0.10), (60, 0.02)]


def evaluer(logs: list[dict], window: int, contamination: float, min_anomalies: int) -> dict:
    keys, X = windows(logs, window)
    pred = IsolationForest(contamination=contamination, random_state=0).fit(X).predict(X)
    signalees = {keys[i] for i in np.where(pred == -1)[0]}
    par_fenetre = Counter(int(e["ts"] // window) for e in logs if e.get("_truth"))
    vraies = {k for k, n in par_fenetre.items() if n >= min_anomalies}
    burst = {int(e["ts"] // window) for e in logs if e.get("_truth") == "burst_500"}
    ok = signalees & vraies
    return {
        "fenetres": len(keys),
        "signalees": len(signalees),
        "vraies": len(vraies),
        "rappel": len(ok) / max(len(vraies), 1),
        "precision": len(ok) / max(len(signalees), 1),
        "burst": f"{len(burst & signalees)}/{len(burst)}",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("logfile", type=Path)
    ap.add_argument("--min-anomalies", type=int, default=1, help="nb min. de requêtes anormales par fenêtre")
    ap.add_argument("--z", type=float, default=6.0, help="seuil du z-score robuste (règle par requête)")
    ap.add_argument("--min-latency-ms", type=float, default=100.0, help="plancher de la règle par requête")
    args = ap.parse_args()
    logs = load(args.logfile)

    print("IsolationForest, niveau fenêtre")
    print(
        "| Fenêtre | Contamination | Fenêtres | Signalées | Réellement anormales | Rappel | Précision | Rafale 500 vue |"
    )
    print("|---|---|---|---|---|---|---|---|")
    for w, c in REGLAGES:
        r = evaluer(logs, w, c, args.min_anomalies)
        print(
            f"| {w} s | {c:.2f} | {r['fenetres']} | {r['signalees']} | {r['vraies']} | "
            f"{r['rappel']:.0%} | {r['precision']:.0%} | {r['burst']} |"
        )

    out = per_request_outliers(logs, threshold=args.z, min_latency_ms=args.min_latency_ms)
    vrais = sum(1 for o in out if o.get("_truth"))
    total = sum(1 for e in logs if e.get("_truth"))
    print(
        f"\nRègle par requête, seuil z = {args.z:g}, plancher {args.min_latency_ms:g} ms : "
        f"{len(out)} signalements, dont {vrais} vrais"
    )
    print(f"  rappel {vrais}/{total} = {vrais / max(total, 1):.0%} ; précision {vrais / max(len(out), 1):.0%}")
    faux = [o for o in out if not o.get("_truth")]
    for o in faux[:10]:
        print(f"  faux positif : {o['path']} {o['latency_ms']} ms (z = {o['robust_z']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
