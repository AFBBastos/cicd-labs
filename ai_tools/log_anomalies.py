"""Détection d'anomalies dans des logs applicatifs JSON (une ligne = une requête).

Approche (apprentissage NON supervisé) :
  1. Fenêtrage : on agrège les logs par fenêtres de N secondes
     (nb requêtes, taux d'erreurs 5xx/4xx, latence p50/p95/max, chemins inconnus).
  2. IsolationForest isole les fenêtres « atypiques » sans avoir besoin d'exemples étiquetés.
  3. En complément, une règle simple par requête (z-score robuste de la latence
     par route, avec un plancher absolu en millisecondes) pour pointer les requêtes précises.

Deux remarques pour lire le rapport :
  * « atypique » ne veut pas dire « grave » : avec --contamination 0.02, l'IsolationForest signale
    toujours environ 2 % des fenêtres, même si tout va bien. C'est un classement, pas un verdict.
  * --fail-on-anomaly (barrière de CI) repose donc sur un critère ABSOLU : code retour 1 si au
    moins une fenêtre a un taux de 5xx >= --gate-5xx-rate ou une latence p95 >= --gate-p95-ms.

Si les logs contiennent la vérité terrain (`_truth`, données simulées), le rapport évalue les deux
techniques séparément : au niveau FENÊTRE (IsolationForest ; dépend de --window et --contamination)
et au niveau REQUÊTE (z-score ; dépend de --z-threshold et --min-latency-ms).

Usage :
    python ai_tools/log_anomalies.py data/app-logs.jsonl --window 30 --contamination 0.02
    python ai_tools/log_anomalies.py data/app-logs.jsonl --z-threshold 3 --min-latency-ms 0
    python ai_tools/log_anomalies.py logs/app.jsonl --window 5 --fail-on-anomaly   # barrière de CI
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.ensemble import IsolationForest

KNOWN_PATHS = {
    "/products",
    "/products/{product_id}",
    "/cart/quote",
    "/orders",
    "/orders/{order_id}",
    "/health",
    "/metrics",
    "/",
    "/openapi.json",
    "/docs",
}


def load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def windows(logs: list[dict], size: int) -> tuple[list[int], np.ndarray]:
    buckets: dict[int, list[dict]] = defaultdict(list)
    for e in logs:
        buckets[int(e["ts"] // size)].append(e)
    keys = sorted(buckets)
    feats = []
    for k in keys:
        b = buckets[k]
        lat = sorted(e["latency_ms"] for e in b)
        feats.append(
            [
                len(b),
                sum(e["status"] >= 500 for e in b) / len(b),
                sum(400 <= e["status"] < 500 for e in b) / len(b),
                lat[len(lat) // 2],
                lat[int(len(lat) * 0.95) - 1 if len(lat) > 1 else 0],
                lat[-1],
                sum(e["path"] not in KNOWN_PATHS for e in b),
            ]
        )
    return keys, np.array(feats)


def per_request_outliers(logs: list[dict], threshold: float = 6.0, min_latency_ms: float = 100.0) -> list[dict]:
    """Requêtes lentes pour leur route (z-score robuste > seuil ET latence >= plancher) ou sur un chemin inconnu.

    Le plancher évite de signaler une requête à 4 ms sous prétexte que la médiane de la route est à 0,6 ms.
    """
    by_path: dict[str, list[float]] = defaultdict(list)
    for e in logs:
        by_path[e["path"]].append(e["latency_ms"])
    stats = {}
    for p, v in by_path.items():
        med = statistics.median(v)
        mad = statistics.median(abs(x - med) for x in v) or 1.0
        stats[p] = (med, mad)
    out = []
    for e in logs:
        med, mad = stats[e["path"]]
        z = 0.6745 * (e["latency_ms"] - med) / mad
        if (z > threshold and e["latency_ms"] >= min_latency_ms) or e["path"] not in KNOWN_PATHS:
            out.append({**e, "robust_z": round(z, 1)})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("logfile", type=Path)
    ap.add_argument("--window", type=int, default=30, help="taille des fenêtres en secondes")
    ap.add_argument("--contamination", type=float, default=0.02, help="part d'anomalies attendue")
    ap.add_argument("--report", type=Path, default=Path("reports/anomalies.md"))
    ap.add_argument("--z-threshold", type=float, default=6.0, help="seuil du z-score robuste (règle par requête)")
    ap.add_argument(
        "--min-latency-ms", type=float, default=100.0, help="plancher : en dessous, une requête n'est jamais « lente »"
    )
    ap.add_argument(
        "--fail-on-anomaly",
        action="store_true",
        help="barrière de CI : code retour 1 si une fenêtre dépasse --gate-5xx-rate ou --gate-p95-ms",
    )
    ap.add_argument("--gate-5xx-rate", type=float, default=0.05, help="taux de 5xx par fenêtre jugé grave")
    ap.add_argument("--gate-p95-ms", type=float, default=500.0, help="latence p95 par fenêtre jugée grave (ms)")
    args = ap.parse_args()

    logs = load(args.logfile)
    keys, X = windows(logs, args.window)
    # Fenêtres GRAVES : critère absolu, indépendant du modèle (c'est lui qui décide de la barrière)
    severe = [i for i in range(len(keys)) if X[i][1] >= args.gate_5xx_rate or X[i][4] >= args.gate_p95_ms]
    gate = (
        f"{len(severe)} fenêtre(s) sur {len(keys)} avec 5xx >= {args.gate_5xx_rate:.0%} "
        f"ou p95 >= {args.gate_p95_ms:.0f} ms"
    )
    if len(keys) < 10:
        print("Pas assez de données pour un modèle (min. 10 fenêtres).")
        print(f"Fenêtres graves (critère absolu) : {gate}")
        return 1 if (args.fail_on_anomaly and severe) else 0
    model = IsolationForest(contamination=args.contamination, random_state=0).fit(X)
    scores = model.decision_function(X)
    flagged = [(keys[i], scores[i], X[i]) for i in np.where(model.predict(X) == -1)[0]]
    flagged.sort(key=lambda t: t[1])
    outliers = per_request_outliers(logs, args.z_threshold, args.min_latency_ms)

    lines = [
        "# Rapport d'anomalies",
        "",
        f"- Fichier : `{args.logfile}` — {len(logs)} requêtes, {len(keys)} fenêtres de {args.window}s",
        f"- Fenêtres anormales (IsolationForest) : **{len(flagged)}**",
        f"- Requêtes atypiques (z-score robuste > {args.z_threshold:g} et latence >= {args.min_latency_ms:g} ms, "
        f"ou chemin inconnu) : **{len(outliers)}**",
        f"- Fenêtres graves (critère absolu de --fail-on-anomaly) : **{gate}**",
        "",
        "## Fenêtres les plus atypiques",
        "",
        "| Début (ts) | Score | Req. | 5xx | 4xx | p50 ms | p95 ms | max ms | chemins inconnus |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for k, s, f in flagged[:15]:
        lines.append(
            f"| {k * args.window} | {s:.3f} | {int(f[0])} | {f[1]:.0%} | {f[2]:.0%} | "
            f"{f[3]:.0f} | {f[4]:.0f} | {f[5]:.0f} | {int(f[6])} |"
        )
    lines += [
        "",
        "## Exemples de requêtes atypiques",
        "",
        "| ts | méthode | chemin | statut | latence ms | z |",
        "|---|---|---|---|---|---|",
    ]
    for e in outliers[:20]:
        lines.append(
            f"| {e['ts']} | {e['method']} | `{e['path']}` | {e['status']} | {e['latency_ms']} | {e['robust_z']} |"
        )

    # Évaluation si les données contiennent la vérité terrain (données simulées)
    evaluation: list[str] = []
    if any("_truth" in e for e in logs):
        # Niveau fenêtre : une fenêtre est réellement anormale si elle contient au moins une requête étiquetée
        true_windows = {int(e["ts"] // args.window) for e in logs if e.get("_truth")}
        flagged_windows = {k for k, _, _ in flagged}
        hit_w = flagged_windows & true_windows
        # Niveau requête
        truth = sum(1 for e in logs if e.get("_truth"))
        found = sum(1 for o in outliers if o.get("_truth"))
        evaluation = [
            "",
            "## Évaluation (données simulées)",
            "",
            f"- Niveau fenêtre (IsolationForest) — rappel : {len(hit_w)}/{len(true_windows)} fenêtres anormales "
            f"signalées ({len(hit_w) / max(len(true_windows), 1):.0%}) ; précision : {len(hit_w)}/{len(flagged_windows)} "
            f"signalements justes ({len(hit_w) / max(len(flagged_windows), 1):.0%})",
            f"- Niveau requête (z-score / chemin inconnu) — rappel : {found}/{truth} requêtes anormales signalées "
            f"({found / max(truth, 1):.0%}) ; précision : {found}/{len(outliers)} signalements justes "
            f"({found / max(len(outliers), 1):.0%})",
        ]
        lines += evaluation

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:7] + evaluation))
    print(f"\nRapport complet : {args.report}")
    if args.fail_on_anomaly and severe:
        print(f"ÉCHEC de la barrière : {gate}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
