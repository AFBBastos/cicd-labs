# L'atelier dans un autre langage que Python

Python vous freine ? Ce dossier reprend l'atelier en **PHP, Java, Node.js et C#**.

## Ce qui est décliné

**L'application MiniShop complète** est portée dans chaque langage : règles de prix, catalogue, API HTTP,
page web, métriques Prometheus, journal JSON, image Docker et les deux bugs injectables
(`MINISHOP_BUG=rounding` et `MINISHOP_BUG=slow`). Les quatre applications sont **interchangeables** avec
l'application Python : mêmes routes, mêmes réponses, mêmes noms de métriques, même port 8000. Tout ce qui
teste MiniShop de l'extérieur fonctionne donc sans modification.

Chaque dossier contient :

- le projet prêt à l'emploi (gestionnaire de paquets, tests, couverture, lint, `Dockerfile`) ;
- les **tests de départ** : règles de prix, API en mémoire, API par HTTP, bout en bout ;
- les énoncés des **Ateliers 1 à 4, 8, 9 et 11** adaptés au langage ;
- `ateliers/autres-ateliers.md`, pour les Ateliers 5, 6, 7, 10 et 12.

| Langage | Dossier | Cadriciel | Tests | Mutation | Bout en bout | Sécurité (code, dépendances) |
|---|---|---|---|---|---|---|
| PHP 8.3+ | [`php/`](php/) | Slim 4 | PHPUnit | Infection | Symfony Panther | Psalm, `composer audit` |
| Java 21+ | [`java/`](java/) | Spring Boot | JUnit, JaCoCo | PIT | Playwright | SpotBugs + FindSecBugs, OSV-Scanner |
| Node.js 20+ | [`node/`](node/) | Fastify | Vitest | Stryker | Playwright Test | `eslint-plugin-security`, `npm audit` |
| C# / .NET 10 | [`csharp/`](csharp/) | ASP.NET Core | xUnit, coverlet | Stryker.NET | Playwright | analyseurs Roslyn, Semgrep, `dotnet list package --vulnerable` |

## Ce qui reste en Python

Les outils du dossier `ai_tools/` (génération de tests, revue de PR, anomalies, modèle de risque, comparaison
visuelle) restent des scripts Python que vous **lancez** sans les modifier : l'environnement de l'Atelier 0
suffit. Ils lisent le journal et les métriques de votre application, quel que soit son langage.

Quelques réponses d'erreur diffèrent légèrement de l'application Python (libellés des erreurs de validation,
conversion d'une quantité envoyée sous forme de chaîne) : le `README.md` de chaque dossier les liste.

## Par où commencer

1. Faites l'Atelier 0 (installation) du dépôt principal.
2. Ouvrez le `README.md` du dossier de votre langage, installez les dépendances, lancez les tests de départ.
3. Suivez `ateliers/atelier-01-tests-unitaires.md` de ce dossier à la place de l'énoncé Python.

Le pipeline de l'Atelier 2 se crée dans `.github/workflows/ci-<langage>.yml`, **à la racine du dépôt**,
avec `working-directory: declinaisons/<langage>`.

Un guide de Python pour celles et ceux qui préfèrent poursuivre dans ce langage, avec les équivalences
entre les cinq langages, est fourni à part par le formateur (mini-site « Python pour l'atelier CI/CD »).
