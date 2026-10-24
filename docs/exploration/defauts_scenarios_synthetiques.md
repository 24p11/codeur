# Incohérences des scénarios des CRH synthétiques au regard du guide des situations cliniques

*Source : les 100 000 lignes du fichier `run08_scenarios_reports_merged_20261007_160916.parquet` (colonnes `icd_primary_code`, `coding_rule`, `case_management_type`), confrontées le 24 octobre 2026 au guide des situations cliniques version 1 (`docs/referentiels/situations_cliniques/`, chapitres I à XVII, XIX et XXII) et à la fonction `regles_compatibles`. Rapport chiffré destiné au projet de génération ; le détail par ligne (identifiants) reste hors du dépôt, dans `donnees/prepare/situations/defauts_scenarios.csv`. Les dossiers concernés sont à traiter à part dans les analyses de la règle de hiérarchisation. Script : `scripts/referentiels/defauts_scenarios.py`.*

## Chiffres

| Mesure | Lignes |
|---|---|
| Lignes de la source | 100000 |
| Lignes confrontables (règle connue du guide, ni `other` ni vide) | 38935 |
| Règle inconnue du guide | 0 |
| **1. Code Z (chapitre XXI) en DP**, hors Z80-Z99 | 3962 |
| Z80-Z99 en DP (admis : antécédents et états, règle D4), pour mémoire | 2124 |
| **2. Règle incompatible avec le DP** (lignes confrontables) | 2246 |
| **3. Code Z de prise en charge hors de la liste de sa règle** | 1548 |
| **3 bis. « DP » alors que la règle impose un code Z** | 101 |
| **4. T1 avec « DP »** (compris dans 3 bis) | 37 |
| Lignes avec au moins un défaut | 6705 |

## Détail

### 1. Codes Z en DP, par catégorie

| Catégorie | Lignes |
|---|---|
| Z45 | 781 |
| Z04 | 475 |
| Z47 | 316 |
| Z49 | 296 |
| Z51 | 295 |
| Z30 | 173 |
| Z09 | 155 |
| Z46 | 151 |
| Z53 | 133 |
| Z43 | 116 |
| Z71 | 105 |
| Z48 | 102 |
| Z01 | 83 |
| Z31 | 81 |
| Z52 | 70 |
| Z42 | 68 |
| Z41 | 64 |
| Z50 | 61 |
| Z35 | 53 |
| Z29 | 52 |
| Z76 | 40 |
| Z13 | 36 |
| Z00 | 34 |
| Z03 | 32 |
| Z21 | 27 |
| Z39 | 27 |
| Z74 | 26 |
| Z61 | 16 |
| Z12 | 16 |
| Z40 | 15 |
| Z34 | 11 |
| Z27 | 10 |
| Z36 | 10 |
| Z75 | 6 |
| Z60 | 5 |
| Z08 | 5 |
| Z23 | 5 |
| Z02 | 4 |
| Z72 | 3 |
| Z59 | 2 |
| Z65 | 2 |

### 2. Règle incompatible avec le DP, par règle

| Règle | Lignes |
|---|---|
| T3 | 1091 |
| D9 | 598 |
| D3-1 | 184 |
| D3-2 | 73 |
| S1-Chronic | 56 |
| T7 | 49 |
| T2-Toxine | 41 |
| T1 | 37 |
| D1 | 35 |
| D5 | 35 |
| T6 | 28 |
| T11 | 17 |
| T5 | 2 |

### 3. Mode de prise en charge hors de la liste de la règle (ou « DP » imposé code Z), par règle et mode

| Règle | Mode | Lignes |
|---|---|---|
| T3 | Z421 | 178 |
| T3 | Z4580 | 125 |
| T3 | Z080 | 97 |
| T3 | Z450 | 91 |
| T3 | Z082 | 84 |
| T3 | Z470 | 73 |
| T3 | Z098 | 71 |
| T3 | Z490 | 51 |
| T7 | DP | 48 |
| T3 | Z087 | 46 |
| T2-R52 | Z4584 | 43 |
| T1 | DP | 37 |
| T3 | Z088 | 35 |
| T3 | Z52801 | 32 |
| T3 | Z4582 | 32 |
| T3 | Z4000 | 30 |
| T2-R52 | Z098 | 30 |
| T3 | Z420 | 28 |
| T2-Toxine | Z098 | 26 |
| T3 | Z466 | 24 |
| T3 | Z090 | 21 |
| T3 | Z4584 | 18 |
| T3 | Z422 | 18 |
| T3 | Z453 | 18 |
| T11 | DP | 16 |
| T3 | Z312 | 16 |
| T2-R52 | Z512 | 15 |
| T8 | Z452 | 13 |
| T3 | Z4001 | 13 |
| T8 | Z087 | 12 |

## Lecture

- Le défaut 1 vient du générateur qui place le code de prise en charge (Z45, Z04, Z47, Z49, Z51…) en DP au lieu de la pathologie ; `codeur` attend la pathologie en pathologie principale et le code Z en mode de prise en charge. Les codes Z80 à Z99 (antécédents, états) sont admis en DP par la règle D4 et ne sont pas comptés comme défaut.
- Le défaut 2 signale une règle qui ne peut pas s'appliquer à la pathologie du scénario (par exemple D9, bilan d'extension d'un cancer, avec un DP hors du chapitre II).
- Les défauts 3 et 4 signalent un mode de prise en charge étranger à la règle (un code Z avec T3, qui n'en prévoit aucun ; « DP » avec T1, qui impose un code Z).
- Les lignes de règle `other` ou vide ne sont pas confrontables : la règle n'est pas renseignée dans le scénario.
