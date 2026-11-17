"""Atelier 6, étape 1 — exploration de data/git-history.csv et vérification de trois hypothèses.

Usage (depuis la racine du dépôt, après `python scripts/simulate_history.py`) :
    python ai_tools/explore_history.py data/git-history.csv
"""

from __future__ import annotations

import sys

import pandas as pd

pd.set_option("display.width", 120)


def taux(serie: pd.Series) -> pd.DataFrame:
    """Taux de casse et effectif par groupe."""
    return serie.agg(taux="mean", lignes="size").round({"taux": 3})


def main() -> int:
    df = pd.read_csv(sys.argv[1] if len(sys.argv) > 1 else "data/git-history.csv")
    df["num"] = df.commit.str[1:].astype(int)
    df["taille"] = df.lines_added + df.lines_deleted

    print(f"{len(df)} lignes, {df.commit.nunique()} commits")
    print(f"Taux de casse global : {df.broke_ci.mean():.3f}\n")
    print("Par fichier :")
    print(taux(df.groupby("file").broke_ci).sort_values("taux"), "\n")
    print("Par auteur :")
    print(taux(df.groupby("author").broke_ci), "\n")

    print("H1 — les gros changements cassent plus (taille = lignes ajoutées + supprimées)")
    tranches = pd.cut(df.taille, [0, 10, 25, 50, 100, 10_000], labels=["1-10", "11-25", "26-50", "51-100", ">100"])
    print(taux(df.groupby(tranches, observed=True).broke_ci))
    print(f"corrélation taille / casse : {df.taille.corr(df.broke_ci):+.3f}\n")

    print("H2 — les commits tardifs (20 h et après) cassent plus")
    print(taux(df.groupby(df.hour >= 20).broke_ci).rename(index={False: "avant 20 h", True: "20 h et après"}), "\n")

    print("H3 — emma casse plus que les autres… mais seulement au début (commits 1 à 299)")
    periode = df.num.lt(300).map({True: "commits 1-299", False: "commits 300-600"})
    qui = df.author.eq("emma").map({True: "emma", False: "autres"})
    print(df.pivot_table(index=qui, columns=periode, values="broke_ci", aggfunc="mean").round(3), "\n")

    print("Complément — commits de correction, nombre de fichiers du commit")
    print(taux(df.groupby("is_fix_commit").broke_ci))
    print(taux(df.groupby("files_in_commit").broke_ci))
    return 0


if __name__ == "__main__":
    sys.exit(main())
