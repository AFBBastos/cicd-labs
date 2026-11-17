"""Atelier 6, étape 4 — déduire la table fichier -> tests de la couverture, au lieu de TEST_MAP manuelle.

Principe : avec `--cov-context=test`, coverage.py note pour chaque ligne exécutée QUEL test l'a
exécutée. On en déduit, pour chaque fichier source, les fichiers de test qui le traversent, classés
par nombre de lignes couvertes (les plus pertinents d'abord).

Usage (depuis la racine du dépôt) :
    pytest -m "not e2e and not visual" --cov --cov-context=test
    coverage json --show-contexts -o reports/coverage-contexts.json
    python ai_tools/coverage_test_map.py                 # écrit reports/test_map.json
    python ai_tools/coverage_test_map.py --min-lines 3   # ignore les tests qui ne font qu'effleurer

Limites : seuls les fichiers Python mesurés apparaissent. Les fichiers statiques (HTML, CSS) ne sont
pas « couverts » : on garde pour eux une règle manuelle (STATIC_RULES). Les tests e2e pilotent un
serveur dans un autre processus : sans configuration particulière, ils ne laissent pas de trace ici.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

STATIC_RULES = {"minishop/static/": ["tests/e2e", "tests/visual"]}


def build(report: dict, min_lines: int) -> tuple[dict[str, list[str]], dict[str, dict[str, int]]]:
    """Retourne (table fichier -> fichiers de test triés, détail fichier -> {fichier de test: lignes})."""
    detail: dict[str, dict[str, set]] = defaultdict(lambda: defaultdict(set))
    for source, data in report["files"].items():
        for line, contexts in data.get("contexts", {}).items():
            for ctx in contexts:
                if not ctx:  # contexte vide = exécuté à l'import, hors de tout test
                    continue
                test_id = ctx.split("|")[0]  # « tests/x.py::test_y|run » -> « tests/x.py::test_y »
                detail[source][test_id.split("::")[0]].add(line)
    table, counts = {}, {}
    for source in sorted(detail):
        c = {t: len(lines) for t, lines in detail[source].items() if len(lines) >= min_lines}
        if c:
            counts[source] = dict(sorted(c.items(), key=lambda kv: (-kv[1], kv[0])))
            table[source] = list(counts[source])
    return table, counts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--coverage-json", type=Path, default=Path("reports/coverage-contexts.json"))
    ap.add_argument("--out", type=Path, default=Path("reports/test_map.json"))
    ap.add_argument("--min-lines", type=int, default=1, help="nb min. de lignes du fichier exécutées par le test")
    args = ap.parse_args()

    report = json.loads(args.coverage_json.read_text(encoding="utf-8"))
    if not report.get("meta", {}).get("show_contexts"):
        print("Rapport sans contextes : relancez `coverage json --show-contexts`.")
        return 2
    table, counts = build(report, args.min_lines)
    if not table:
        print("Aucun contexte de test : relancez pytest avec `--cov --cov-context=test`.")
        return 2

    print("| Fichier source | Fichier de test | Lignes du fichier exécutées par ces tests |")
    print("|---|---|---|")
    for source, tests in counts.items():
        for test, n in tests.items():
            print(f"| `{source}` | `{test}` | {n} |")
    table.update(STATIC_RULES)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(table, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nTable écrite dans {args.out} ({len(table)} entrées, dont {len(STATIC_RULES)} règle(s) manuelle(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
