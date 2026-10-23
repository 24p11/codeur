# Livraison — bibliothèque de fiches CIM-10, profil `generation`

**Version** : commit `65701d6` · kit ATIH **atih-2025** · générée le
2026-10-18 · dépôt `recode-icd`.

## Contenu

| Fichier | Rôle |
|---|---|
| `cards_library/` | 15282 fiches Markdown, une par code codable en MCO (15071 émissibles + 211 troncs de composition du chapitre XX), rangées par chapitre |
| `cards_library/index.csv` | index canonique (noyau garanti : `code`, `fichier`, `statut_mco`, `format_version`) — **commencer ici** ; `_index.csv` déprécié, dernier cycle |
| `cards_library/CONTRAT.md` | le contrat de l'index : noyau garanti, sémantique `tronc_composition`, canal officiel |
| `codes.csv` | TOUS les codes du kit ATIH (42897) : `code_atih` (sans point, extension collée — la clé des consommateurs), forme pointée, libellé, `codable_mco`, `statut_mco` — la seule source de la liste des codes |
| `formulations.csv` | 109987 formulations rendues (après R1/R3/registre archaïque, SANS plafond R2) pour la recherche par mots-clés |
| `descendants_codables.csv` | 19974 couples (nœud du kit, descendant codable avec fiche) pour la boucle de correction/affinage — même logique que le résolveur |
| `extensions_preambule.md` | les extensions PMSI expliquées, généré du kit |
| `guide_usage_fiches.md` | structure des fiches, usage de l'index, les quatre « à ne pas faire » |
| `resolveur_mode_emploi.md` | `recode-icd resoudre` : toute écriture d'un code → fiche ou raison motivée |

## Garanties de cette version

- **Couverture 100 %** : tout code autorisé en MCO a sa fiche
  (invariant I1) ; le chapitre XX est couvert par composition
  (25 348 codes composés → 1 021 troncs, dont 211 portent une
  fiche de génération).
- **Aucun code non codable présenté comme émissible** (invariant I2) —
  seule exception, déclarée et marquée : les troncs du chapitre XX
  (`classe_generation=tronc_composition`).
- **Formulations filtrées du registre archaïque** : 136
  formulations de certificat de décès / terminologie désuète écartées
  sur verdict clinicien ligne à ligne (validation RF
  2026-09-09, complément 2026-09-12).
- Fiches **déterministes** : même dépôt, même build, mêmes octets.

## Point d'entrée conseillé

1. Lire `CONTRAT.md`, charger `index.csv`, filtrer `classe_generation == "emissible"`.
2. Lire la fiche via `fichier`.
3. Pour tout code venant d'ailleurs (autre écriture, code composé,
   code interdit) : passer par le résolveur, jamais par une jointure
   manuelle — cf. `resolveur_mode_emploi.md`.

Retours et codes non résolus : joindre le journal du résolveur
(`--journal`) à vos remontées.
