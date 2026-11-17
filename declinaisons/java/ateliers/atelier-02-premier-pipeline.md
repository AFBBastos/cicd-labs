# Atelier 2 — Premier pipeline CI avec GitHub Actions (1 h 30) — déclinaison Java

**Module 1** · Compétence C17

## Objectif
Construire un pipeline qui, à chaque push et Pull Request : vérifie le format, teste sur plusieurs
versions de Java, mesure la couverture, publie les rapports et construit l'image Docker de l'application Java.

## Étapes

### 1. Le pipeline minimal (15 min)
Créez `.github/workflows/ci-java.yml` **à la racine du dépôt** (GitHub ne lit les workflows que là) :
```yaml
name: CI Java
on:
  push:
    branches: [main]
  pull_request:
defaults:
  run:
    working-directory: declinaisons/java
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with: { distribution: temurin, java-version: "21" }
      - run: mvn -B -ntp test
```
`defaults.run.working-directory` place toutes les étapes `run:` dans le projet Java. Il ne s'applique pas aux
étapes `uses:` : leurs chemins restent relatifs à la racine du dépôt.
`-B` (mode non interactif) et `-ntp` (pas de barres de téléchargement) gardent le log lisible.
`mvn test` lance les tests unitaires et les tests d'API en mémoire (étiquettes `unit` et `api`).

Poussez sur votre branche, ouvrez une PR vers `main` **de votre fork** et observez l'onglet *Actions*.

### 2. Qualité de code (10 min)
Ajoutez un job `lint` **avant** les tests (`needs: lint`) qui lance `mvn -B -ntp spotless:check`.
Cassez volontairement le format (une indentation, un import inutile) pour voir le job échouer : le log
montre le diff attendu. `mvn spotless:apply` corrige en local.

### 3. Matrice et parallélisme (20 min)
- Matrice Java `21`, `25` (`strategy.matrix`), `fail-fast: false`.
- Cache Maven : `cache: maven` et `cache-dependency-path: declinaisons/java/pom.xml` dans `setup-java`.
  Comparez la durée avant / après.
- Tests en parallèle dans chaque job (facultatif, la suite est déjà rapide) :
  `-Djunit.jupiter.execution.parallel.enabled=true`.

### 4. Rapports et quality gate (20 min)
- `mvn -B -ntp verify "-Dgroups=unit | api" -Djacoco.branches.min=0.90` : tests, rapport de couverture et
  seuil bloquant (le seuil porte sur les branches de `Pricing`).
- Publiez `declinaisons/java/target/surefire-reports/` (JUnit XML) et `declinaisons/java/target/site/jacoco/`
  avec `actions/upload-artifact@v4` **même en cas d'échec** (`if: always()`).
- Écrivez la couverture dans `$GITHUB_STEP_SUMMARY`. JaCoCo n'a pas de sortie Markdown : construisez un
  tableau à partir de `target/site/jacoco/jacoco.csv` (colonnes `CLASS`, `BRANCH_MISSED`, `BRANCH_COVERED`,
  `LINE_MISSED`, `LINE_COVERED`), par exemple avec `awk -F,`. Prévoyez le cas où le fichier n'existe pas :
  quand un test échoue, Maven s'arrête avant la mesure.

### 5. Conteneurs (15 min)
- Un job qui exécute les tests **dans** `maven:3.9-eclipse-temurin-21` (`container:`).
- Un job `docker` qui construit l'image de **ce dossier** (`declinaisons/java/Dockerfile`) puis fait un
  *smoke test* (`curl /health`). Le `working-directory` par défaut convient : `docker build -t minishop-java .`
  Laissez à la JVM le temps de démarrer avant le premier `curl` :
  ```bash
  docker run -d -p 8000:8000 --name app minishop-java
  timeout 60 bash -c 'until curl -sf localhost:8000/health; do sleep 1; done'
  curl -sf localhost:8000/products | grep -q mug
  ```
  Lisez le `Dockerfile` : pourquoi deux étapes (`FROM … AS build` puis `FROM …-jre-alpine`) ?

### 6. Protéger `main` (10 min)
Settings → Branches → règle sur `main` : PR obligatoire + checks `lint` et `unit` requis.

### 7. Équivalent GitLab CI (bonus, 10 min)
Traduisez votre pipeline en `.gitlab-ci.yml` (stages, `parallel: matrix`, `image: maven:3.9-eclipse-temurin-21`,
`artifacts: reports: junit: declinaisons/java/target/surefire-reports/TEST-*.xml`).
Quelles notions sont identiques ? Lesquelles diffèrent ?

## Critères de réussite
- [ ] Pipeline vert sur la PR, 2 versions de Java
- [ ] Un test cassé fait échouer la PR et le rapport reste téléchargeable
- [ ] La couverture apparaît dans le résumé du run
- [ ] Image Docker construite et testée

## Pièges fréquents
- Indentation YAML (2 espaces, jamais de tabulation)
- Oublier `needs:` → tout part en parallèle
- `if: always()` manquant → pas de rapport quand on en a le plus besoin
- Chemins d'artefacts écrits comme si l'on était dans `declinaisons/java` → artefact vide
- Workflow rangé dans `declinaisons/java/.github/` → jamais exécuté

## Sous Windows

Rien à adapter : le pipeline s'exécute sur des runners Ubuntu, pas sur votre poste. Les étapes `run:`
s'écrivent donc en bash, même si vous éditez le fichier sous Windows.

- Pour reproduire le job `lint` en local : `mvn spotless:check`
- Pour reproduire le job `docker` en local (PowerShell, depuis `declinaisons/java`) :
  ```powershell
  docker build -t minishop-java .
  docker run -d --name app -p 8000:8000 minishop-java
  curl.exe -sf http://localhost:8000/health
  docker rm -f app
  ```
  (`curl.exe` et non `curl`, qui est un alias de `Invoke-WebRequest` dans Windows PowerShell.)
