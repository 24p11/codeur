# Documentation de la livraison recode-icd

Livraison **`65701d6_atih-2025`** (commit `65701d6` de recode-icd, kit ATIH 2025, générée le 18 octobre 2026), profil `generation`. Ce dossier contient **seulement la documentation** de la livraison, copiée telle quelle le 23 octobre 2026 ; aucun de ces documents ne contient de formulation ni de fiche (vérifié avant la copie : on n'y trouve que le squelette d'une fiche, le tableau de la famille `Z992` avec ses libellés ATIH, et des codes cités en exemple).

| Fichier | Contenu |
|---|---|
| `LIVRAISON.md` | Ce que la livraison contient (index, formulations, descendants codables, fiches) et ses chiffres |
| `extensions_preambule.md` | Les extensions PMSI : ce qu'elles sont, comment les lire |
| `resolveur_mode_emploi.md` | Le résolveur de recode-icd : d'un code écrit à sa fiche, ou la raison de son absence |
| `guide_usage_fiches.md` | La structure d'une fiche et la façon de l'employer |
| `CONTRAT.md` | Le contrat entre la bibliothèque de fiches et ses consommateurs (format, invariants) |

**Les données restent hors du dépôt** : l'index des codes (`codes.csv`), les formulations (`formulations.csv`, sans licence de rediffusion), les descendants codables et les fiches (`cards_library/`) sont dans `donnees/referentiels/recode-icd/65701d6_atih-2025/`, jamais suivis par git. L'index et les formulations sont chargés dans la base (`fiches`, `synonymes`, `descendants_codables`) ; les fiches attendent la revue par l'IA. Voir `docs/referentiels/README.md` §3.1 et `docs/chargement.md` §2.
