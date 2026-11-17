# Atelier 11 — Tests de sécurité automatisés (2 h 30) — déclinaison C#

**Module 3** · Compétence C18 (DevSecOps) — OWASP ZAP, analyse des dépendances (Snyk, Dependabot)

## Objectif
Intégrer quatre familles de contrôles de sécurité dans la pipeline et savoir lesquels doivent bloquer.

| Famille | Question | Outil de l'atelier | Équivalents |
|---|---|---|---|
| SAST (code) | Mon code contient-il des motifs dangereux ? | Analyseurs de sécurité Roslyn (règles `CA2xxx`, `CA3xxx`, `CA5xxx`), Semgrep | SonarQube, CodeQL |
| SCA (dépendances) | Mes bibliothèques ont-elles des CVE connues ? | Audit NuGet (`dotnet restore`, `dotnet list package --vulnerable`), Dependabot | Snyk, OWASP Dependency-Check, Renovate |
| Conteneur | Mon image embarque-t-elle des paquets vulnérables ? | Trivy (+ SBOM) | Grype, Docker Scout |
| DAST (appli qui tourne) | L'application exposée est-elle attaquable ? | OWASP ZAP | Burp Suite, Nuclei |

Tout l'atelier porte sur l'application C# de ce dossier : son code (parties A et B), son image Docker
(partie C) et l'application qui tourne (partie D). Les commandes se lancent depuis `declinaisons/csharp/`,
sauf mention contraire.

## Partie A — SAST (25 min)
1. Les analyseurs Roslyn tournent à chaque compilation ; une partie seulement des règles de sécurité est
   active par défaut. Comparez :
   ```bash
   dotnet build --no-incremental
   dotnet build --no-incremental -p:AnalysisLevelSecurity=latest-all      # toutes les règles de sécurité
   ```
2. Ajoutez à l'application un fichier `src/MiniShop.Api/Debug.cs` volontairement dangereux :
   ```csharp
   using System.Data.Common;
   using System.Diagnostics;
   using System.Security.Cryptography;
   using System.Text;

   namespace MiniShop.Api;

   public static class Debug
   {
       public static string Empreinte(string coupon) => Convert.ToHexString(MD5.HashData(Encoding.UTF8.GetBytes(coupon)));

       public static string CodePromo() => "PROMO" + new Random().Next(1000, 9999);

       public static void Chercher(DbCommand commande, string produit)
       {
           ArgumentNullException.ThrowIfNull(commande);
           commande.CommandText = "SELECT * FROM products WHERE id = '" + produit + "'";
       }

       public static void Lancer(string programme)
       {
           using var p = Process.Start(programme);
       }
   }
   ```
   Relancez les deux commandes, puis un second outil :
   ```bash
   docker run --rm -v "$PWD/src":/src semgrep/semgrep semgrep scan --config p/csharp --metrics=off /src
   ```
   Lesquels des quatre pièges chaque outil détecte-t-il ? Avec quelle sévérité (ici, un avertissement est une
   erreur de compilation : `TreatWarningsAsErrors`) ? Lequel n'est détecté par personne, et pourquoi ?
   Laquelle de ces commandes arrêterait le fichier piégé dans une pipeline (code retour différent de 0), et
   pour combien de pièges : `dotnet build --no-incremental`, la même avec
   `-p:AnalysisLevelSecurity=latest-all`, ou la commande SARIF de l'étape 3 ? (Retirez le fichier ensuite !)
3. Format **SARIF** + onglet *Security* de GitHub :
   ```bash
   dotnet build src/MiniShop.Api --no-incremental -p:TreatWarningsAsErrors=false \
       -p:AnalysisLevelSecurity=latest-all "-p:ErrorLog=analyse.sarif%2Cversion=2.1"
   ```
   (`%2C` est une virgule : format SARIF 2.1 ; un rapport par projet compilé, `src/MiniShop/analyse.sarif` et
   `src/MiniShop.Api/analyse.sarif`) puis
   `github/codeql-action/upload-sarif@v4` (permissions `security-events: write`, et `actions: read`
   si le dépôt est privé ; l'onglet n'existe sur un dépôt privé qu'avec GitHub Code Security).
   Ne commitez pas les fichiers `.sarif`. Cherchez `CA5394` dans celui de l'API, même sans le fichier piégé :
   l'alerte de `Observability.cs` y figure comme **supprimée** (`#pragma warning disable`, avec sa
   justification en commentaire). Dans quels cas une suppression est-elle acceptable ?

## Partie B — Dépendances (30 min)
1. `dotnet list package --vulnerable --include-transitive` → propre ? Ajoutez
   `<PackageReference Include="Newtonsoft.Json" Version="12.0.3" />` dans
   `src/MiniShop.Api/MiniShop.Api.csproj`, puis :
   ```bash
   dotnet restore                                   # NuGet audite les paquets à chaque restauration
   dotnet restore -p:TreatWarningsAsErrors=false    # la même alerte, en simple avertissement
   dotnet list package --vulnerable --include-transitive --no-restore
   ```
   Quel code d'erreur NuGet, quelle sévérité, quel avis de sécurité ? Notez deux pièges : `dotnet list
   package --vulnerable` renvoie toujours 0 (dans une pipeline, c'est `dotnet restore` qui bloque), et il lit
   le résultat de la dernière restauration **réussie**. Retirez ensuite la ligne et relancez `dotnet restore` :
   `packages.lock.json` doit revenir à son état d'origine (`git status`).
2. **Dependabot** : le fichier `.github/dependabot.yml` est fourni à la racine. Ajoutez-y les paquets NuGet et
   l'image de base du `Dockerfile` de ce dossier :
   ```yaml
     - package-ecosystem: nuget
       directory: "/declinaisons/csharp"
       schedule: { interval: weekly }
     - package-ecosystem: docker
       directory: "/declinaisons/csharp"
       schedule: { interval: weekly }
   ```
   Activez *Dependabot alerts* et *security updates* sur votre fork (Settings → Code security). Observez les PR créées.
3. **Snyk** (compte gratuit) : `npx snyk test --all-projects` — comparez avec l'audit NuGet.
4. Discussion : Dependabot vs Renovate ; bloquer sur **toute** CVE ou seulement HIGH/CRITICAL avec correctif ?
   (voir les propriétés `NuGetAuditLevel` et `NuGetAuditMode`)

## Partie C — Image Docker (20 min)
```bash
docker build -t minishop-csharp .
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image minishop-csharp
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "$PWD":/out aquasec/trivy \
       image --format cyclonedx --output /out/sbom.cdx.json minishop-csharp
```
Trivy analyse les paquets Ubuntu de l'image **et** les bibliothèques .NET embarquées (fichiers `*.deps.json`).
Dans le `Dockerfile`, changez l'image finale `mcr.microsoft.com/dotnet/aspnet:10.0` en
`mcr.microsoft.com/dotnet/sdk:10.0` (image complète) : combien de paquets et de vulnérabilités en plus ?
Retirez la ligne `apt-get upgrade` : que devient le résultat ?
Qu'est-ce qu'un **SBOM** et pourquoi les clients (et le Cyber Resilience Act) le demandent-ils ?

## Partie D — DAST avec OWASP ZAP (45 min)
1. Application lancée dans Docker (`docker compose up -d --build`), puis scan **baseline** (passif, quelques
   minutes). Les règles ZAP sont communes à toutes les déclinaisons : `security/zap-rules.tsv`, à la racine du dépôt.
   ```bash
   mkdir -p zap && cp ../../security/zap-rules.tsv zap/ && chmod 777 zap
   docker run --rm --network host -v "$PWD/zap":/zap/wrk ghcr.io/zaproxy/zaproxy:stable \
       zap-baseline.py -t http://localhost:8000 -c zap-rules.tsv -r zap-report.html
   ```
2. Lisez `zap/zap-report.html`. Corrigez au moins un avertissement : ajoutez dans `src/MiniShop.Api/Program.cs`
   un middleware (`app.Use(...)`) qui pose `X-Content-Type-Options: nosniff` et une `Content-Security-Policy`
   sur chaque réponse. Passez la règle de `WARN` à `FAIL` dans `zap-rules.tsv` : elle protège désormais
   contre une régression.
3. Scan d'API guidé par le schéma, avec le même fichier de règles :
   `zap-api-scan.py -t http://localhost:8000/openapi.json -f openapi -c zap-rules.tsv`
4. **Burp Suite** (démo formateur) : proxy d'interception, Repeater sur `/cart/quote` — complémentaire
   du scan automatique pour les tests manuels d'intrusion.

## Partie E — Pipeline `security-csharp.yml` (10 min)
Assemblez les jobs dans `.github/workflows/security-csharp.yml`, à la racine du dépôt (voir énoncé de
l'Atelier 2 pour la structure et `working-directory`), avec un déclenchement nocturne (`schedule:`) en plus
des PR : une CVE publiée dans la journée est vue avant la prochaine PR. Décidez et justifiez ce qui bloque :

| Contrôle | Sur PR | Sur main | Nocturne |
|---|---|---|---|
| Analyseurs Roslyn, toutes les règles de sécurité (`-p:AnalysisLevelSecurity=latest-all`) | | | |
| Audit NuGet | | | |
| Trivy HIGH/CRITICAL | | | |
| ZAP baseline | | | |
| ZAP API complet | | | |

## Critères de réussite
- [ ] Le code piégé est détecté par le SAST **et bloqué** par la commande retenue pour la pipeline
- [ ] Dependabot actif et au moins une alerte comprise
- [ ] SBOM généré
- [ ] Un en-tête de sécurité corrigé et verrouillé en `FAIL` dans ZAP
- [ ] Tableau de politique de blocage rempli et justifié

## Sous Windows

- Parties A et B : commandes `dotnet` identiques en PowerShell ; pour Semgrep, `-v "${PWD}/src:/src"`, et la
  commande SARIF s'écrit sur une seule ligne.
- Parties C, D et E : voir la section « Sous Windows » de l'énoncé d'origine (`ateliers/atelier-11-securite.md`),
  en remplaçant l'image `minishop` par `minishop-csharp` et `security/zap-rules.tsv` par `../../security/zap-rules.tsv`.
