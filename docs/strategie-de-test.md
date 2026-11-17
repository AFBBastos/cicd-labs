# Stratégie de test — MiniShop

> Modèle à compléter pendant l'Atelier 12. Une stratégie de test tient sur 2 pages : si elle est plus longue, personne ne la lit.

## 1. Périmètre et risques
| Zone | Risque métier | Probabilité | Impact | Niveau de test principal |
|---|---|---|---|---|
| Calcul des prix (`pricing.py`) | Mauvais montant facturé | Moyenne | Élevé | Unitaire + génération IA |
| API commandes | Commande perdue | Faible | Élevé | API + contrat |
| Interface | Parcours bloqué | Moyenne | Moyen | E2E + visuel |
| Performance | Abandon de panier | … | … | Charge (Locust/JMeter) |
| Sécurité | Fuite / injection | … | … | SAST, SCA, DAST (ZAP) |

## 2. Pyramide et quality gates
| Étape pipeline | Tests | Seuil bloquant |
|---|---|---|
| PR | lint, unitaires, API | 100 % OK, couverture ≥ 85 % |
| main | + E2E, visuel, sécurité | 0 vulnérabilité HIGH/CRITICAL |
| nocturne | charge, ZAP complet | p95 < 300 ms, erreurs < 1 % |

## 3. Règles pour les tests générés par IA
| # | Règle | Comment elle est vérifiée |
|---|---|---|
| 1 | Un test généré porte le marqueur `@pytest.mark.generated` et vit dans `tests/generated/`. | `pytest -m generated` les isole ; `pytest -m "not generated"` mesure la suite sans eux. |
| 2 | Un test généré est **relu par un humain** avant fusion, comme du code : une PR, un relecteur qui connaît la règle métier. | Revue de PR. Le relecteur vérifie la **valeur attendue** de chaque `assert` contre la spécification, pas contre le code. |
| 3 | Un test sans `assert` (ou qui ne peut pas échouer) est refusé. | Lecture, puis mutation : le test doit tuer au moins un mutant. |
| 4 | Le score de mutation de `pricing.py` ne baisse pas quand on intègre des tests générés ; seuil visé : ≥ 80 %. | `python ai_tools/mutation_score.py minishop/pricing.py tests/unit` avant fusion. |
| 5 | Un test généré qui échoue n'est **jamais** corrigé en recopiant la valeur renvoyée par le code. On tranche : bug de l'application (ticket), spécification fausse (on la corrige) ou hallucination (on supprime le test). | Le motif est écrit dans la PR. |
| 6 | Aucun secret, aucune donnée client, aucune donnée de production dans un prompt. On n'envoie que la spécification et le code du module testé. | Prompts versionnés dans `ai_tools/prompts/` et relus ; jeux de données fictifs uniquement. |
| 7 | Le fournisseur du modèle et le modèle sont choisis par l'équipe (`LLM_PROVIDER`, `LLM_MODEL`), avec une clé à quota limité stockée en secret. Code confidentiel : modèle local ou moteur offline. | Variables du workflow ; pas de clé personnelle. |
| 8 | Le prompt est du code : toute modification passe par une PR, avec le tableau de comparaison (nombre de tests, échecs, couverture, mutation). | Historique Git de `ai_tools/prompts/`. |
| 9 | Dans la pipeline, la génération **informe** et ne bloque pas (`continue-on-error`) ; les tests générés sont publiés en artefact et un humain décide de les intégrer. | Workflow `ai-tests.yml`. |

**Responsabilité.** Une fois fusionné, un test généré appartient à l'équipe, au même titre qu'un test écrit
à la main : la personne qui a ouvert la PR et celle qui l'a approuvée en répondent. « C'est l'IA qui l'a
écrit » n'est pas une explication recevable. Un test généré faux découvert après coup se traite comme un
défaut : ticket, correction, et vérification des autres tests issus de la même génération.

**Régénération.** Les fichiers de `tests/generated/` produits par le moteur offline ne se modifient pas à la
main : on corrige la spécification et on régénère. Un test généré par LLM que l'on a retouché sort de
`tests/generated/` et rejoint `tests/unit/` (il perd le marqueur `generated`).

## 4. Gestion des tests instables (flaky)
- Détection : `ai_tools/test_history.py` (score ≥ 0,6).
- Quarantaine : marqueur `flaky`, ticket ouvert, délai de correction 5 jours.

## 5. Indicateurs suivis
Taux de réussite sur main, durée de la suite, nombre de tests flaky, couverture, MTTR d'une régression.
