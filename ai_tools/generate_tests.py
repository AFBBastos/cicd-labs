"""Génération de tests pytest à partir d'une spécification en langage naturel.

Deux moteurs :
  * LLM (LLM_PROVIDER=anthropic|mistral|ollama|openai) : le modèle lit la spec ET le
    code source, puis propose des tests (scénarios de la spec + cas limites).
  * offline (par défaut) : un analyseur déterministe de la grammaire Gherkin
    (voir l'en-tête de specs/pricing.feature) — utile sans réseau et comme
    « vérité terrain » pour comparer avec la sortie du LLM.

Dans tous les cas, les tests générés sont EXÉCUTÉS immédiatement (garde-fou) :
un test généré qui échoue est soit un bug de l'application, soit une
hallucination du modèle -> revue humaine obligatoire.

Usage :
    python ai_tools/generate_tests.py specs/pricing.feature \
        --source minishop/pricing.py --out tests/generated/test_pricing_generated.py

Autres langages (déclinaisons PHP, Java, Node.js, C# du dossier declinaisons/) :
    python ai_tools/generate_tests.py specs/pricing.feature --lang java \
        --source <fichiers source...> --out <fichier de test>
Il n'existe alors NI moteur offline NI exécution automatique : un LLM est requis, et les
tests générés se lancent avec l'outil du langage (voir l'Atelier 3 de la déclinaison).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ai_tools.llm import LLMError, chat, extract_code, is_offline, provider  # noqa: E402

PROMPT_FILE = Path(__file__).parent / "prompts" / "generate_tests.md"

# Autres langages : étiquette du bloc de code attendu et motif qui repère un test dans le fichier généré.
LANGS = {
    "php": ("php", r"^\s*public function test\w+\(|#\[Test\]"),
    "java": ("java", r"@(?:Test|ParameterizedTest)\b"),
    "node": ("javascript", r"^\s*(?:test|it)(?:\.each\([^)]*\))?\("),
    "csharp": ("csharp", r"\[(?:Fact|Theory)\b"),
}

FIELDS = {"sous-total": "subtotal", "remise": "discount", "livraison": "shipping", "total": "total"}


# --------------------------------------------------------------------------- offline
def slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def warn(message: str) -> None:
    print(f"[!] {message}", file=sys.stderr)


def parse_feature(text: str) -> list[dict]:
    scenarios, current = [], None
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if line.startswith("Scénario:") or line.startswith("Scenario:"):
            current = {"name": line.split(":", 1)[1].strip(), "items": [], "coupon": None, "asserts": [], "error": None}
            scenarios.append(current)
            continue
        if current is None or not line or line.startswith("#"):
            continue
        if "panier avec" in line:
            current["items"] = [{"product_id": p, "qty": int(q)} for q, p in re.findall(r'(\d+)\s+"([^"]+)"', line)]
        elif m := re.search(r'coupon "([^"]+)"', line):
            current["coupon"] = m.group(1)
        elif m := re.search(r"(sous-total|remise|livraison|total) vaut (\d+(?:[.,]\d+)?)", line):
            current["asserts"].append((FIELDS[m.group(1)], m.group(2).replace(",", ".")))  # 29,90 accepté comme 29.90
        elif m := re.search(r'erreur "([^"]+)"', line):
            current["error"] = m.group(1)
        elif "panier vide" not in line and "je calcule le total" not in line:
            # Hors grammaire : la ligne ne produit rien. On le dit, plutôt que de générer un test qui ne vérifie pas tout.
            warn(f"ligne {number} non reconnue par le moteur offline, ignorée : {line}")
    for sc in scenarios:
        if not sc["asserts"] and not sc["error"]:
            warn(f"scénario « {sc['name']} » : aucune vérification reconnue, le test généré n'aura pas d'assertion")
    return scenarios


def render_offline(scenarios: list[dict], spec_name: str) -> str:
    out = [
        f'"""Tests générés automatiquement depuis {spec_name} (moteur : offline).',
        "",
        "NE PAS MODIFIER À LA MAIN : régénérer avec ai_tools/generate_tests.py",
        '"""',
        "from decimal import Decimal",
        "",
        "import pytest",
        "",
        "from minishop.pricing import quote",
        "",
        "pytestmark = [pytest.mark.generated, pytest.mark.unit]",
        "",
    ]
    used: dict[str, int] = {}
    for sc in scenarios:
        name = slug(sc["name"]) or "scenario"
        used[name] = used.get(name, 0) + 1
        if used[name] > 1:  # deux scénarios de même titre : sans suffixe, Python ne garderait que le dernier
            warn(f"titre de scénario en double : « {sc['name']} » -> test_{name}_{used[name]}")
            name = f"{name}_{used[name]}"
        out += ["", "", f"def test_{name}():", f'    """{sc["name"]}"""']
        call = f"quote({sc['items']!r}, {sc['coupon']!r})"
        if sc["error"]:
            exc = "KeyError" if "Produit" in sc["error"] else "ValueError"
            out += [f"    with pytest.raises({exc}, match={sc['error']!r}):", f"        {call}"]
        else:
            out.append(f"    q = {call}")
            out += [f'    assert q.{f} == Decimal("{v}")' for f, v in sc["asserts"]]
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------- LLM
def render_llm(spec: str, sources: list[Path], spec_name: str, lang: str = "python", out: Path | None = None) -> str:
    fence = "python" if lang == "python" else LANGS[lang][0]
    prompt = PROMPT_FILE if lang == "python" else PROMPT_FILE.with_name(f"generate_tests_{lang}.md")
    system = prompt.read_text(encoding="utf-8")
    code = "\n\n".join(f"Fichier `{src}` :\n\n```{fence}\n{src.read_text(encoding='utf-8')}\n```" for src in sources)
    user = (
        f"## Spécification ({spec_name})\n\n{spec}\n\n"
        f"## Code source sous test\n\n{code}\n\n"
        "Génère le fichier de tests complet."
    )
    if out is not None:
        # Java, PHP et C# exigent que la classe porte le nom du fichier ; Node.js a besoin du chemin relatif.
        user += f" Il sera enregistré dans `{out}` : nomme la classe et écris les chemins d'import en conséquence."
    return extract_code(chat(system, user), fence)


def generate_other_language(args: argparse.Namespace, spec: str) -> int:
    """Déclinaisons PHP / Java / Node.js / C# : LLM obligatoire, exécution laissée à l'outil du langage."""
    if args.out is None:
        print("[x] --out est obligatoire avec --lang (chemin du fichier de test à écrire)", file=sys.stderr)
        return 2
    if is_offline():
        print(
            f"[x] Pas de moteur offline pour --lang {args.lang} : configurez un LLM "
            "(export LLM_PROVIDER=anthropic ANTHROPIC_API_KEY=<clé>)",
            file=sys.stderr,
        )
        return 2
    try:
        code = render_llm(spec, args.source, args.spec.name, args.lang, args.out)
    except LLMError as exc:
        print(f"[x] LLM indisponible ({exc}) : aucun repli possible pour --lang {args.lang}", file=sys.stderr)
        return 2
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(code, encoding="utf-8")
    n = len(re.findall(LANGS[args.lang][1], code, flags=re.M))
    print(f"[+] {n} tests écrits dans {args.out} (moteur : {provider()})")
    print(
        "[i] Non exécutés : lancez la suite avec l'outil du langage, puis relisez chaque échec (bug ou hallucination ?)"
    )
    return 0


# --------------------------------------------------------------------------- garde-fou
def run_pytest(path: Path) -> tuple[bool, str]:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(path)],
        capture_output=True,
        text=True,
        errors="replace",
    )
    return proc.returncode == 0, proc.stdout[-3000:]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", type=Path)
    ap.add_argument("--source", type=Path, nargs="+", default=[Path("minishop/pricing.py")])
    ap.add_argument("--out", type=Path, help="défaut (Python) : tests/generated/test_pricing_generated.py")
    ap.add_argument("--lang", choices=["python", *LANGS], default="python", help="langage des tests générés")
    ap.add_argument("--no-run", action="store_true", help="ne pas exécuter les tests générés")
    args = ap.parse_args()

    spec = args.spec.read_text(encoding="utf-8")
    if args.lang != "python":
        return generate_other_language(args, spec)
    args.out = args.out or Path("tests/generated/test_pricing_generated.py")
    if is_offline():
        engine, code = "offline", render_offline(parse_feature(spec), args.spec.name)
    else:
        try:
            engine, code = provider(), render_llm(spec, args.source, args.spec.name)
        except LLMError as exc:
            print(f"[!] LLM indisponible ({exc}) -> repli sur le moteur offline", file=sys.stderr)
            engine, code = "offline", render_offline(parse_feature(spec), args.spec.name)

    try:
        compile(code, str(args.out), "exec")
    except SyntaxError as exc:
        print(f"[x] Le code généré ne compile pas : {exc}", file=sys.stderr)
        args.out.with_suffix(".rejected.txt").write_text(code, encoding="utf-8")
        return 2

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(code, encoding="utf-8")
    subprocess.run([sys.executable, "-m", "ruff", "format", "-q", str(args.out)], capture_output=True)
    n = len(re.findall(r"^def test_", code, flags=re.M))
    print(f"[+] {n} tests écrits dans {args.out} (moteur : {engine})")
    if args.no_run:
        return 0
    ok, output = run_pytest(args.out)
    print(output)
    print(
        "[+] Tous les tests générés passent"
        if ok
        else "[!] Des tests générés échouent : à analyser (bug ou hallucination ?)"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
