"""Comparaison visuelle de captures d'écran — SOLUTION Atelier 7.

Version corrigée de l'outil du dépôt stagiaires. Le SSIM d'origine est calculé sur une
image convertie en niveaux de gris : deux couleurs de même luminance (le vert #1f7a5a et
le bleu #2563eb, par exemple) y deviennent presque le même gris, et le changement passe
inaperçu. Deux corrections, indépendantes l'une de l'autre :

  * SSIM par canal : le SSIM est calculé séparément sur R, V et B, on garde le plus
    mauvais des trois ;
  * ΔE (CIE76) : distance entre les deux couleurs d'un même pixel dans l'espace Lab,
    proche de l'écart perçu par l'œil. On compte la part de pixels dont le ΔE dépasse
    un seuil (10 par défaut : un écart visible au premier regard).

L'interface est compatible avec l'outil d'origine : `compare()` renvoie un résultat dont
`ssim` est désormais le SSIM par canal ; l'ancien calcul reste disponible dans `ssim_gray`.

Usage :
    python ai_tools/visual_diff.py baseline.png current.png --diff diff.png
    # code retour 1 si la différence dépasse les seuils
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

MAX_DIFF = 0.002  # part maximale de pixels différents (0,2 %)
MIN_SSIM = 0.99  # SSIM par canal minimal
MAX_DELTA_E_RATIO = 0.001  # part maximale de pixels dont le ΔE dépasse le seuil


@dataclass
class VisualResult:
    diff_ratio: float
    ssim: float  # SSIM par canal (le plus mauvais des trois canaux)
    size_mismatch: bool
    ssim_gray: float = 1.0  # ancien calcul, conservé pour comparer
    delta_e_mean: float = 0.0  # ΔE moyen sur toute l'image
    delta_e_ratio: float = 0.0  # part de pixels dont le ΔE dépasse le seuil

    def ok(self, max_diff: float, min_ssim: float, max_delta_e_ratio: float = MAX_DELTA_E_RATIO) -> bool:
        return (
            not self.size_mismatch
            and self.diff_ratio <= max_diff
            and self.ssim >= min_ssim
            and self.delta_e_ratio <= max_delta_e_ratio
        )


def _gray(a: np.ndarray) -> np.ndarray:
    return a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114


def ssim(x: np.ndarray, y: np.ndarray, win: int = 8) -> float:
    """SSIM moyen sur fenêtres non chevauchantes (implémentation pédagogique)."""
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    h, w = (x.shape[0] // win) * win, (x.shape[1] // win) * win
    xb = x[:h, :w].reshape(h // win, win, w // win, win).swapaxes(1, 2).reshape(-1, win * win)
    yb = y[:h, :w].reshape(h // win, win, w // win, win).swapaxes(1, 2).reshape(-1, win * win)
    mx, my = xb.mean(1), yb.mean(1)
    vx, vy = xb.var(1), yb.var(1)
    cov = ((xb - mx[:, None]) * (yb - my[:, None])).mean(1)
    s = ((2 * mx * my + c1) * (2 * cov + c2)) / ((mx**2 + my**2 + c1) * (vx + vy + c2))
    return float(s.mean())


def ssim_per_channel(a: np.ndarray, b: np.ndarray) -> float:
    """SSIM calculé sur chaque canal R, V, B : on retient le plus mauvais."""
    return min(ssim(a[..., c], b[..., c]) for c in range(3))


def rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """sRGB (0-255) -> CIE Lab, illuminant D65."""
    c = rgb / 255.0
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    m = np.array(
        [
            [0.4124564, 0.3575761, 0.1804375],
            [0.2126729, 0.7151522, 0.0721750],
            [0.0193339, 0.1191920, 0.9503041],
        ]
    )
    xyz = lin @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], axis=-1)


def delta_e(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """ΔE CIE76 par pixel : distance euclidienne dans l'espace Lab."""
    return np.sqrt(((rgb_to_lab(a) - rgb_to_lab(b)) ** 2).sum(axis=-1))


def compare(
    baseline: Path,
    current: Path,
    diff_out: Path | None = None,
    tolerance: int = 16,
    delta_e_threshold: float = 10.0,
) -> VisualResult:
    a = np.asarray(Image.open(baseline).convert("RGB"), dtype=np.float64)
    b = np.asarray(Image.open(current).convert("RGB"), dtype=np.float64)
    if a.shape != b.shape:
        return VisualResult(1.0, 0.0, True, 0.0, 100.0, 1.0)
    changed = (np.abs(a - b) > tolerance).any(axis=2)
    if diff_out:
        out = (a * 0.3 + 178).astype(np.uint8)
        out[changed] = [255, 0, 255]
        diff_out.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(out).save(diff_out)
    de = delta_e(a, b)
    return VisualResult(
        diff_ratio=float(changed.mean()),
        ssim=ssim_per_channel(a, b),
        size_mismatch=False,
        ssim_gray=ssim(_gray(a), _gray(b)),
        delta_e_mean=float(de.mean()),
        delta_e_ratio=float((de > delta_e_threshold).mean()),
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("baseline", type=Path)
    ap.add_argument("current", type=Path)
    ap.add_argument("--diff", type=Path)
    ap.add_argument("--max-diff", type=float, default=MAX_DIFF, help="part max de pixels différents")
    ap.add_argument("--min-ssim", type=float, default=MIN_SSIM, help="SSIM par canal minimal")
    ap.add_argument(
        "--max-delta-e-ratio", type=float, default=MAX_DELTA_E_RATIO, help="part max de pixels dont le ΔE dépasse 10"
    )
    args = ap.parse_args()
    r = compare(args.baseline, args.current, args.diff)
    print(
        f"pixels différents : {r.diff_ratio:.4%} | SSIM par canal : {r.ssim:.4f} (gris : {r.ssim_gray:.4f}) | "
        f"ΔE moyen : {r.delta_e_mean:.2f} | pixels ΔE>10 : {r.delta_e_ratio:.4%} | "
        f"tailles différentes : {r.size_mismatch}"
    )
    return 0 if r.ok(args.max_diff, args.min_ssim, args.max_delta_e_ratio) else 1


if __name__ == "__main__":
    sys.exit(main())
