# Atelier 11 — Tests de sécurité automatisés (2 h 30) — déclinaison PHP

**Module 3** · Compétence C18 (DevSecOps) — OWASP ZAP, analyse des dépendances (Snyk, Dependabot)

## Objectif
Intégrer quatre familles de contrôles de sécurité dans la pipeline et savoir lesquels doivent bloquer.

| Famille | Question | Outil de l'atelier | Équivalents |
|---|---|---|---|
| SAST (code) | Mon code contient-il des motifs dangereux ? | Psalm (*taint analysis*) | Semgrep, SonarQube, CodeQL |
| SCA (dépendances) | Mes bibliothèques ont-elles des CVE connues ? | `composer audit`, Dependabot | Snyk, OWASP Dependency-Check, Renovate |
| Conteneur | Mon image embarque-t-elle des paquets vulnérables ? | Trivy (+ SBOM) | Grype, Docker Scout |
| DAST (appli qui tourne) | L'application exposée est-elle attaquable ? | OWASP ZAP | Burp Suite, Nuclei |

Tout porte sur l'application PHP de ce dossier : son code (parties A et B), son image Docker (partie C),
l'application qui tourne (partie D). Les commandes se lancent depuis `declinaisons/php/`.

## Partie A — SAST (25 min)
1. `composer sast` (Psalm en mode *taint analysis* : il suit les données non fiables — `$_GET`, `$_POST`… —
   jusqu'aux fonctions dangereuses), puis `composer lint` (PHPStan). Le code est-il propre ?
2. Ajoutez dans `src/Http/Application.php` (méthode `routes()`) une route de debug volontairement dangereuse :
   ```php
   $app->get('/debug/eval', static function (Request $request, Response $response): Response {
       return self::json($response, ['result' => eval('return '.$_GET['expr'].';')]);
   });
   ```
   Les deux outils la détectent-ils ? Sous quel nom ? Que dit PHPStan, et pourquoi ? Quel est le code de retour
   de `composer sast` (`echo $?`) : la commande **bloquerait-elle** une pipeline ? (Retirez-la ensuite !)
   Variante : remplacez `$_GET['expr']` par `$request->getQueryParams()['expr']`, la façon PSR-7 de lire le même
   paramètre. Psalm la voit-il encore ? Qu'en concluez-vous sur les limites d'un SAST ?
3. Format **SARIF** + onglet *Security* de GitHub :
   `vendor/bin/psalm --taint-analysis --no-cache --report=psalm.sarif`
   puis `github/codeql-action/upload-sarif@v4` (permissions `security-events: write`, et `actions: read`
   si le dépôt est privé ; l'onglet n'existe sur un dépôt privé qu'avec GitHub Code Security).

## Partie B — Dépendances (30 min)
1. `composer audit` → propre ? (`composer audit --locked` lit `composer.lock` sans rien installer : pratique en CI.)
   Dans un **projet d'essai** (un dossier vide hors du dépôt), demandez une version vulnérable :
   ```bash
   composer init -n --name essai/essai
   composer require twig/twig:3.14.0
   ```
   Que répond Composer ? Les versions récentes (2.11 dans ce cours) **refusent** d'installer une version touchée par un avis de
   sécurité. Levez ce blocage dans le projet d'essai, puis relancez l'audit :
   ```bash
   composer config policy.advisories.block false
   composer require twig/twig:3.14.0
   composer audit
   ```
2. **Dependabot** : le fichier `.github/dependabot.yml` est fourni pour Python. Ajoutez-y l'écosystème du projet PHP :
   ```yaml
     - package-ecosystem: composer
       directory: "/declinaisons/php"
       schedule: { interval: weekly }
   ```
   Activez *Dependabot alerts* et *security updates* sur votre fork (Settings → Code security). Observez les PR créées.
3. **Snyk** (compte gratuit) : `npx snyk test --file=composer.lock` — comparez avec `composer audit`.
4. Discussion : Dependabot vs Renovate ; bloquer sur **toute** CVE ou seulement HIGH/CRITICAL avec correctif ?
   Bloquer à l'installation (Composer) ou à l'audit (CI) ?

## Partie C — Image Docker (20 min)
```bash
docker build -t minishop-php .
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image minishop-php
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "$PWD":/out aquasec/trivy \
       image --format cyclonedx --output /out/sbom.cdx.json minishop-php
```
L'image part de `dunglas/frankenphp:1-php8.4-alpine`. Comparez avec la variante Debian de la même image de
base, sans rien construire : `docker run --rm aquasec/trivy image dunglas/frankenphp:1-php8.4` puis la même
commande avec `…-alpine`. Combien de vulnérabilités en plus ? À quoi sert le `apk upgrade` du `Dockerfile` ?
Qu'est-ce qu'un **SBOM** et pourquoi les clients (et le Cyber Resilience Act) le demandent-ils ?

## Partie D — DAST avec OWASP ZAP (45 min)
ZAP attaque l'application qui tourne, quel que soit son langage : mêmes commandes que l'énoncé d'origine. Le
fichier de règles `security/zap-rules.tsv` est à la racine du dépôt.
1. Application lancée dans Docker (`docker compose up -d --build`), puis scan **baseline** (passif, quelques minutes) :
   ```bash
   mkdir -p zap && cp ../../security/zap-rules.tsv zap/ && chmod 777 zap
   docker run --rm --network host -v "$PWD/zap":/zap/wrk ghcr.io/zaproxy/zaproxy:stable \
       zap-baseline.py -t http://localhost:8000 -c zap-rules.tsv -r zap-report.html
   ```
2. Lisez `zap/zap-report.html`. Corrigez au moins un avertissement : ajoutez un middleware Slim qui pose
   `X-Content-Type-Options: nosniff` et une `Content-Security-Policy` sur chaque réponse (une classe
   `MiddlewareInterface` sur le modèle de `ObserveMiddleware`, ajoutée dans `Application::create()`),
   reconstruisez l'image. Passez la règle de `WARN` à `FAIL` dans `zap/zap-rules.tsv` (puis reportez-la dans
   `security/zap-rules.tsv`) : elle protège désormais contre une régression.
3. Scan d'API guidé par le schéma : `zap-api-scan.py -t http://localhost:8000/openapi.json -f openapi`
   (scan actif ; sans fichier de règles `-c`, tout y est avertissement : il informe, il ne bloque pas).
4. **Burp Suite** (démo formateur) : proxy d'interception, Repeater sur `/cart/quote` — complémentaire
   du scan automatique pour les tests manuels d'intrusion.

## Partie E — Pipeline `security-php.yml` (10 min)
Assemblez les jobs dans `.github/workflows/security-php.yml` (voir énoncé de l'Atelier 2 pour la structure ;
`working-directory: declinaisons/php` partout ; seul `security/zap-rules.tsv` se lit à la racine).
Décidez et justifiez ce qui bloque :

| Contrôle | Sur PR | Sur main | Nocturne |
|---|---|---|---|
| Psalm *taint analysis* (`composer sast`, toute alerte) | | | |
| composer audit | | | |
| Trivy HIGH/CRITICAL | | | |
| ZAP baseline | | | |
| ZAP API complet | | | |

## Critères de réussite
- [ ] La route `eval` est détectée par le SAST **et bloquée** par la commande retenue pour la pipeline
- [ ] Dependabot actif et au moins une alerte comprise
- [ ] SBOM généré
- [ ] Un en-tête de sécurité corrigé et verrouillé en `FAIL` dans ZAP
- [ ] Tableau de politique de blocage rempli et justifié

## Sous Windows

Poste sous **WSL2** : rien à adapter. En **PowerShell** :

- Parties A et B : `composer sast`, `composer lint` et `composer audit` sont identiques. `npx snyk` demande Node.js.
- Parties C, D et E : voir la section « Sous Windows » de l'énoncé d'origine (`ateliers/atelier-11-securite.md`
  à la racine), en remplaçant l'image `minishop` par `minishop-php` et `security/zap-rules.tsv` par
  `../../security/zap-rules.tsv`.
