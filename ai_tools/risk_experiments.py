"""Atelier 6, étape 3 — comparer des variantes du modèle de risque sans modifier risk_model.py.

Même découpage que `risk_model.py train` : validation temporelle, 75 % de lignes les plus anciennes
pour apprendre, 25 % les plus récentes pour évaluer. Pour chaque variante : AUC, rappel et précision
sur la classe « casse », matrice de confusion, et coût des erreurs
(faux positif = 2 min de tests lancés pour rien, faux négatif = 60 min de débogage).

Usage (depuis la racine du dépôt, après `python scripts/simulate_history.py`) :
    python ai_tools/risk_experiments.py data/git-history.csv
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, roc_auc_score
from sklearn.model_selection import train_test_split

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ai_tools.risk_model import FEATURES, featurize, load  # noqa: E402

COUT_FP_MIN = 2  # tests ciblés lancés pour rien
COUT_FN_MIN = 60  # casse non anticipée : débogage
COL = {name: i for i, name in enumerate(FEATURES)}


def nouvelles_variables(X: np.ndarray) -> np.ndarray:
    """Deux variables ajoutées, dérivées de colonnes déjà « sans fuite » de featurize().

    - taille          : lines_added + lines_deleted (suggestion de l'énoncé) ;
    - risque_x_taille : taux de casse passé du fichier × (1 + taille / 150), taille plafonnée à 300.
                        Idée issue de l'exploration : un gros changement dans un fichier fragile
                        est plus dangereux que la somme des deux effets (interaction).
    """
    taille = X[:, COL["lines_added"]] + X[:, COL["lines_deleted"]]
    inter = X[:, COL["file_past_breaks_rate"]] * (1 + np.minimum(taille, 300) / 150)
    return np.column_stack([taille, inter])


def evaluer(nom: str, modele, X: np.ndarray, y: np.ndarray, cut: int, seuil: float = 0.5) -> dict:
    modele.fit(X[:cut], y[:cut])
    proba = modele.predict_proba(X[cut:])[:, 1]
    tn, fp, fn, tp = confusion_matrix(y[cut:], (proba >= seuil).astype(int), labels=[0, 1]).ravel()
    return {
        "nom": nom,
        "auc": roc_auc_score(y[cut:], proba),
        "rappel": tp / max(tp + fn, 1),
        "precision": tp / max(tp + fp, 1),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "cout": COUT_FP_MIN * fp + COUT_FN_MIN * fn,
        "proba": proba,
    }


def ligne(r: dict) -> str:
    return (
        f"| {r['nom']} | {r['auc']:.3f} | {r['rappel']:.0%} | {r['precision']:.0%} | "
        f"{r['tp']} | {r['fp']} | {r['fn']} | {r['cout']} |"
    )


def main() -> int:
    rows = load(Path(sys.argv[1] if len(sys.argv) > 1 else "data/git-history.csv"))
    X, y, _ = featurize(rows)
    extra = nouvelles_variables(X)
    X_taille = np.hstack([X, extra[:, :1]])
    X_inter = np.hstack([X, extra[:, 1:]])
    X_sans_auteur = np.delete(X, COL["author_past_breaks_rate"], axis=1)
    cut = int(len(X) * 0.75)
    n_test, n_casse = len(y) - cut, int(y[cut:].sum())
    print(f"{len(X)} lignes — apprentissage sur {cut}, test sur {n_test} dont {n_casse} casses\n")

    def lr(**kw):
        return LogisticRegression(max_iter=1000, **kw)

    def rf(**kw):
        return RandomForestClassifier(random_state=0, **kw)

    resultats = [
        evaluer("Défaut (régression logistique, seuil 0,5)", lr(), X, y, cut),
        evaluer('`class_weight="balanced"`', lr(class_weight="balanced"), X, y, cut),
        evaluer("Seuil de décision 0,3", lr(), X, y, cut, seuil=0.3),
        evaluer("`RandomForestClassifier`", rf(), X, y, cut),
        evaluer("Nouvelle variable `taille`", lr(), X_taille, y, cut),
        evaluer("Nouvelle variable `risque_x_taille`", lr(), X_inter, y, cut),
        evaluer("`risque_x_taille` + `balanced`", lr(class_weight="balanced"), X_inter, y, cut),
    ]
    entete = "| Variante | AUC | Rappel casse | Précision casse | VP | FP | FN | Coût (min) |"
    print(entete)
    print("|---|---|---|---|---|---|---|---|")
    for r in resultats:
        print(ligne(r))

    print("\nPour comparaison (hors énoncé) :")
    print(entete)
    print("|---|---|---|---|---|---|---|---|")
    autres = [
        evaluer("Gradient boosting (défaut du script)", GradientBoostingClassifier(random_state=0), X, y, cut),
        evaluer("Random forest + `balanced`", rf(class_weight="balanced"), X, y, cut),
        evaluer("Random forest, seuil 0,3", rf(), X, y, cut, seuil=0.3),
        evaluer("Régression logistique, seuil 0,1", lr(), X, y, cut, seuil=0.1),
        evaluer("Une seule variable : `risque_x_taille`", lr(), extra[:, 1:], y, cut),
        evaluer("Sans `author_past_breaks_rate`", lr(), X_sans_auteur, y, cut),
        evaluer("Sans `author_past_breaks_rate` + `balanced`", lr(class_weight="balanced"), X_sans_auteur, y, cut),
    ]
    for r in autres:
        print(ligne(r))

    print("\nRéférences sans modèle :")
    print(f"  ne jamais alerter  : {n_casse} FN -> {COUT_FN_MIN * n_casse} min")
    print(f"  toujours alerter   : {n_test - n_casse} FP -> {COUT_FP_MIN * (n_test - n_casse)} min")

    print("\nSeuil qui minimise le coût (régression logistique par défaut) :")
    proba, yt = resultats[0]["proba"], y[cut:]
    meilleurs = []
    for s in np.arange(0.02, 0.61, 0.02):
        pred = proba >= s
        fp, fn = int((pred & (yt == 0)).sum()), int((~pred & (yt == 1)).sum())
        meilleurs.append((COUT_FP_MIN * fp + COUT_FN_MIN * fn, round(float(s), 2), fp, fn))
    for cout, s, fp, fn in sorted(meilleurs)[:5]:
        print(f"  seuil {s:.2f} : {fp} FP, {fn} FN -> {cout} min")
    theorique = COUT_FP_MIN / (COUT_FP_MIN + COUT_FN_MIN)
    print(f"  seuil théorique si les probabilités sont calibrées : {theorique:.3f}")

    print("\nDémonstration de la fuite de données (à ne PAS faire) :")
    # 1) taux par fichier et par auteur calculés sur TOUT l'historique, futur compris
    f_n, f_b, a_n, a_b, c_n, c_b = (defaultdict(int) for _ in range(6))
    for r in rows:
        casse = int(r["broke_ci"])
        f_n[r["file"]] += 1
        f_b[r["file"]] += casse
        a_n[r["author"]] += 1
        a_b[r["author"]] += casse
        c_n[r["commit"]] += 1
        c_b[r["commit"]] += casse
    X_fuite = X.copy()
    X_fuite[:, COL["file_past_breaks_rate"]] = [f_b[r["file"]] / f_n[r["file"]] for r in rows]
    X_fuite[:, COL["author_past_breaks_rate"]] = [a_b[r["author"]] / a_n[r["author"]] for r in rows]
    print(f"  taux calculés sur tout l'historique         : AUC {evaluer('', lr(), X_fuite, y, cut)['auc']:.3f}")
    # 2) une variable qui contient l'étiquette de la ligne elle-même : taux de casse du commit
    X_commit = np.column_stack([X, [c_b[r["commit"]] / c_n[r["commit"]] for r in rows]])
    print(f"  + taux de casse du commit (contient la cible) : AUC {evaluer('', lr(), X_commit, y, cut)['auc']:.3f}")

    print("\nDécoupage aléatoire au lieu de temporel (20 graines, régression logistique) :")
    aucs = []
    for graine in range(20):
        Xa, Xb, ya, yb = train_test_split(X, y, test_size=0.25, random_state=graine, stratify=y)
        aucs.append(roc_auc_score(yb, lr().fit(Xa, ya).predict_proba(Xb)[:, 1]))
    print(f"  AUC moyenne {np.mean(aucs):.3f}, de {min(aucs):.3f} à {max(aucs):.3f} selon le tirage")
    return 0


if __name__ == "__main__":
    sys.exit(main())
