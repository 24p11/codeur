# Guide d'usage — bibliothèque de fiches CIM-10 (profil `generation`)

> Public : data scientists consommant les fiches pour construire des
> prompts de génération de textes médicaux annotés. Ce guide décrit ce
> que contient la bibliothèque, comment s'y retrouver, et ce qu'il ne
> faut PAS en faire.

## Ce que c'est

Une fiche Markdown par code CIM-10 **codable en MCO** (kit ATIH), plus
les 211 troncs de composition du chapitre XX — 15 282 fiches, rangées
par chapitre (`IX/I64.md`). Chaque fiche agrège tout ce que les
référentiels officiels (OFS 2006, ANS 2025) et les sources
complémentaires validées disent du code, avec la provenance tracée.
**Couverture : tout code autorisé en MCO a sa fiche** (invariant I1) ;
**aucun code non codable n'est présenté comme émissible** (invariant
I2, une exception déclarée : les troncs du chapitre XX, marqués).

## Structure d'une fiche

```
# I64 — Accident vasculaire cérébral, non précisé …    ← titre officiel
Statut MCO (kit ATIH 2025) : …                          ← autorisation de codage
## Périmètre clinique du code                           ← inclusions officielles (OFS/ANS)
## Définition (CIM-10)                                  ← définition officielle, si elle existe
## Description clinique (OMS)                           ← glossaire officiel (chapitre F surtout)
## Localisations / subdivisions                         ← si pertinent
## À ne pas décrire                                     ← exclusions (l'affection vit AILLEURS)
## Consignes de codage (guide méthodologique 2026)      ← consignes [rec_id], si le code est régi
## Notes de la CIM-10                                   ← règles d'emploi officielles de la classification
## Formulations cliniques alternatives                  ← langage réel des CRH (voir ci-dessous)
```

Points d'attention :

- **« À ne pas décrire » n'est pas une négation** : chaque entrée
  désigne une affection qui appartient à un AUTRE code (souvent indiqué
  entre parenthèses). Un texte généré pour ce code ne doit pas décrire
  ces affections.
- **« Formulations cliniques alternatives »** reflète le langage
  réellement employé par les médecins (Index CIM-10 vol3, thésaurus
  AP-HP, dictionnaire CepiDc). Cette section est **curée au rendu** :
  plafonnée par famille de sources, normalisée, et filtrée d'un
  registre archaïque validé cliniquement (vocabulaire de certificat de
  décès — « apoplexie congestive », « misère physiologique » — écarté
  ligne à ligne). Elle ne définit jamais le périmètre du code : le
  périmètre, c'est la section « Périmètre clinique ».
- **Troncs du chapitre XX** (`W00`…) : fiche marquée en première ligne
  « non codable seul — se compose du lieu (4ᵉ caractère) et de
  l'activité (5ᵉ caractère) », avec la table de composition. Un code
  composé (`W0009`) n'a pas de fiche propre : sa fiche est celle du
  tronc (cf. mode d'emploi du résolveur).

## `index.csv` — le point d'entrée programmatique (cf. CONTRAT.md)

Une ligne par fiche. Le **noyau garanti** par le contrat
(`CONTRAT.md`, `format_version` 1) : `code`, `fichier`, `statut_mco`,
`format_version`. Les principales colonnes :

| Colonne | Contenu |
|---|---|
| `code`, `chapter`, `fichier` | identité et chemin relatif de la fiche |
| `libelle` | libellé officiel |
| `has_perimetre` … `has_notes_cim` | présence de chaque section (booléens — y compris `has_definition`, `has_description_clinique`, `has_notes_cim`) : de quoi arbitrer quelles fiches valent leur coût en tokens |
| `type_mco`, `statut_mco` | statut d'autorisation au kit ATIH |
| `classe_generation` | `emissible` ou `tronc_composition` (chapitre XX) |
| `nb_chars` | taille de la fiche |

Usage type (polars) :

```python
import polars as pl
idx = pl.read_csv("cards_library/index.csv")
emissibles = idx.filter(pl.col("classe_generation") == "emissible")
```

## Ce qu'il ne faut pas faire

1. **Ne pas tirer un tronc de composition comme un code émissible** :
   filtrer sur `classe_generation == "emissible"` pour l'échantillonnage,
   ou composer un code complet (tronc + lieu + activité).
2. **Ne pas joindre « à la main » sur le code** pour retrouver une
   fiche : passer par le résolveur (`recode-icd resoudre`), qui accepte
   toutes les écritures (compacte `O0490`, pointée `O04.90`) et motive
   chaque absence.
3. **Ne pas traiter les Formulations comme une définition** du code ni
   comme une liste exhaustive : c'est un échantillon curé de langage
   vivant, plafonné et filtré.
4. **Ne pas éditer les fiches** : elles sont régénérées de façon
   déterministe à chaque build ; toute correction passe par les données
   ou la curation amont.

## Les autres fichiers du paquet

- **`codes.csv`** : TOUS les codes du kit ATIH (codables ou non), avec
  la clé `code_atih` (sans point, extension collée) — la seule source
  de la liste des codes ; voir CONTRAT.md.
- **`formulations.csv`** : le vivier de recherche par mots-clés
  (formulations rendues, sans plafond).
- **`descendants_codables.csv`** : pour un code proposé non codable
  (ou codable mais tronqué), la liste de ses descendants codables avec
  libellés, dans l'ordre du kit — la matière de la boucle de
  correction/affinage.
- **`extensions_preambule.md`** : les extensions PMSI expliquées.
