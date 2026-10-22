# Référentiels

*Fichier `docs/referentiels/README.md` du dépôt `codeur`. Il recense tous les référentiels dont l'outil a besoin : d'où ils viennent, leur version, leur licence, où ils sont rangés, et leur état. Il est tenu à jour à chaque nouvelle livraison.*

---

## 1. Deux emplacements

Le dépôt est public. Les référentiels sont donc rangés à deux endroits :

| Emplacement | Contenu | Dans le dépôt ? |
|---|---|---|
| `docs/referentiels/` | Les référentiels **publics et de petite taille** | Oui |
| `donnees/referentiels/` | Les livraisons de recode-icd, **volumineuses** et dont certaines sources **ne sont pas rediffusables** | **Non** (dossier exclu de git). Seules leur version et leur empreinte figurent dans ce fichier |

## 2. L'arborescence

```
docs/referentiels/                      (dans le dépôt)
├── README.md                           ce fichier
├── atih/
│   └── formats_mco_2026.xlsx           format officiel du RUM (RSS non groupé, format 023)
├── situations_cliniques/
│   └── guide_situations_cliniques.csv  guide des règles de hiérarchisation, corrigé
└── qualite/
    ├── grille_qualite.md               les cinq dimensions et leurs repères de 1 à 5
    └── controles_pmsi.md               les règles de contrôle qualité du prototype

donnees/referentiels/                   (hors du dépôt)
└── recode-icd/
    └── <version-de-la-livraison>/      un dossier par livraison (ex. 65701d6_atih-2025), jamais modifié
        ├── recode-icd_…tar.gz          l'archive livrée
        └── extrait/<livraison>/        sa décompression : codes.csv (tous les codes, clé code_atih),
                                        formulations.csv, descendants_codables.csv, cards_library/ (index.csv,
                                        CONTRAT.md, fiches par chapitre), LIVRAISON.md, guide et mode d'emploi
```

**Une livraison de recode-icd n'est jamais modifiée** : une nouvelle livraison crée un nouveau dossier. La base indique toujours la version chargée (table `fiches`, colonne de version), et l'on peut revenir à une livraison antérieure.

## 3. La liste des référentiels

### 3.1 Référentiels de codage (issus de recode-icd)

**recode-icd est la seule source de la liste des codes CIM-10 pour `codeur`.** La sélection des codes codables à partir du référentiel officiel de l'ATIH (et de sa notice explicative) est faite dans recode-icd, une fois pour toutes ; `codeur` ne retraite pas lui-même le fichier de l'ATIH. L'index, les fiches et les formulations proviennent toujours de la même livraison.

| Référentiel | Usage dans `codeur` | Lot | État | Version | Licence |
|---|---|---|---|---|---|
| **Index des codes** : code complet sans point, extension collée ; libellé ; indicateur « codable » ; statuts MCO | Vérification des codes, boucle de correction, contrôles qualité | B3 | **Chargé** le 22 octobre 2026 (`fiches`, 42 897 codes ; `descendants_codables`, 19 974) | `65701d6_atih-2025` (kit ATIH 2025) | Données ATIH |
| **Fiches d'identité des codes** : une par code codable, éventuellement vide si elle n'apporte rien | Revue par l'IA | B3 (livraison actuelle), puis chantier recode-icd | Livrées (15 282 fiches dans `cards_library/`), **non chargées** (attendent la revue) | `65701d6_atih-2025` | À préciser |
| **Formulations** : code, formulation, source | Recherche par mots-clés, codes candidats dans le prompt | B3 | **Chargé** le 22 octobre 2026 (`synonymes`, 109 987 formulations + 42 897 libellés) | `65701d6_atih-2025` | **Aucune licence indiquée dans la livraison** : en base seulement, jamais dans le dépôt ; sources CepiDc 2015, CIM-10 index, thésaurus AP-HP |

### 3.2 Référentiels réglementaires et métier

| Référentiel | Usage | Lot | État | Version | Licence |
|---|---|---|---|---|---|
| **Format RUM** (`atih/formats_mco_2026.xlsx`), feuille « RSS non groupé format 023 » | Structure du champ RUM | — | Fourni | 023 | Publication ATIH |
| **Guide des situations cliniques** (`situations_cliniques/`) | Proposition de la règle de hiérarchisation, contrôle règle / pathologie principale | Avant A2 | **En cours de correction** (doublons S2/S3, Z95/Z96, D5/D6, S4, noms de listes à remplacer) | | Interne au projet |

### 3.3 Référentiels à rédiger

| Référentiel | Usage | Lot | État |
|---|---|---|---|
| **Grille de qualité** (`qualite/grille_qualite.md`) : cinq dimensions (organisation, langage, cohérence médicale, synthèse, qualité générale), un repère pour chaque note de 1 à 5 | Évaluation du document par l'IA et par le testeur | A2, A5 | À rédiger |
| **Règles de contrôle qualité PMSI** (`qualite/controles_pmsi.md`) | Contrôles sur le RUM | A4 | À rédiger ; une partie reposera sur les statuts MCO de l'index |
| **Mention d'information et accord** des testeurs | Fiche d'inscription | A1 | À rédiger |
| **Prompts** des quatre tâches (dans `prompts/`, numérotés par version) | Appels au LLM | A2, B4 | À rédiger |

### 3.4 Autres éléments à fournir

| Élément | Usage | Lot | Emplacement |
|---|---|---|---|
| **Calculs des mesures fixes** du projet de génération | Évaluation du document | A1 | À reprendre dans le code de la page |
| **Les 5 CRH de PARHAF à corriger** | Chargés tels quels en version 1 et signalés `a_corriger` (lot B1, fait) ; corrigés par Rémi avec la page d'édition, ce qui crée leur version 2 (`docs/SCHEMA.md` §9.5) | A6 | Dans la base (versions 1 puis 2) |

### 3.5 Plus tard

| Élément | Usage |
|---|---|
| Fonction groupage de l'ATIH | Groupage des RUM (hors prototype pour l'instant) |
