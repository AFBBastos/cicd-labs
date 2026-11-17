# Atelier 2 — Premier pipeline CI avec GitHub Actions (1 h 30) — déclinaison Node.js

**Module 1** · Compétence C17

## Objectif
Construire un pipeline qui, à chaque push et Pull Request : lint, teste en parallèle sur plusieurs
versions de Node.js, mesure la couverture, publie les rapports et construit l'image Docker.

## Avant de commencer
GitHub ne lit les workflows que dans `.github/workflows/` **à la racine du dépôt**. Le projet Node.js,
lui, est dans `declinaisons/node/` : le workflow déclare donc ce dossier comme répertoire de travail.
Deux conséquences à garder en tête pendant tout l'atelier :
- `defaults.run.working-directory` ne vaut que pour les étapes `run:` ;
- les étapes `uses:` (cache de `setup-node`, `upload-artifact`) attendent des chemins **depuis la racine
  du dépôt** : `declinaisons/node/package-lock.json`, `declinaisons/node/reports/`…

## Étapes

### 1. Le pipeline minimal (15 min)
Créez `.github/workflows/ci-node.yml` (à la racine du dépôt) :
```yaml
name: CI Node.js
on:
  push:
    branches: [main]
  pull_request:
defaults:
  run:
    working-directory: declinaisons/node
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 22 }
      - run: npm ci
      - run: npx vitest run tests/unit tests/api
```
Poussez sur votre branche, ouvrez une PR vers `main` **de votre fork** et observez l'onglet *Actions*.

### 2. Qualité de code (10 min)
Ajoutez un job `lint` (ESLint puis Prettier) **avant** les tests (`needs: lint`) :
`npx eslint .` et `npx prettier --check .`. L'action `setup-node` enregistre un *problem matcher* pour
ESLint : les erreurs s'affichent directement dans la PR.
Cassez volontairement le code (une variable jamais utilisée, un `==` au lieu de `===`) pour voir l'annotation.

### 3. Matrice et parallélisme (20 min)
- Matrice Node.js `20`, `22`, `24` (`strategy.matrix`), `fail-fast: false`.
- Tests en parallèle dans chaque job : rien à ajouter, Vitest répartit déjà les **fichiers** de test
  sur plusieurs processus (l'équivalent de `pytest -n auto`).
- Cache npm : `cache: npm` de `setup-node`, avec `cache-dependency-path: declinaisons/node/package-lock.json`.
  Comparez la durée avant / après.

### 4. Rapports et quality gate (20 min)
- `--coverage --reporter=default --reporter=junit --outputFile.junit=reports/junit.xml`
- Seuil bloquant : dans `vitest.config.js`, ajoutez à `coverage` un seuil sur le cœur métier,
  `thresholds: { 'src/pricing.js': { branches: 90 } }`. Vitest sort alors en erreur sous le seuil
  (le rapport est quand même écrit).
- Publiez `declinaisons/node/reports/` et `declinaisons/node/coverage/` avec `actions/upload-artifact@v4`
  **même en cas d'échec** (`if: always()`).
- Écrivez la couverture dans `$GITHUB_STEP_SUMMARY` : Vitest produit le tableau dans `coverage/coverage.txt`
  (voir `vitest.config.js`) ; entourez-le d'un bloc de code Markdown.

### 5. Conteneurs (15 min)
- Un job qui exécute les tests **dans** `node:22-slim` (`container:`).
- Un job `docker` qui construit l'image de **ce dossier** (`docker build -t minishop-node .`, avec le
  `Dockerfile` de `declinaisons/node/`) puis fait un *smoke test* : lancer le conteneur, attendre `/health`,
  vérifier que `/products` contient `mug`.

### 6. Protéger `main` (10 min)
Settings → Branches → règle sur `main` : PR obligatoire + checks `lint` et `unit` requis.

### 7. Équivalent GitLab CI (bonus, 10 min)
Traduisez votre pipeline en `.gitlab-ci.yml` (stages, `image: node:22`, `parallel: matrix`,
`artifacts: reports: junit`, `coverage_report` au format Cobertura).
Quelles notions sont identiques ? Lesquelles diffèrent ?

## Critères de réussite
- [ ] Pipeline vert sur la PR, 3 versions de Node.js
- [ ] Un test cassé fait échouer la PR et le rapport reste téléchargeable
- [ ] La couverture apparaît dans le résumé du run
- [ ] Image Docker construite et testée

## Pièges fréquents
- Indentation YAML (2 espaces, jamais de tabulation)
- Oublier `needs:` → tout part en parallèle
- `if: always()` manquant → pas de rapport quand on en a le plus besoin
- Chemin relatif au dossier `declinaisons/node` dans une étape `uses:` → cache ignoré ou artefact vide
- `npm install` au lieu de `npm ci` → les versions ne sont plus celles de `package-lock.json`
- Le seuil de couverture n'est tenu qu'une fois les tests de l'Atelier 1 écrits : avec les 3 tests de
  départ, le job échoue (c'est le but d'un *quality gate*)

## Sous Windows

Rien à adapter : le pipeline s'exécute sur des runners Ubuntu, pas sur votre poste. Les étapes `run:`
s'écrivent donc en bash, même si vous éditez le fichier sous Windows.

- Pour reproduire le job `lint` en local : `npx eslint .; npx prettier --check .`
- Pour reproduire le job `docker` en local (PowerShell, depuis `declinaisons/node`) :
  ```powershell
  docker build -t minishop-node .
  docker run -d --name app -p 8000:8000 minishop-node
  curl.exe -sf http://localhost:8000/health
  docker rm -f app
  ```
  (`curl.exe` et non `curl`, qui est un alias de `Invoke-WebRequest` dans Windows PowerShell.)
