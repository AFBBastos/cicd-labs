# Atelier 11 — Tests de sécurité automatisés (2 h 30) — déclinaison Node.js

**Module 3** · Compétence C18 (DevSecOps) — OWASP ZAP, analyse des dépendances (Snyk, Dependabot)

## Objectif
Intégrer quatre familles de contrôles de sécurité dans la pipeline et savoir lesquels doivent bloquer.

| Famille | Question | Outil de l'atelier | Équivalents |
|---|---|---|---|
| SAST (code) | Mon code contient-il des motifs dangereux ? | `eslint-plugin-security`, règle `no-eval` d'ESLint | Semgrep, SonarQube, CodeQL |
| SCA (dépendances) | Mes bibliothèques ont-elles des CVE connues ? | `npm audit`, Dependabot | Snyk, OWASP Dependency-Check, Renovate |
| Conteneur | Mon image embarque-t-elle des paquets vulnérables ? | Trivy (+ SBOM) | Grype, Docker Scout |
| DAST (appli qui tourne) | L'application exposée est-elle attaquable ? | OWASP ZAP | Burp Suite, Nuclei |

Tout l'atelier porte sur l'application de `declinaisons/node/` : son code (parties A et B), son image
Docker (partie C), l'application qui tourne (partie D). Les commandes se lancent depuis ce dossier.

## Partie A — SAST (25 min)
1. `npm run lint:security` : ESLint avec les règles de `eslint-plugin-security` sur `src/` (configuration
   dans `eslint.security.config.js`). Puis `npx eslint --rule 'no-eval: error' src`, la règle du cœur d'ESLint.
2. Ajoutez dans `src/app.js`, à côté des autres routes, une route de debug volontairement dangereuse :
   ```js
   app.get('/debug/eval', { schema: { hide: true } }, async (request) => ({
     result: eval(request.query.expr),
   }));
   ```
   Les deux outils la détectent-ils ? Avec quelle sévérité ? `npm run lint` (le lint de tous les jours)
   la signale-t-il ? Laquelle de ces commandes l'arrêterait dans une pipeline (code retour différent de 0) :
   `npx eslint -c eslint.security.config.js src` ou `npm run lint:security`, qui ajoute `--max-warnings 0` ?
   (Retirez-la ensuite !)
   Cherchez aussi `eslint-disable` dans `src/app.js` : une alerte du SAST y a été examinée puis levée.
   La justification écrite vous convainc-t-elle ?
3. Format **SARIF** + onglet *Security* de GitHub :
   `npx eslint -c eslint.security.config.js -f @microsoft/eslint-formatter-sarif -o eslint-security.sarif src`
   puis `github/codeql-action/upload-sarif@v4` (permissions `security-events: write`, et `actions: read`
   si le dépôt est privé ; l'onglet n'existe sur un dépôt privé qu'avec GitHub Code Security).

## Partie B — Dépendances (30 min)
1. `npm audit --omit=dev` (dépendances de production) → propre ? Puis `npm audit` (avec les outils de
   développement) : que signale-t-il, et où ? Ajoutez une version vulnérable et relancez :
   ```bash
   npm install lodash@4.17.15
   npm audit --omit=dev
   npm uninstall lodash          # ou : git checkout package.json package-lock.json
   ```
2. **Dependabot** : le fichier `.github/dependabot.yml` est fourni. Ajoutez-y l'écosystème npm de ce dossier :
   ```yaml
     - package-ecosystem: npm
       directory: "/declinaisons/node"
       schedule: { interval: weekly }
   ```
   Activez *Dependabot alerts* et *security updates* sur votre fork (Settings → Code security).
   Observez les PR créées.
3. **Snyk** (compte gratuit) : `npx snyk test` — comparez avec `npm audit`.
4. Discussion : Dependabot vs Renovate ; bloquer sur **toute** CVE ou seulement HIGH/CRITICAL avec correctif ?
   Faut-il bloquer pour une vulnérabilité dans un outil de développement qui ne part jamais en production
   (`--omit=dev`, `--audit-level=high`) ?

## Partie C — Image Docker (20 min)
```bash
docker build -t minishop-node .
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image minishop-node
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "$PWD":/out aquasec/trivy \
       image --format cyclonedx --output /out/sbom.cdx.json minishop-node
```
Changez `node:22-slim` en `node:22` (image complète) : combien de vulnérabilités en plus ? Retirez du
`Dockerfile` la suppression de npm : que signale Trivy, et dans quel paquet ?
Qu'est-ce qu'un **SBOM** et pourquoi les clients (et le Cyber Resilience Act) le demandent-ils ?

## Partie D — DAST avec OWASP ZAP (45 min)
1. Application lancée dans Docker (`docker run -d --name app -p 8000:8000 minishop-node`), puis scan
   **baseline** (passif, quelques minutes) — le fichier de règles est à la racine du dépôt :
   ```bash
   mkdir -p zap && cp ../../security/zap-rules.tsv zap/ && chmod 777 zap
   docker run --rm --network host -v "$PWD/zap":/zap/wrk ghcr.io/zaproxy/zaproxy:stable \
       zap-baseline.py -t http://localhost:8000 -c zap-rules.tsv -r zap-report.html
   ```
2. Lisez `zap/zap-report.html`. Corrigez au moins un avertissement : ajoutez dans `src/app.js` un hook
   `onSend` qui pose `X-Content-Type-Options: nosniff` et une `Content-Security-Policy`. Passez la règle de
   `WARN` à `FAIL` dans `security/zap-rules.tsv` : elle protège désormais contre une régression.
3. Scan d'API guidé par le schéma : `zap-api-scan.py -t http://localhost:8000/openapi.json -f openapi`
   (scan actif ; sans fichier de règles `-c`, tout y est avertissement : il informe, il ne bloque pas).
4. **Burp Suite** (démo formateur) : proxy d'interception, Repeater sur `/cart/quote` — complémentaire
   du scan automatique pour les tests manuels d'intrusion.

## Partie E — Pipeline `security-node.yml` (10 min)
Assemblez les jobs dans `.github/workflows/security-node.yml` (voir énoncé de l'Atelier 2 pour la
structure : répertoire de travail `declinaisons/node` ; seul `security/zap-rules.tsv` est à la racine du dépôt). Décidez et justifiez ce qui bloque :

| Contrôle | Sur PR | Sur main | Nocturne |
|---|---|---|---|
| ESLint security (`npm run lint:security`, avertissements bloquants) | | | |
| npm audit | | | |
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

**Parties A et B** : les commandes `npm` et `npx` sont identiques ; écrivez la règle entre guillemets
doubles : `npx eslint --rule "no-eval: error" src`.

**Partie C — Trivy** (Docker Desktop expose bien `/var/run/docker.sock` aux conteneurs)
```powershell
docker build -t minishop-node .
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image minishop-node
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "${PWD}:/out" aquasec/trivy image --format cyclonedx --output /out/sbom.cdx.json minishop-node
```

**Partie D — OWASP ZAP** : pas de `--network host` ni de `chmod` ; ZAP joint l'application par
`host.docker.internal`.
```powershell
docker run -d --name app -p 8000:8000 minishop-node
New-Item -ItemType Directory -Force zap; Copy-Item ../../security/zap-rules.tsv zap/
docker run --rm -v "${PWD}/zap:/zap/wrk" ghcr.io/zaproxy/zaproxy:stable zap-baseline.py -t http://host.docker.internal:8000 -c zap-rules.tsv -r zap-report.html
docker run --rm -v "${PWD}/zap:/zap/wrk" ghcr.io/zaproxy/zaproxy:stable zap-api-scan.py -t http://host.docker.internal:8000/openapi.json -f openapi
```
Rapport : `start zap/zap-report.html`. En Git Bash, préfixez ces `docker run` par `MSYS_NO_PATHCONV=1`.

**Partie E** : le workflow `security-node.yml` s'exécute sur un runner Ubuntu, gardez la syntaxe bash de l'énoncé.
