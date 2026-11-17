# Atelier 2 — Premier pipeline CI avec GitHub Actions (1 h 30) — déclinaison C#

**Module 1** · Compétence C17

## Objectif
Construire un pipeline qui, à chaque push et Pull Request : lint, teste sur une matrice de versions de .NET,
mesure la couverture, publie les rapports et construit l'image Docker de l'application C#.

Le workflow se crée **à la racine du dépôt** (GitHub ne lit que `.github/workflows/` à la racine), mais le
projet C# est dans `declinaisons/csharp/` : c'est le rôle de `defaults.run.working-directory`.

## Étapes

### 1. Le pipeline minimal (15 min)
Créez `.github/workflows/ci-csharp.yml` :
```yaml
name: CI C#
on:
  push:
    branches: [main]
  pull_request:
defaults:
  run:
    working-directory: declinaisons/csharp
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-dotnet@v4
        with: { dotnet-version: "10.0.x" }
      - run: dotnet test --filter "Category=unit|Category=api"
```
Le filtre retient les tests unitaires (`tests/MiniShop.Tests`) et les tests d'API en mémoire
(`tests/MiniShop.Api.Tests`) : ni les uns ni les autres n'ont besoin d'un serveur.
Poussez sur votre branche, ouvrez une PR vers `main` **de votre fork** et observez l'onglet *Actions*.

### 2. Qualité de code (10 min)
Ajoutez un job `lint` **avant** les tests (`needs: lint`) :
- `dotnet format --verify-no-changes` : mise en forme et style définis dans `.editorconfig` ;
- `dotnet build` : les analyseurs Roslyn tournent à la compilation et, avec `TreatWarningsAsErrors`
  (`Directory.Build.props`), un avertissement fait échouer le job. `setup-dotnet` transforme ces erreurs en
  annotations dans la PR.

Cassez volontairement le style (une indentation, un `using` inutile) pour voir l'annotation.

### 3. Matrice et parallélisme (20 min)
- Matrice `dotnet: ["10.0"]` (`strategy.matrix`), `fail-fast: false`, et `dotnet-version: ${{ matrix.dotnet }}.x`.
  Une seule valeur aujourd'hui : .NET 10 est la version LTS courante (.NET 8 et .NET 9 arrivent en fin de
  support en novembre 2026). La matrice est prête à recevoir la suivante ; pour en tester deux, il faudrait
  aussi déclarer deux cibles dans `Directory.Build.props` (`<TargetFrameworks>`).
- Parallélisme : xUnit exécute en parallèle les classes de tests. Il est désactivé ici
  (`xunit.runner.json`) à cause du test qui modifie une variable d'environnement (Atelier 1). Discussion :
  quel est le prix d'un état global partagé entre tests ?
- Cache NuGet : `cache: true` et `cache-dependency-path: declinaisons/csharp/**/packages.lock.json` dans
  `setup-dotnet`, puis `dotnet restore --locked-mode`. Comparez la durée avant / après.

### 4. Rapports et quality gate (20 min)
- Tests, rapports JUnit (un par projet de tests) et couverture :
  ```bash
  dotnet test --filter "Category=unit|Category=api" --logger "junit;LogFileName={assembly}.xml" \
      --collect:"XPlat Code Coverage" --results-directory reports/tests
  ```
- Rapport HTML, résumé Markdown et **seuils bloquants** (code de retour non nul sous un seuil) :
  ```bash
  dotnet tool restore
  dotnet reportgenerator "-reports:reports/tests/*/coverage.cobertura.xml" -targetdir:reports/coverage \
      "-reporttypes:Html;MarkdownSummaryGithub" "-assemblyfilters:+MiniShop" "-classfilters:-*Generated*;-System.*" \
      minimumCoverageThresholds:lineCoverage=85 minimumCoverageThresholds:branchCoverage=90
  ```
  `-assemblyfilters:+MiniShop` limite pour l'instant la mesure à la bibliothèque `MiniShop` (règles de prix et
  catalogue) : l'application web `MiniShop.Api` n'a pas encore de tests. À l'Atelier 9, vous retirerez ce filtre
  pour étendre les seuils à tout le code.
  `-classfilters` écarte le code produit par les générateurs de source du compilateur (OpenAPI, expressions
  régulières), que personne ne teste. Les seuils : 85 % des lignes (comme le pipeline Python) et 90 % des branches,
  sur la bibliothèque. Avec les seuls tests de départ, les seuils ne sont pas tenus : le job reste rouge tant que
  vos tests de l'Atelier 1 ne sont pas dans la branche. C'est le rôle d'un *quality gate*.
- Publiez `declinaisons/csharp/reports/` avec `actions/upload-artifact@v4` **même en cas d'échec**
  (`if: always()`). Attention : `path:` se lit depuis la racine du dépôt, `working-directory` ne s'applique
  qu'aux étapes `run`.
- Écrivez la couverture dans `$GITHUB_STEP_SUMMARY` (`cat reports/coverage/SummaryGithub.md >> "$GITHUB_STEP_SUMMARY"`).

### 5. Conteneurs (15 min)
- Un job qui exécute les tests **dans** `mcr.microsoft.com/dotnet/sdk:10.0` (`container:`).
- Un job `docker` qui construit l'image de l'application C# (`Dockerfile` de ce dossier :
  `docker build -t minishop-csharp .`) puis fait un *smoke test* (`curl /health`). Lisez le `Dockerfile` :
  pourquoi deux étapes `FROM` ? Que contient l'image finale, et sous quel utilisateur tourne l'application ?

### 6. Protéger `main` (10 min)
Settings → Branches → règle sur `main` : PR obligatoire + checks `lint` et `unit` requis.

### 7. Équivalent GitLab CI (bonus, 10 min)
Traduisez votre pipeline en `.gitlab-ci.yml` (stages, `image: mcr.microsoft.com/dotnet/sdk:10.0`,
`parallel: matrix`, `artifacts: reports: junit`). Quelles notions sont identiques ? Lesquelles diffèrent ?

## Critères de réussite
- [ ] Pipeline vert sur la PR, matrice de versions de .NET en place
- [ ] Un test cassé fait échouer la PR et le rapport reste téléchargeable
- [ ] La couverture apparaît dans le résumé du run
- [ ] Image Docker construite et testée

## Pièges fréquents
- Indentation YAML (2 espaces, jamais de tabulation)
- Oublier `needs:` → tout part en parallèle
- `if: always()` manquant → pas de rapport quand on en a le plus besoin
- `packages.lock.json` non commité après l'ajout d'un paquet → `dotnet restore --locked-mode` échoue (NU1004)
- Chemins : `run` part de `declinaisons/csharp`, mais `uses:` (artefacts, cache) part de la racine

## Sous Windows

Rien à adapter : le pipeline s'exécute sur des runners Ubuntu, pas sur votre poste. Les étapes `run:`
s'écrivent donc en bash, même si vous éditez le fichier sous Windows.

- Pour reproduire le job `lint` en local : `dotnet format --verify-no-changes; dotnet build`
- Pour reproduire le job `docker` en local (PowerShell, depuis `declinaisons/csharp`) :
  ```powershell
  docker build -t minishop-csharp .
  docker run -d --name app -p 8000:8000 minishop-csharp
  curl.exe -sf http://localhost:8000/health
  docker rm -f app
  ```
  (`curl.exe` et non `curl`, qui est un alias de `Invoke-WebRequest` dans Windows PowerShell.)
