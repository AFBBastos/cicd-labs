# Atelier 2 — Premier pipeline CI avec GitHub Actions (1 h 30) — déclinaison PHP

**Module 1** · Compétence C17

## Objectif
Construire un pipeline qui, à chaque push et Pull Request : lint, teste en parallèle sur plusieurs
versions de PHP, mesure la couverture, publie les rapports et construit l'image Docker.

## Étapes

### 1. Le pipeline minimal (15 min)
Les workflows vivent **à la racine du dépôt**, pas dans `declinaisons/php/`. Créez
`.github/workflows/ci-php.yml` ; le bloc `defaults` place toutes les étapes `run:` dans le projet PHP :
```yaml
name: CI PHP
on:
  push:
    branches: [main]
  pull_request:
defaults:
  run:
    working-directory: declinaisons/php
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: shivammathur/setup-php@v2
        with: { php-version: "8.4" }
      - run: composer install --no-interaction --no-progress
      - run: vendor/bin/phpunit --testsuite unit,api
```
(`unit` : les règles de prix ; `api` : l'API appelée en mémoire, sans serveur — l'équivalent de `pytest -m "unit or api"`.)
Poussez sur votre branche, ouvrez une PR vers `main` **de votre fork** et observez l'onglet *Actions*.

### 2. Qualité de code (10 min)
Ajoutez un job `lint` **avant** les tests (`needs: lint`) :
`vendor/bin/php-cs-fixer check --diff` puis `vendor/bin/phpstan analyse --no-progress --error-format=github`
(les erreurs de PHPStan s'affichent directement dans la PR).
Cassez volontairement le style, puis un type, pour voir l'échec et l'annotation.

### 3. Matrice et cache (20 min)
- Matrice PHP `8.3`, `8.4` (`strategy.matrix`), `fail-fast: false`.
- Cache des dépendances : `actions/cache@v4` sur le dossier donné par `composer config cache-files-dir`,
  avec une clé calculée sur `hashFiles('declinaisons/php/composer.lock')`. Comparez la durée avant / après.
- Les jobs de la matrice tournent en parallèle. À l'intérieur d'un job, l'équivalent de `pytest -n auto`
  serait ParaTest ; inutile ici, la suite dure quelques millisecondes.

### 4. Rapports et quality gate (20 min)
- `setup-php` avec `coverage: pcov`, puis
  `vendor/bin/phpunit --testsuite unit,api --log-junit reports/junit.xml --coverage-text --coverage-html reports/coverage --coverage-cobertura reports/cobertura.xml`
- Seuil bloquant, sur le cœur métier : `php tools/coverage-check.php reports/cobertura.xml --file=Pricing.php --min-lines=85`
  (PHPUnit n'a pas d'option « fail-under » : ce script du dépôt en tient lieu). Avec les seuls tests de départ,
  le seuil n'est pas tenu : c'est le rôle d'un *quality gate*. Il le sera avec vos tests de l'Atelier 1.
  Le seuil ne porte pour l'instant que sur `Pricing.php` : la couche HTTP n'a pas encore de tests. À l'Atelier 9,
  vous l'étendrez à tout le code en retirant `--file=Pricing.php`.
- Publiez `reports/` avec `actions/upload-artifact@v4` **même en cas d'échec** (`if: always()`).
  Attention : `path:` ne suit pas `working-directory`, il faut écrire `declinaisons/php/reports/`.
- Écrivez la couverture dans `$GITHUB_STEP_SUMMARY`
  (`php tools/coverage-check.php reports/cobertura.xml --markdown`).

### 5. Conteneurs (15 min)
- Un job qui exécute les tests **dans** `php:8.4-cli` (`container:`). L'image officielle ne contient ni
  Composer ni `unzip` : installez-les dans une première étape.
- Un job `docker` qui construit l'image de l'application PHP (le `Dockerfile` de ce dossier) puis fait un
  *smoke test* : `docker build -t minishop-php:${{ github.sha }} .`, `docker run -d -p 8000:8000 …`, attente de
  `/health`, puis `curl -sf localhost:8000/products | grep -q mug`.

### 6. Protéger `main` (10 min)
Settings → Branches → règle sur `main` : PR obligatoire + checks `lint` et `unit` requis.

### 7. Équivalent GitLab CI (bonus, 10 min)
Traduisez votre pipeline en `.gitlab-ci.yml` (stages, `parallel: matrix`, `artifacts: reports: junit`).
Quelles notions sont identiques ? Lesquelles diffèrent ?

## Critères de réussite
- [ ] Pipeline vert sur la PR, 2 versions de PHP
- [ ] Un test cassé fait échouer la PR et le rapport reste téléchargeable
- [ ] La couverture apparaît dans le résumé du run
- [ ] Image Docker construite et testée

## Pièges fréquents
- Indentation YAML (2 espaces, jamais de tabulation)
- Oublier `needs:` → tout part en parallèle
- `if: always()` manquant → pas de rapport quand on en a le plus besoin
- `working-directory` ne s'applique qu'aux étapes `run:`, pas aux `uses:` (chemins d'artefacts, `hashFiles`)

## Sous Windows

Rien à adapter : le pipeline s'exécute sur des runners Ubuntu, pas sur votre poste. Les étapes `run:`
s'écrivent donc en bash, même si vous éditez le fichier sous Windows.

- Pour reproduire le job `lint` en local : `composer lint`
- Pour reproduire le job `docker` en local (PowerShell, depuis `declinaisons/php`) :
  ```powershell
  docker build -t minishop-php .
  docker run -d --name app -p 8000:8000 minishop-php
  curl.exe -sf http://localhost:8000/health
  docker rm -f app
  ```
  (`curl.exe` et non `curl`, qui est un alias de `Invoke-WebRequest` dans Windows PowerShell.)
