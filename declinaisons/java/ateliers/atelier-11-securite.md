# Atelier 11 — Tests de sécurité automatisés (2 h 30) — déclinaison Java

**Module 3** · Compétence C18 (DevSecOps) — OWASP ZAP, analyse des dépendances (Snyk, Dependabot)

## Objectif
Intégrer quatre familles de contrôles de sécurité dans la pipeline et savoir lesquels doivent bloquer.

| Famille | Question | Outil de l'atelier | Équivalents |
|---|---|---|---|
| SAST (code) | Mon code contient-il des motifs dangereux ? | SpotBugs + FindSecBugs | Semgrep, SonarQube, CodeQL |
| SCA (dépendances) | Mes bibliothèques ont-elles des CVE connues ? | OSV-Scanner, Dependabot | OWASP Dependency-Check, Snyk, Renovate |
| Conteneur | Mon image embarque-t-elle des paquets vulnérables ? | Trivy (+ SBOM) | Grype, Docker Scout |
| DAST (appli qui tourne) | L'application exposée est-elle attaquable ? | OWASP ZAP | Burp Suite, Nuclei |

Tout l'atelier porte sur l'application Java de `declinaisons/java/` : son code (A), ses dépendances (B), son
image Docker (C) et l'application qui tourne (D). **Les commandes se lancent depuis ce dossier**, sauf mention contraire.

## Partie A — SAST (25 min)
1. `mvn compile spotbugs:check` : SpotBugs analyse le bytecode, le greffon **FindSecBugs** (déjà déclaré
   dans le `pom.xml`) ajoute les règles de sécurité. Le code fourni doit sortir propre.
   Lisez `spotbugs-exclude.xml` : deux alertes ont été écartées, chacune avec sa justification. Êtes-vous d'accord ?
2. Ajoutez dans `src/main/java/fr/minishop/api/ShopController.java` une route de debug volontairement dangereuse :
   ```java
   @GetMapping("/debug/exec")
   public Map<String, Object> debug(@RequestParam String cmd) throws IOException {
     return Map.of("pid", Runtime.getRuntime().exec(cmd).pid());
   }
   ```
   (imports : `org.springframework.web.bind.annotation.RequestParam`, `java.io.IOException`).
   Relancez. Est-elle détectée ? Sous quelle règle, avec quelle priorité ?
   Relancez en retirant le bloc `findsecbugs-plugin` du `pom.xml` : que voit SpotBugs seul ?
   (Retirez la route ensuite et rétablissez le `pom.xml` !)
3. Format **SARIF** + onglet *Security* de GitHub : `mvn compile spotbugs:spotbugs` écrit
   `target/spotbugsSarif.json` sans faire échouer le build, puis `github/codeql-action/upload-sarif@v4`
   (permissions `security-events: write`, et `actions: read` si le dépôt est privé ; l'onglet n'existe sur
   un dépôt privé qu'avec GitHub Code Security). Dans la pipeline, le contrôle **bloquant** est
   `mvn compile spotbugs:check` : vérifiez qu'il échoue bien tant que la route de debug est là.
   (`-Dspotbugs.threshold=High` ne garde que la priorité haute : quel risque à relever ainsi le seuil ?)

## Partie B — Dépendances (30 min)
1. **OSV-Scanner** lit le `pom.xml`, résout les dépendances transitives et interroge la base OSV
   (que pip-audit sait aussi interroger) :
   ```bash
   docker run --rm -v "$PWD":/src:ro ghcr.io/google/osv-scanner:latest scan source --lockfile /src/pom.xml
   ```
   Propre ? Ajoutez dans les `<dependencies>` une version connue pour être vulnérable, relancez, puis retirez-la :
   ```xml
   <dependency>
     <groupId>org.apache.logging.log4j</groupId>
     <artifactId>log4j-core</artifactId>
     <version>2.14.1</version>
   </dependency>
   ```
   Faites de même sur `tests-app/pom.xml`. Les dépendances de test doivent-elles être auditées ?
   La plupart des versions viennent de Spring Boot (`spring-boot-dependencies`) : quel est l'intérêt, pour la
   sécurité, de suivre les versions correctives du cadriciel ?
2. **Dependabot** : ajoutez au fichier `.github/dependabot.yml` (racine du dépôt) les entrées de l'écosystème Maven :
   ```yaml
     - package-ecosystem: maven
       directory: "/declinaisons/java"
       schedule: { interval: weekly }
     - package-ecosystem: maven
       directory: "/declinaisons/java/tests-app"
       schedule: { interval: weekly }
   ```
   Activez *Dependabot alerts* et *security updates* sur votre fork (Settings → Code security). Observez les PR créées.
3. **OWASP Dependency-Check** est l'outil historique de l'écosystème Java
   (`mvn org.owasp:dependency-check-maven:13.0.0:check -DfailBuildOnCVSS=7 -DnvdApiKey=<clé>`). Il télécharge
   la base NVD et demande une clé d'API NVD (gratuite, à stocker en secret dans la CI) : sans clé, la mise à
   jour échoue. **Snyk** (compte gratuit) : `npx snyk test --file=pom.xml` — comparez avec OSV-Scanner.
4. Discussion : Dependabot vs Renovate ; bloquer sur **toute** CVE ou seulement HIGH/CRITICAL avec correctif ?

## Partie C — Image Docker (20 min)
```bash
docker build -t minishop-java .
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image minishop-java
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "$PWD":/out aquasec/trivy \
       image --format cyclonedx --output /out/sbom.cdx.json minishop-java
```
Trivy analyse les paquets du système **et** les bibliothèques Java embarquées dans `minishop.jar`.
Dans le `Dockerfile`, changez `eclipse-temurin:21-jre-alpine` en `eclipse-temurin:21-jdk` (image complète) :
combien de vulnérabilités en plus ? (Rétablissez ensuite, et ne committez pas `sbom.cdx.json`.)
Qu'est-ce qu'un **SBOM** et pourquoi les clients (et le Cyber Resilience Act) le demandent-ils ?

## Partie D — DAST avec OWASP ZAP (45 min)
1. Application lancée dans Docker (`docker compose up -d --build`), puis scan **baseline** (passif, quelques
   minutes). Les règles ZAP sont celles du dépôt, à la racine (`../../security/zap-rules.tsv`) :
   ```bash
   mkdir -p zap && cp ../../security/zap-rules.tsv zap/ && chmod 777 zap
   docker run --rm --network host -v "$PWD/zap":/zap/wrk ghcr.io/zaproxy/zaproxy:stable \
       zap-baseline.py -t http://localhost:8000 -c zap-rules.tsv -r zap-report.html
   ```
2. Lisez `zap/zap-report.html`. Corrigez au moins un avertissement : ajoutez un filtre (sur le modèle de
   `ObservabilityFilter`) qui pose `X-Content-Type-Options: nosniff` et une `Content-Security-Policy`.
   Passez la règle de `WARN` à `FAIL` dans `zap/zap-rules.tsv` : elle protège désormais contre une régression.
3. Scan d'API guidé par le schéma : `zap-api-scan.py -t http://localhost:8000/openapi.json -f openapi`
   (scan actif ; sans fichier de règles `-c`, tout y est avertissement : il informe, il ne bloque pas).
4. **Burp Suite** (démo formateur) : proxy d'interception, Repeater sur `/cart/quote` — complémentaire
   du scan automatique pour les tests manuels d'intrusion.

(Le dossier `zap/` est un dossier de travail : ne le committez pas.)

## Partie E — Pipeline `security-java.yml` (10 min)
Assemblez les jobs dans `.github/workflows/security-java.yml`, à la racine du dépôt (voir l'Atelier 2 pour la
structure ; l'image se construit avec `docker build -t minishop declinaisons/java`).
Décidez et justifiez ce qui bloque :

| Contrôle | Sur PR | Sur main | Nocturne |
|---|---|---|---|
| SpotBugs / FindSecBugs (`spotbugs:check`) | | | |
| OSV-Scanner | | | |
| Trivy HIGH/CRITICAL | | | |
| ZAP baseline | | | |
| ZAP API complet | | | |

## Critères de réussite
- [ ] La route `/debug/exec` est détectée par le SAST **et bloquée** par la commande retenue pour la pipeline
- [ ] Dependabot actif et au moins une alerte comprise
- [ ] SBOM généré
- [ ] Un en-tête de sécurité corrigé et verrouillé en `FAIL` dans ZAP
- [ ] Tableau de politique de blocage rempli et justifié

## Sous Windows

Poste sous **WSL2** : rien à adapter. En **PowerShell**, voir aussi les règles générales de l'Atelier 0.

**Partie A** : `mvn compile spotbugs:check` est identique ; mettez l'option de seuil entre guillemets
(`"-Dspotbugs.threshold=High"`).

**Partie B — OSV-Scanner**
```powershell
docker run --rm -v "${PWD}:/src:ro" ghcr.io/google/osv-scanner:latest scan source --lockfile /src/pom.xml
```
`npx snyk` demande Node.js.

**Partie C — Trivy** (Docker Desktop expose bien `/var/run/docker.sock` aux conteneurs)
```powershell
docker build -t minishop-java .
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image minishop-java
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "${PWD}:/out" aquasec/trivy image --format cyclonedx --output /out/sbom.cdx.json minishop-java
```

**Partie D — OWASP ZAP** : pas de `--network host` ni de `chmod` ; ZAP joint l'application par
`host.docker.internal`.
```powershell
docker compose up -d --build
New-Item -ItemType Directory -Force zap; Copy-Item ../../security/zap-rules.tsv zap/
docker run --rm -v "${PWD}/zap:/zap/wrk" ghcr.io/zaproxy/zaproxy:stable zap-baseline.py -t http://host.docker.internal:8000 -c zap-rules.tsv -r zap-report.html
docker run --rm -v "${PWD}/zap:/zap/wrk" ghcr.io/zaproxy/zaproxy:stable zap-api-scan.py -t http://host.docker.internal:8000/openapi.json -f openapi
```
Rapport : `start zap/zap-report.html`. En Git Bash, préfixez ces `docker run` par `MSYS_NO_PATHCONV=1`.

**Partie E** : le workflow `security-java.yml` s'exécute sur un runner Ubuntu, gardez la syntaxe bash de l'énoncé.
