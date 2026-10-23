# Listes de codes CIM-10

Listes issues du **projet Stream** (génération de CRH synthétiques), fournies par Rémi le 23 octobre 2026, converties au format commun `code,libelle` (virgule, UTF-8, codes à la forme `codeur` : sans point, extension PMSI collée ; libellé officiel de l'index recode-icd `65701d6_atih-2025`). Une catégorie sans point (`Z95`, `Z80`) désigne la catégorie et ses descendants codables. Chargées dans la table `listes_codes` (nature `cim`) par `scripts/chargement/listes_charger.py` ; les fichiers du dépôt restent la source.

| Fichier | Codes | Usage (guide des situations cliniques, version 1) |
|---|---|---|
| `icd_codes_cardic_vascular_implants.csv` | 11 | disponible, non citée par le guide |
| `icd_codes_chronic_attack.csv` | 23 | règle D6 (codes spécifiques de poussée aiguë, à confirmer à l'étape 3) |
| `icd_codes_diabetes_chronic.csv` | 69 | règle T9-diabetes (pathologie) |
| `icd_codes_family_history.csv` | 69 | disponible, non citée par le guide |
| `icd_codes_iron_deficiency_anemia.csv` | 5 | règle T10-fer (pathologie) |
| `icd_codes_ivg.csv` | 41 | disponible, non citée par le guide |
| `icd_codes_legal_abortion.csv` | 10 | règle IVG (pathologie) |
| `icd_codes_liveborn_infants.csv` | 10 | règle T13 (pathologie) |
| `icd_codes_medical_abortion.csv` | 30 | règle ITG (pathologie) |
| `icd_codes_overnight_study.csv` | 2 | disponible, non citée par le guide |
| `icd_codes_personnel_history.csv` | 127 | disponible, non citée par le guide |
| `icd_codes_preoperative_assessment.csv` | 1 | disponible, non citée par le guide |
| `icd_codes_prophylactic_intervention.csv` | 8 | disponible, non citée par le guide |
| `icd_codes_sensitization_tests.csv` | 1 | disponible, non citée par le guide |
| `icd_codes_sessions.csv` | 9 | disponible, non citée par le guide |
| `icd_codes_spontaneous_vertex_delivery.csv` | 1 | règle T12 (pathologie) |
| `icd_codes_supervision.csv` | 55 | disponible, non citée par le guide |
| `icd_codes_supervision_chronic_disease.csv` | 23 | disponible, non citée par le guide |
| `icd_codes_supervision_post_partum.csv` | 6 | disponible, non citée par le guide |
| `icd_codes_supervision_pregnancy.csv` | 15 | disponible, non citée par le guide |
| `icd_codes_surgical_followup.csv` | 4 | disponible, non citée par le guide |
| `icd_codes_transplanted_organ.csv` | 20 | disponible, non citée par le guide |
| `icd_primary_exclusions.csv` | 96 | disponible, non citée par le guide |

## Codes retirés à la conversion (23 octobre 2026)

Un code est retiré seulement s'il n'existe pas dans le kit ATIH 2025 ou s'il n'y est pas codable sans descendant codable, et que ses équivalents sont déjà dans la liste ou n'existent pas. Rien n'a été ajouté.

| Liste | Code d'origine | Motif | Équivalents |
|---|---|---|---|
| `icd_codes_diabetes_chronic` | `E11i` | inconnu du kit 2025 | équivalents déjà dans la liste (E11 et ses subdivisions) |
| `icd_codes_diabetes_chronic` | `E11ni` | inconnu du kit 2025 | équivalents déjà dans la liste (E11 et ses subdivisions) |
| `icd_codes_ivg` | `O040` | non codable sans descendant (pere_interdit) | équivalents déjà dans la liste (O0400, O0401, O0402, O0403) |
| `icd_codes_ivg` | `O041` | non codable sans descendant (pere_interdit) | équivalents déjà dans la liste (O0410, O0411, O0412, O0413) |
| `icd_codes_ivg` | `O042` | non codable sans descendant (pere_interdit) | équivalents déjà dans la liste (O0420, O0421, O0422, O0423) |
| `icd_codes_ivg` | `O043` | non codable sans descendant (pere_interdit) | équivalents déjà dans la liste (O0430, O0431, O0432, O0433) |
| `icd_codes_ivg` | `O044` | non codable sans descendant (pere_interdit) | équivalents déjà dans la liste (O0440, O0441, O0442, O0443) |
| `icd_codes_ivg` | `O045` | non codable sans descendant (pere_interdit) | équivalents déjà dans la liste (O0450, O0451, O0452, O0453) |
| `icd_codes_ivg` | `O046` | non codable sans descendant (pere_interdit) | équivalents déjà dans la liste (O0460, O0461, O0462, O0463) |
| `icd_codes_ivg` | `O047` | non codable sans descendant (pere_interdit) | équivalents déjà dans la liste (O0470, O0471, O0472, O0473) |
| `icd_codes_ivg` | `O048` | non codable sans descendant (pere_interdit) | équivalents déjà dans la liste (O0480, O0481, O0482, O0483) |
| `icd_codes_ivg` | `O049` | non codable sans descendant (pere_interdit) | équivalents déjà dans la liste (O0490, O0491, O0492, O0493) |
| `icd_codes_personnel_history` | `Z86090` | non codable sans descendant (pere_interdit) | aucun équivalent |
| `icd_codes_transplanted_organ` | `Z94801` | non codable sans descendant (supprime) | équivalents déjà dans la liste (Z94800, Z94802, Z94803, Z94804, Z94809) |
| `icd_primary_exclusions` | `Z2028` | inconnu du kit 2025 | aucun équivalent |

## Codes ajoutés (23 octobre 2026)

`icd_codes_chronic_attack` sert de pathologie à la règle D6 (« code spécifique de poussée aiguë »). Ajoutés pour couvrir les exemples de la règle D6 du guide méthodologique : `I200` (angor instable) ; et, le guide écrivant « E1–.1 » pour l'acidocétose diabétique, les codes de coma et d'acidocétose des diabètes E12, E13 et E14 sous leur forme codable dans le kit 2025 (`E120`, `E121`, `E130`, `E131`, `E140`, `E141`) ; le type 1 (`E100`, `E101`) et le type 2 (`E1100`, `E1108`, `E1110`, `E1118`) y étaient déjà.
