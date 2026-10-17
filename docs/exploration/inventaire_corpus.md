# Inventaire des corpus de CRH

*Note d'exploration, séance du 17 octobre 2026. Tous les chiffres ont été calculés par les scripts de `scripts/exploration/` sur les fichiers réels ; chaque affirmation indique sur combien de documents elle a été vérifiée.*

Cette note décrit, pour chaque source de comptes rendus, d'où elle vient, ce qu'elle contient, ce qu'elle apporte en matière de codage, ses particularités et les questions qu'elle soulève. Elle se termine par la liste des points à trancher lors de la séance sur le schéma. Elle ne tranche rien elle-même ; les décisions déjà prises figurent dans `CADRAGE.md` (§4.2) et sont rappelées ici en encadré.

---

## 1. PARHAF

### 1.1 Origine et récupération

PARHAF est un corpus ouvert de comptes rendus cliniques de patients fictifs, rédigés par des internes seniors et relus par un autre interne de la même spécialité, dans le cadre du projet PARTAGES (Health Data Hub). Licences CC BY 4.0 et Etalab 2.0. Version 1.0.0, déposée sur Hugging Face le 24 mars 2026 (seule la carte README a été modifiée depuis, jusqu'au 9 juin 2026).

- Identifiant Hugging Face : `HealthDataHub/PARHAF`. Public, sans jeton.
- Récupération : `uv run python -I scripts/exploration/01_telecharger_parhaf.py`, qui télécharge dans `donnees/parhaf/` (34 Mo au total) :
  - `data/train-00000-of-00001.parquet` (9 Mo) : version Hugging Face, texte inclus ;
  - `standalone/patients.json` (4 Mo) et `standalone/data.zip` (20 Mo, décompressé dans `standalone/textes/`, un dossier par spécialité, un fichier `.txt` par document) : version « standalone », déclarée **canonique** par les auteurs ;
  - `doc/PARTAGES_Guide_methodologique_de_redaction_et_de_relecture_des_CR_fictifs.pdf` : le guide donné aux rédacteurs ;
  - `README.md` : la carte du jeu de données.
- Le dépôt Hugging Face ne contient **que des données non annotées**. Health Data Hub publie des versions annotées pour la pseudonymisation, les biomarqueurs, la réponse au traitement, l'infectiologie et la conclusion, **mais aucune pour le codage CIM-10** (cas d'usage « CU 2 »), dont le jeu de test est sous embargo.

### 1.2 Les deux versions et leur écart

Vérifié par `02_comparer_versions_parhaf.py` sur l'ensemble des deux versions.

| | JSON + textes (canonique) | Parquet |
|---|---|---|
| Patients | 4 259 | 4 254 |
| Documents | 6 190 | 6 185 |
| Patients propres à cette version | 39 | 34 |
| Patients communs | 4 220 | 4 220 |

- Les 73 patients propres à l'une ou l'autre version sont **tous des anatomopathologies du pool « CU 5a - Oncology (biomarkers) »** (152 dans le JSON, 147 dans le parquet), avec des textes différents : ce sont deux extractions distinctes du même pool, et non une renumérotation.
- Pour les 4 220 patients communs, les 6 151 textes sont **strictement identiques** (comparaison caractère par caractère entre le parquet et le fichier `.txt`), avec les mêmes types et le même ordre.
- Le JSON correspond aux effectifs annoncés par la carte (4 259 patients, 6 190 documents).
- Dans le parquet, `documents` est un dictionnaire de listes (une liste de types, une de titres, une de textes…), et non une liste de documents : à remettre en forme si on l'utilise.

> **Décision (CADRAGE §4.2)** : on part du JSON, version de référence. L'écart ne concerne que des patients d'anatomopathologie, qui sont exclus.

### 1.3 Structure

Une entrée = **un patient**, pas un document. Champs (tous présents sur les 4 259 patients) :

| Champ | Contenu |
|---|---|
| `id`, `local_id` | Identifiant global (`SPECIALITE-NNNNN`) et local |
| `specialty` | Spécialité, 20 valeurs fermées |
| `pool` | Partition : General (3 577), CU 2 - ICD-10 coding (288), CU 5a (152), CU 6 - Infectiology (134), CU 5b (108) |
| `author`, `reviewer` | Trigrammes du rédacteur et du relecteur |
| `suggested_scenario` | Le scénario donné au rédacteur (voir 1.5) |
| `structured_abstract` | Résumé structuré facultatif saisi par le rédacteur, « non vérifié » (voir 1.5) |
| `documents[]` | 1 à 3 documents : `type`, `header` (titre), `path` (JSON) ou `text` (parquet), `word_count` |

Aucun champ de date, aucun champ d'ordre explicite.

### 1.4 Les documents

Vérifié par `03_inventaire_parhaf.py` sur les 4 259 patients et 6 190 documents.

**Types** : CRH 3 563, CRC (consultation) 1 079, CRO (opératoire) 889, ANAPATH 438, ACCOUCHEMENT 74, MATERNITE 74, URGENCES 73.

**Documents par patient** : 3 290 patients à 1 document, 7 à 2, 962 à 3. Combinaisons, dans l'ordre du fichier :

| Effectif | Combinaison | Remarque |
|---|---|---|
| 2 672 | CRH | |
| 886 | CRC > CRO > CRH | Chirurgies (viscérale, orthopédie, gynécologie, urologie, cardio-vasculaire) |
| 426 | ANAPATH | Anatomopathologie seule |
| 192 | CRC | Consultations d'oncologie seules |
| 72 | URGENCES > ACCOUCHEMENT > MATERNITE | Parcours obstétricaux |
| 6 | ANAPATH > ANAPATH | |
| 2 | CRH > ACCOUCHEMENT > MATERNITE | |
| 1 | CRO > CRH | |
| 1 | CRC > CRH > CRO | |
| 1 | URGENCES > CRO > CRH | |

696 patients n'ont aucun CRH (432 anapath, 192 consultations seules, 72 obstétrique). Aucun patient n'a plus d'un CRH.

**Ordre des documents.** Il n'y a pas de champ de date, mais 5 515 documents sur 6 190 contiennent au moins une date écrite (jj/mm/aaaa). Chez les 886 patients « CRC > CRO > CRH », la première date de chaque document croît dans l'ordre du fichier pour 616 patients ; 138 ont un document sans date ; les 132 cas restants sont des dates égales ou à un jour près (consultation d'anesthésie et hospitalisation le même jour, par exemple). Les 72 parcours obstétricaux sont croissants dans 63 cas. **L'ordre du fichier est donc l'ordre chronologique.** La concaténation suivra cet ordre.

**Longueurs** (en mots, champ `word_count`) :

| Type | n | min | médiane | max |
|---|---|---|---|---|
| CRH | 3 563 | 44 | 725 | 5 370 |
| CRC | 1 079 | 24 | 304 | 4 409 |
| CRO | 889 | 71 | 307 | 1 455 |
| ANAPATH | 438 | 136 | 393 | 4 953 |
| URGENCES | 73 | 269 | 516 | 897 |
| ACCOUCHEMENT | 74 | 167 | 287 | 755 |
| MATERNITE | 74 | 106 | 171 | 358 |

Par patient (documents concaténés) : minimum 136, médiane 798, maximum 7 006 mots. 225 CRH font moins de 100 mots : ce sont des « mini-CRH » d'ambulatoire en chirurgie viscérale (79), gynécologie (78), urologie (62) et orthopédie (6), qui disent en deux phrases que le patient a été opéré et est rentré chez lui ; l'information clinique est dans la consultation et le compte rendu opératoire qui les précèdent.

**Titres** (`header`) : 71 valeurs distinctes, de la forme « Compte rendu d'hospitalisation du service de … » ; la première ligne du texte reprend le titre. 3 titres seulement contiennent une date.

**Rubriques attendues** (présence du mot, sur les 3 563 CRH) : motif 2 996, antécédents 3 146, histoire de la maladie 3 063, examen clinique 2 585, évolution 1 404, conclusion 2 999, traitement de sortie 2 954.

### 1.5 Le codage et les variables du scénario

**Le seul codage disponible est le diagnostic principal du scénario** (`suggested_scenario.primary_diagnosis`) : présent pour les 4 259 patients, toujours un seul, sous la forme code + libellé. Codes **sans point** (K402, C61, I5009, F02801), 1 140 codes distincts. Il n'y a ni diagnostics associés, ni règle de hiérarchisation, ni code Z, ni élément de preuve. Le scénario ne comporte jamais d'acte CCAM.

> **Décision (CADRAGE §4.2)** : le DP du scénario est considéré comme le vrai DP du dossier et constitue le codage initial. La forme des codes sera alignée sur celle des fiches recode-icd.

Le **résumé structuré** (`structured_abstract`) existe pour 3 615 patients. Son DP concorde avec celui du scénario dans 3 608 cas et diverge dans 7. Il contient parfois un acte CCAM (1 029 patients), une durée de séjour (3 533), les modes d'entrée et de sortie (1 601). C'est une saisie libre du rédacteur, non vérifiée.

**Autres variables du scénario**, sur les 3 827 patients retenus (voir 1.7) :

- `name` (nom fictif), `age` (valeur + unité : ans 4 239, mois 20), `sex` (F 2 209, M 2 050) : toujours présents. Le nom du scénario figure dans 3 554 des 3 563 CRH.
- `type_of_care` : 141 valeurs distinctes, 189 absents (tous en cancérologie). Saisie libre, bruitée : variantes d'une même valeur (« Prise en charge médicale, en hospitalisation complète » 1 578 et « Prise en charge médicale en hospitalisation complète. » 145), suffixe doublé (« … en ambulatoire, en ambulatoire »), « NA, en hospitalisation complète » (33), apostrophe parasite en tête, espace insécable. La valeur se décompose presque toujours en **une famille de prise en charge** + **un mode d'hospitalisation** (« en ambulatoire » / « en hospitalisation complète »).
- `admission_mode` : 13 valeurs, 189 absents ; `discharge_mode` : 19 valeurs, 189 absents. Même bruit (fautes, annotations de l'auteur comme « domicile (à modifier pour entrée par les urgences) »).

> **Décision (CADRAGE §4.2)** : ces variables sont rangées avec le codage initial et ne sont jamais affichées au testeur. La spécialité et `type_of_care` servent de colonnes de recherche des dossiers.

**Correspondance proposée pour `type_of_care`** avec les familles du guide des situations cliniques (D diagnostic, T traitement, S surveillance), **à trancher en séance** :

Effectifs calculés par mots-clés sur les 3 827 patients retenus (chaque valeur n'est comptée qu'une fois, dans la première ligne qui la reconnaît) :

| Mots-clés dans la valeur | Effectif | Famille proposée | Remarque |
|---|---|---|---|
| « Chirurgie(s) … », « Hernies », « Cholécystectomies », « Appendicectomies », « Césariennes », « Accouchements », « Pontages », « Circoncisions », « Amygdalectomies », « Transplantations », « accès vasculaire », « Stimulateurs », « Lithotritie » | 936 | **T** | Séjour pour un acte thérapeutique |
| « Séances : chimiothérapie / radiothérapie / dialyse / aphérèse », « Chimiothérapie en hôpital de jour / en hospitalisation complète » | 259 | **T** | Séances et traitements itératifs ; le guide prévoit sans doute une règle propre aux séances (code Z51) |
| « Endoscopies digestives thérapeutiques » | 38 | **T** | |
| « Cathétérismes thérapeutiques … » | 34 | **T** | |
| « Interruptions médicales de grossesse », « Affections ante/post partum » | 9 | T | |
| « Cathétérismes diagnostiques … », « Endoscopies … avec ou sans anesthésie », « Arthroscopies, biopsies », « biopsie prostatique », « Découverte ou bilan du cancer » | 175 | **D** | Séjour à visée diagnostique |
| « Prise en charge médicale … » (toutes variantes, y compris « des tumeurs de … »), « Prise en charge chirurgicale … », « geste technique », « Activité interventionnelle », « Insuffisance rénale, avec dialyse » | 2 138 | **indéterminé** | Ne dit pas si le séjour est diagnostique ou thérapeutique ; seul le texte le dit |
| « Affections … sans acte opératoire, avec anesthésie », « Autres séj. sans acte » | 16 | indéterminé | Libellés de GHM |
| Absent (`None`), « NA, … » | 222 | aucune | |

Aucune valeur n'évoque la surveillance (S) : si cette famille existe dans le guide, elle ne pourra pas être déduite de `type_of_care`.

**Correspondance proposée pour les modes d'entrée et de sortie** avec les variables officielles du RUM (mode d'entrée / provenance, mode de sortie / destination), **à trancher en séance** :

| Valeur de `admission_mode` | Effectif | Proposition RUM |
|---|---|---|
| domicile ; domicile sans passer par le service des urgences ; domicile- service de gastro-entérologie | 2 195 | Mode 8 (domicile), sans provenance urgences |
| entrée par les urgences ; urgences ; admission par les urgences ; transfert par le service des urgences ; domicile (à modifier pour entrée par les urgences) | 1 289 | Mode 8 (domicile), provenance 5 (urgences) |
| admission non programmée suite à un contact avec le médecin traitant (ou un médecin suivant le patient) dans les 48h | 152 | Mode 8, sans passage par les urgences ; information « non programmée » à conserver à part (elle intervient dans certaines règles de codage) |
| transfert d'un autre hôpital | 1 | Mode 7 (transfert) |
| transfert depuis un autre service | 1 | Mode 6 (mutation) |
| absent | 189 | inconnu |

| Valeur de `discharge_mode` | Effectif | Proposition RUM |
|---|---|---|
| retour à domicile ; domicile | 3 447 | Mode 8 (domicile) |
| transfert en soins de suite et rééducation / réadaptation ; retour au soins de suite… ; ssr neurologique ; admission en smr | 119 | Mode 7, destination 2 (SMR) |
| décès | 60 | Mode 9 |
| transfert dans un autre hôpital ; transfert | 2 | Mode 7 |
| transfert dans un autre service ; en gynécologie ; en gastro-entérologie ; en psychiatrie | 6 | Mode 6 (mutation), ou 7 selon l'établissement |
| retour à domicile -> hématologie stérile ; → hospitalisation ; ; transfert gastrologie ; > changer pour transfert en chirurgie digestive | 4 | Ambigus : annotations de l'auteur, à lire au cas par cas |
| absent | 189 | inconnu |

### 1.6 Codes CIM-10 présents dans le texte lui-même

Vérifié par `05_codes_dans_texte_parhaf.py` et `06_verifications_parhaf.py` sur les 6 190 documents. Certains textes contiennent des résidus du gabarit de rédaction, avec des codes CIM-10 entre crochets. Trois cas :

1. **Bloc « Résumé structuré » recopié en fin de CRH** : 12 CRH (hématologie 3, cancérologie 2, neurologie 2, cardiologie, orthopédie, chirurgie viscérale, infectiologie, gériatrie 1 chacun). Le bloc contient le DP avec son code, parfois l'acte CCAM, la durée de séjour, les modes d'entrée et de sortie, et une rubrique « Diagnostics associés » en deux parties : « Sélection des diagnostics retenus dans la liste initiale » (codés) et « Autres diagnostics que vous avez choisis (en texte libre, sans codage) ». Il représente de 5 % à 63 % du texte (63 % pour un mini-CRH de 44 mots).
2. **Liste « Diagnostics fréquemment associés à ce diagnostic » en fin de consultation d'oncologie** : 49 CRC de cancérologie (50 avec le cas 3). C'est la liste informative fournie au rédacteur avec le scénario, laissée dans le texte, 1 à 11 codes. Dans un document, le titre apparaît deux fois.
3. **Liste codée sans titre en fin de consultation** : 1 CRC (CANCERO-ADULTE-01016), neuf diagnostics codés après la signature, sans ligne de titre.

S'y ajoutent **5 CRH où des codes entre crochets figurent dans le corps du texte** (liste d'antécédents codés en hématologie : 3, 7 et 1 codes ; conclusion d'un examen en gériatrie : 1 code chacun). Ce ne sont pas des blocs détachables : les retirer modifierait le compte rendu. Dans un seul de ces 5 cas, le code présent est le DP du scénario.

Les codes CIM-10 « nus » repérés ailleurs dans le corps (B12, J15, T12, P40…) sont des faux positifs (vitamine B12, quinzième jour, vertèbre T12, pouls).

> **Décision (CADRAGE §4.2)** : avant chargement, on retire tout ce qui n'est pas le compte rendu et on normalise les caractères ; le texte nettoyé devient le texte de référence ; le fichier source n'est jamais modifié ; chaque retrait est tracé et le passage retiré conservé à part, jamais affiché. **Le nettoyage n'a pas été fait dans cette séance** : seules les règles de repérage ont été écrites et vérifiées.

**Règles de repérage proposées** (expressions régulières de `06_verifications_parhaf.py`, appliquées ligne par ligne, insensibles à la casse et aux accents) :

| Règle | Déclencheur | Portée | Documents touchés | Contrôle |
|---|---|---|---|---|
| A | Une ligne entière « Résumé structuré », avec ou sans deux-points | De cette ligne jusqu'à la fin du texte | 12 CRH | Une seule occurrence par document. Les lignes du bloc sans code sont toutes des intitulés du gabarit (« Durée de séjour : N jours », « Sélection des diagnostics retenus… », « Autres diagnostics que vous avez choisis… ») ou des diagnostics en texte libre. La dernière ligne conservée est toujours une signature ou une phrase de conclusion. |
| B | Une ligne entière commençant par « Diagnostics fréquemment associés » | De cette ligne jusqu'à la fin du texte | 49 CRC | Idem ; dans le document où le titre apparaît deux fois, la première occurrence couvre les deux. Les 20 lignes de tirets sont à l'intérieur des blocs. |
| C (à définir) | Fin de texte constituée uniquement de lignes « - libellé [code] », après une signature | Le groupe de lignes | 1 CRC | Règle plus fragile ; peut aussi se traiter comme une exception nominative. |

Après application de A et B, les seuls documents retenus où subsiste un code entre crochets sont le CRC du cas 3 et les 5 CRH à codes dans le corps.

**Exemples avant / après** (fin du texte) :

- CANCERO-ADULTE-00024, CRH, règle A. Avant : « …Pose de CIP en prévision du début de 1ère ligne le 15/04 ⏎⏎ Résumé structuré ⏎⏎ Diagnostic principal motivant l'hospitalisation (code CIM 10) : Tumeur maligne du lobe inférieur, bronches ou poumon [C343] ⏎⏎ Durée de séjour : 11 jours ⏎⏎ Diagnostics associés : … ». Après : « …Pose de CIP en prévision du début de 1ère ligne le 15/04 ».
- CANCERO-ADULTE-00667, CRC, règle B. Avant : « …Bien à vous, confraternellement, ⏎⏎ Dr ONFURE oncologue médical. ⏎⏎ Diagnostics fréquemment associés à ce diagnostic : ⏎⏎ -   Tumeur maligne secondaire du poumon [C780] ⏎⏎ … ». Après : « …Bien à vous, confraternellement, ⏎⏎ Dr ONFURE oncologue médical. ».
- CANCERO-ADULTE-00669, CRC, règle B. Avant : « …Remise d'une ordonnance pour bilan anémie (…). ⏎⏎ Bien confraternellement, ⏎⏎ Dr MOUMOU ⏎⏎ Diagnostics fréquemment associés à ce diagnostic : ⏎⏎ -   Tumeur maligne secondaire du poumon [C780] … ». Après : « …Bien confraternellement, ⏎⏎ Dr MOUMOU ».

**Recherche d'autres résidus de gabarit** (hors blocs A et B, sur les documents retenus) : « Diagnostic principal motivant », « Mode de prise en charge (… », « Acte principal : », « Durée de séjour : », « code CIM », « liste initiale », « sans codage », « rédacteur », « relecteur », « fictif », « PARTAGES », « lorem », « xxx » : **aucun**. « CCAM » : 4 documents, où le chirurgien cite le code de son acte dans le compte rendu opératoire (contenu légitime). « scénario », « consigne », « à compléter » : usages cliniques normaux. Marqueurs markdown « ** » : 5 documents, résidus de mise en forme sans contenu à retirer. Lignes de tirets « ----- » : 23 documents, dont 20 dans les blocs B ; les autres sont des séparateurs de sections. **Aucun autre bloc de même nature n'a été trouvé.**

### 1.7 Patients retenus

> **Décision (CADRAGE §4.2)** : tous les patients sauf ceux dont le dossier ne comprend que de l'anatomopathologie.

Vérifié par `06_verifications_parhaf.py` :

- Les 10 cas atypiques : 6 « ANAPATH > ANAPATH » (exclus), les 4 autres (CRH > ACCOUCHEMENT > MATERNITE ×2, CRO > CRH, CRC > CRH > CRO, URGENCES > CRO > CRH) ne contiennent pas d'anatomopathologie (retenus).
- **Exclus : 432 patients, 438 documents** (426 « ANAPATH » + 6 « ANAPATH > ANAPATH »).
- **Retenus : 3 827 patients, 5 752 documents**, dont 2 864 à 1 document, 1 à 2, 962 à 3. Aucun document ANAPATH ne subsiste. Par pool : General 3 297, CU 2 - ICD-10 coding 288, CU 6 - Infectiology 134, CU 5b 108.

### 1.8 Diagnostics associés des 11 CRH au résumé structuré recopié

Information conservée **à part**, qui n'entre pas dans le codage initial (décision du 17 octobre 2026). Codes tels qu'ils figurent dans le texte (forme PMSI avec extensions : E11ni, R53+0, J961+0). Les diagnostics « en texte libre, sans codage » sont indiqués entre parenthèses.

| Patient | DP scénario | Diagnostics associés sélectionnés dans la liste initiale (codés) | Texte libre |
|---|---|---|---|
| CANCERO-ADULTE-00024 | C343 | Z8671, D630, C771, R451 | douleurs osseuses, dénutrition, perte d'autonomie à domicile |
| CANCERO-ADULTE-00189 | C509 | J91, R410, I5009, E8718, R5218, I10, R268 | initiation thérapie orale anticancéreuse, séance radiothérapie, antalgiques palier 3, métastases osseuses, pulmonaires, ganglionnaires, hépatiques, hypoalbuminémie, écoulement mammaire tumoral, activité physique adaptée, aides à domicile |
| CARDIOLOGIE-00133 | R074 | E11ni, I482, I255, Z6020, N184, I10, R53+0, N300, Z955, I7020 | (vide) ; acte DDQH012 |
| CHIR-ORTHO-ET-TRAUMATO-00066 | M0005 | A490, Y95, B956 | ; acte NEJA001 |
| CHIRURGIE-VISCERALE-00022 | K649 | aucun | ; acte EDSD011 |
| HEMATOLOGIE-CLINIQUE-00039 | D683 | Z952, E8768, E8718, Z512, N189, K564, I482, D648, Z921, Y442 | (points de suspension) |
| HEMATOLOGIE-CLINIQUE-00061 | D500 | N938, N920, D269 | |
| HEMATOLOGIE-CLINIQUE-00067 | D500 | K297, D50 (hors gabarit, saisis directement) | |
| MALADIES-INFECTIEUSES-00746 | U0710 | J128, E559, J961+0, I10, M4806, J91, F0631, E6695, E86, Z922 | (points de suspension) |
| MEDECINE-GERIATRIQUE-00004 | F02801 | aucun | arthrose pluri-articulaire, allergie à la pénicilline |
| NEUROLOGIE-00069 | G971 | aucun | aucun |
| NEUROLOGIE-00300 | G409 | R400 | |

(12 CRH portent le bloc ; 11 ont une rubrique « Diagnostics associés » non vide au sens large, 9 contiennent au moins un code.)

### 1.9 Particularités du texte

Vérifié sur les 6 190 textes :

- **Encodage** : UTF-8 sans exception, aucun BOM en tête de fichier, fins de ligne `\n` uniquement, aucun `\r`.
- **Mise en forme** : paragraphes séparés par une ligne vide, jamais trois sauts consécutifs, aucune tabulation ; chaque texte se termine par un `\n` (4 textes par « trois espaces + `\n` »). Listes à puces « -   » (tiret + trois espaces), parfois « · » ou « • ».
- **Aucun** texte vide, **aucun** doublon de texte, d'identifiant ou de chemin.
- **Caractères à normaliser** (ils déplacent les positions ou gênent la recherche) : accents décomposés (forme NFD) dans 19 documents ; espace fine insécable U+202F dans 27 ; espace insécable U+00A0 dans 41 ; caractère de largeur nulle U+200B dans 19 ; un BOM U+FEFF au milieu du texte dans 1 (CANCERO-ADULTE-00070, position 1 336) ; trait d'union conditionnel U+00AD dans 1.
- **Caractères légitimes mais inhabituels** : µ (2 373 occurrences), ² ³ ⁵ ₂, ®, ½ ⅓, →, ≥ ≈, ×, ◦, ᵉ ; tableaux de biologie avec séparateur « ¦ » dans 10 documents de cardiologie.
- Le champ `word_count` ne correspond pas à un simple comptage des mots séparés par des blancs (écart sur les 6 190 documents) : il a été calculé autrement ; ne pas s'y fier pour des mesures fines.

### 1.10 Questions soulevées par PARHAF

- Le DP du scénario a été considéré comme le vrai DP après quelques vérifications (CADRAGE §4.2) ; 7 résumés structurés d'auteur donnent un DP différent du scénario : à regarder le moment venu.
- Pour les 886 dossiers chirurgicaux, le CRH est souvent minimal et l'information est dans la consultation et le compte rendu opératoire : le testeur code bien le dossier concaténé, mais la « pathologie principale » surlignée se trouvera souvent hors du CRH.
- Les 192 consultations d'oncologie seules ne sont pas des séjours d'hospitalisation : elles sont retenues (décision §4.2), mais leur codage comme « séjour » est à discuter avec la règle de hiérarchisation.
- Le nom fictif du patient figure dans le texte : sans conséquence pour le codage, mais à savoir pour l'évaluation du document par le LLM.
- Le guide méthodologique PDF n'a pas été lu dans cette séance ; il pourrait préciser le gabarit de rédaction et expliquer les résidus trouvés.

---

## 2. CRH synthétiques

### 2.1 Origine et récupération

Comptes rendus générés par LLM dans le projet connexe de génération de CRH, à partir de scénarios tirés de données PMSI (campagne « C1 »). Un seul lot, un seul fichier, déposé sur Google Drive et copié à la main dans `donnees/synthetiques/` :

- `run08_scenarios_reports_merged_20261007_160916.parquet` : 228 Mo, **100 000 lignes, 97 colonnes**.
- Une ligne = **un document généré pour un séjour** (pas un patient : il n'y a jamais plusieurs documents par séjour).
- Modèle : `mistral-large-latest` pour les 100 000 lignes, générées du 2 au 7 octobre 2026.
- Un scénario (`id_scenario`, 89 501 valeurs distinctes) peut avoir été rendu en plusieurs **variantes** (10 364 scénarios ont 2 lignes, 29 en ont 3 à 5 ; colonne `variante`). Aucun texte n'est dupliqué à l'identique.

Scripts : `07_colonnes_synthetiques.py` (colonnes), `08_json_synthetiques.py` (clés du JSON), `09_coherence_synthetiques.py` (cohérence JSON / colonnes / texte), `10_colonnes_codage_synthetiques.py` (valeurs des colonnes de codage), `11_exemples_synthetiques.py` (exemples complets), `12_reparation_json_synthetiques.py` (JSON invalides), `13_titres_codes_cr_synthetiques.py` (titres et codes dans le texte).

### 2.2 Structure : trois couches

**Couche 1, les colonnes du scénario** (96 colonnes, toutes renseignées sauf mention contraire) :

| Groupe | Colonnes | Remarques |
|---|---|---|
| Patient | `age`, `age2`, `sexe` (1/2), `date_of_birth`, `first_name`, `last_name`, `cage` (classe d'âge), `population` (adulte 90 306, pédiatrie 9 694), `taille_cm`, `poids_kg`, `imc`, `classe_imc`, `tabac`, `alcool` (absents sur 10 996 lignes) | Noms fictifs |
| Séjour | `date_entry`, `date_discharge` (2024 à 2026), `los` (0 : 69 501, 1 : 18 851, 2 : 11 484, puis 7 à 30 jours pour les 177 lignes de la branche « long »), `admission_mode` (DOMICILE 79 102, URGENCES 20 898), `discharge_disposition` (DOMICILE 92 328, SMR 5 968, DECES 1 704), `mode_hospit` = `admission_type` (HP 56 886, HC 43 114), `TPEC` (Médecine 53 000, Chirurgie et interventionnel 47 000), `DPEC` (5 valeurs), `hospital` (23 noms d'hôpitaux réels), `department`/`specialty` (55 valeurs, absents sur 10 164 lignes), `ghm2`, `drg_parent_code` + description | `date_discharge - date_entry` = `los` sur 99 526 lignes |
| **Codage du scénario** | `icd_primary_code` + `icd_primary_description` (DP, 3 241 codes distincts), `icd_secondary_code` (liste de DAS, 0 à 17, 18 706 lignes sans DAS) + `text_secondary_icd_official`, `case_management_type` + description (**code Z de prise en charge, ou la valeur « DP »** quand le DP motive lui-même le séjour : 70 171 lignes « DP », 205 codes Z distincts), `procedure` + `text_procedure` (acte CCAM, vide sur 4 560 lignes), **`coding_rule`** (règle de hiérarchisation, 20 valeurs), `situa` (situation clinique en texte libre, 2 279 valeurs, vide sur 2 861 lignes), `dp_origine`, `dp_substitue` (13 407 DP substitués), `nb_das`, `codes_ajoutes` + `enrichi` (89 004 lignes enrichies de codes tabac/alcool/obésité : F17…, F10…, E66…), `icd_parent_code` | Codes **sans point**, avec extensions PMSI (« K635+0 », « E11ni » : 1 120 DP avec « + ») |
| Oncologie | `cancer_stage`, `score_TNM`, `histological_type`, `treatment_recommandation`, `chemotherapy_regimen`, `biomarkers` | Renseignés sur environ 2 400 lignes |
| Génération | `template_name` (6 gabarits), `system_prompt` (6), `user_prompt` = `scenario`, `prefix`, `code_cards_codes` / `_found_codes` / `_missing_codes` / `_text` (les fiches de codes fournies au LLM), `model`, `timestamp`, `prompt_tokens`, `completion_tokens`, `total_tokens`, `generation_id`, `source_row_id` (uniques), `graine`, `poids`, `branche`, `campagne`, etc. | Trace complète de la génération |

Les 6 gabarits : `medical_outpatient` 40 136, `medical_inpatient` 30 543, `surgery_outpatient` 12 497, `surgery_inpatient` 11 078, `medical_outpatient_onco` 4 887, `medical_inpatient_onco` 859.

**Règles de codage** (`coding_rule`) : other 56 745, T3 23 452, S1-Chronic 5 647, vide 4 320, T1 3 040, D1 1 878, D5 1 774, D9 947, D3-1 775, T2-R52 415, T2-Toxine 243, D3-2 164, T11 162, T2-J9 112, T8 97, T4 90, T2-R18 57, T7 49, T6 28, T5 5. Les familles D / T / S du guide des situations cliniques sont donc **directement présentes** pour 38 935 lignes ; « other » et vide (61 065 lignes) correspondent surtout à la situation « prise en charge diagnostique et thérapeutique du diagnostic principal ».

**Couche 2, le champ `report`** : ce n'est pas un texte suivi d'un JSON, mais **un objet JSON complet** dont la clé `CR` contient le compte rendu, et la clé `formulations` le codage. Structure constatée sur les 84 657 lignes analysables sans réparation :

```
{
  "CR": "<texte du compte rendu, en markdown>",
  "formulations": {
    "diagnostics": {
      "<libellé officiel> (<code>)": ["<formulation 1>", "<formulation 2>", ...],
      ...
    },
    "informations": {
      "Nom/Prénom du patient": [...], "Âge": [...], "Sexe": [...],
      "Date entrée": [...], "Date de sortie": [...], "Service d'hospitalisation": [...],
      "État général": [...], "Poids": [...], "NFS": [...], "Créatinine": [...],
      "Bilan hépatique": [...], "Traitements": [...], ...
    }
  }
}
```

- `CR` : toujours présent (chaîne). `formulations` : présent sur 36 862 des 36 868 objets strictement valides ; 8 objets sur 84 657 n'ont pas de `formulations.diagnostics` exploitable.
- `formulations.diagnostics` : un objet dont **chaque clé est « libellé (CODE) »** et chaque valeur **une liste de formulations**, c'est-à-dire les tournures du texte qui justifient le code. 1 à 18 diagnostics par ligne (médiane 3) ; 0 à 14 formulations par diagnostic (0 : 360 cas ; 1 : 60 518 ; 2 : 114 840 ; 3 : 60 338). Les codes des clés sont **tantôt avec point (148 304), tantôt sans (119 145)**, et 72 clés n'ont pas de code en fin.
- `formulations.informations` : 12 à 15 rubriques administratives et biologiques, listes de chaînes, toujours les mêmes noms (variantes « Bilan hépatique » / « Bilan hepatique »). Pour les gabarits chirurgicaux : « Intervention », « Date de l'intervention », « Nom/Prénom du chirurgien ».
- Pour 13 lignes d'oncologie, des rubriques supplémentaires apparaissent au niveau de `formulations` (« Évolutivité tumorale », « Traitements antitumoraux »…).
- **Aucune position** (début/fin) : les éléments de preuve sont des **citations**, à retrouver dans le texte.
- **Ni règle de hiérarchisation, ni code Z, ni catégorie (DP/DAS) dans le JSON** : ces informations sont dans les colonnes. La catégorie d'un code du JSON se déduit en le rapprochant de `icd_primary_code` et `icd_secondary_code`.

**Couche 3, le texte `CR`** : markdown (titres `###` sur les 84 657 textes, gras `**` sur 73 163), sauts de ligne `\n` uniquement, 171 à 1 395 mots (médiane 551). Il commence par le nom d'un hôpital réel, le service, un titre, l'identité fictive du patient, puis des sections. Rubriques les plus fréquentes : Antécédents, Mode de vie, Histoire de la maladie, Examen clinique, Examens complémentaires, Évolution pendant l'hospitalisation, Conclusion (gabarits médicaux) ; Intervention, Date de l'intervention, Rappel clinique, Technique utilisée, Constatations per-opératoires, Matériels utilisés, Nom du chirurgien (gabarits chirurgicaux). La rubrique « traitement de sortie » n'existe que dans 184 textes. **Les deux gabarits chirurgicaux produisent un « Compte rendu opératoire », pas un CRH** (23 575 lignes).

### 2.3 Validité du JSON

Vérifié par `12_reparation_json_synthetiques.py` sur les 100 000 lignes :

| Situation | Lignes |
|---|---|
| JSON strictement valide | 36 868 |
| Valide en mode tolérant (`strict=False` : sauts de ligne bruts dans les chaînes) | 84 657 |
| Réparable en ajoutant une accolade fermante manquante | + 11 656 |
| Réparable en retirant une accolade fermante en trop | + 1 385 |
| Réparable en retirant une clôture ``` de fin | + 207 |
| **Total analysable avec ces réparations simples** | **97 905** |
| Non réparé simplement (1 861 se terminent par « }]} », probablement une structure en liste au lieu d'un objet ; non vérifié) | 2 095 |

Les échecs touchent tous les gabarits (de 188 à 626 lignes chacun).

### 2.4 Cohérence entre le JSON, les colonnes et le texte

Vérifié par `09_coherence_synthetiques.py` sur les 84 649 lignes analysables sans réparation :

- **Codes du JSON contre codes du scénario** (DP + DAS, après suppression des points) : le DP manque dans le JSON sur 639 lignes, et 1 870 DAS sur 183 147 manquent ; dans les cas examinés, c'est l'extension qui diffère (« K635+0 » en colonne, « K635 » dans le JSON ; « D126+3 » / « D126 »). Le code Z de `case_management_type` n'est repris dans le JSON que sur 7 lignes. Le JSON contient des **codes absents du scénario** sur 2 421 lignes (2 460 codes : Z992, F03, B24, J961, K635…), soit des codes ajoutés par le LLM, soit des formes tronquées.
- **Formulations retrouvées dans le texte** (610 582 formulations) : 513 020 à l'identique (84,0 %), 62 614 à la casse et aux espaces près (10,3 %), 37 aux accents près, **34 911 introuvables (5,7 %)**. Les introuvables sont des paraphrases (« HTA essentielle » pour « hypertension artérielle », « polype dégénéré du côlon ascendant »).

### 2.5 Codage et blocs parasites présents dans le texte

Vérifié par `13_titres_codes_cr_synthetiques.py` et un comptage complémentaire sur les 84 657 textes :

- **1 455 textes CR contiennent un bloc « Dictionnaires des formulations » ou un objet JSON recopié** après la signature : le LLM a inséré le codage dans le texte au lieu de le mettre dans la clé `formulations`. C'est un bloc de même nature que ceux de PARHAF, à retirer avec traçage. Règle de repérage à construire : une ligne « **Dictionnaires des formulations** » ou un `{"` ouvrant après la dernière section, jusqu'à la fin du texte (non testée dans cette séance).
- 274 textes ont une rubrique « **Diagnostics** » en gras (à examiner : liste de diagnostics codés ou simple rubrique narrative).
- 188 textes contiennent un code CIM-10 entre parenthèses ou crochets (I10, E66.03, F17.25…), dont une partie dans les blocs ci-dessus et une partie dans le corps (« tumeur à évolution imprévisible (D37.4) »).
- 9 textes mentionnent « CIM-10 ».
- 10 345 textes n'ont pas de ligne de titre « Compte rendu … » (le document commence directement par l'hôpital et les sections).

### 2.6 Particularités et anomalies

- Les noms d'hôpitaux sont **réels** (AP-HP, CHU de Bordeaux, Toulouse, Grenoble…) ; patients et médecins sont fictifs.
- `nb_das` compte les DAS du scénario avant enrichissement ; `icd_secondary_code` inclut les codes ajoutés (`codes_ajoutes`) : 40 961 lignes ont `nb_das` = 0, mais seulement 18 706 ont une liste de DAS vide.
- `case_management_type` mélange une valeur conventionnelle (« DP ») et des codes Z : à séparer en « mode de prise en charge = DP » et « code Z ».
- `coding_rule` est vide sur 4 320 lignes et vaut « other » sur 56 745 ; `situa` est vide sur 2 861 lignes. Les libellés de `situa` comportent des coquilles (« diagnotic »).
- Les formulations du JSON ne sont pas toutes des diagnostics au sens strict : les codes tabac/alcool/obésité ajoutés par enrichissement ont presque toujours une formulation (« Tabagisme actif… »).
- 10 164 lignes sans spécialité (`specialite_source` = « repli »).

### 2.7 Questions soulevées par les CRH synthétiques

- Les 23 575 comptes rendus opératoires sont-ils des « dossiers » à coder au même titre que les CRH ? Ils ne contiennent ni antécédents détaillés ni évolution.
- Les 2 095 JSON non réparables simplement : les exclure, ou écrire une réparation spécifique ?
- Faut-il conserver les variantes d'un même scénario (10 393 scénarios à plusieurs rendus) ? Pour l'outil, deux testeurs sur deux variantes du même scénario codent « le même séjour » avec des textes différents.
- Les codes ajoutés par le LLM hors scénario (2 421 lignes) : erreurs ou enrichissements légitimes ? Le codage initial doit-il être les colonnes (le scénario) ou le JSON (ce que le texte dit) ?
- Le volume (100 000) dépasse de loin le besoin du démonstrateur : quel sous-ensemble charger (par gabarit, par règle de codage, par spécialité) ?

---

## 3. Points à décider lors de la séance sur le schéma

Chaque point liste les options sans trancher.

1. **Unité de dossier et concaténation (PARHAF).** Décidé : un dossier = un patient, documents concaténés dans l'ordre du fichier, intitulé visible avant chaque document, limites conservées. Reste à fixer : la forme de l'intitulé (le `header` du document, ou un libellé normalisé par type), le séparateur entre documents, et si les positions des limites se comptent sur le texte concaténé avec ou sans intitulés.
2. **Texte de référence et nettoyage.** Décidé : nettoyage avant chargement, texte ensuite figé, retraits tracés. À fixer : (a) la liste des normalisations (NFC, U+00A0 et U+202F en espace simple ou conservés, U+200B et U+FEFF supprimés, U+00AD supprimé, markdown des CRH synthétiques conservé, converti en texte brut, ou rendu) ; (b) les règles A, B, C de PARHAF et la règle « Dictionnaires des formulations » des synthétiques ; (c) où ranger les passages retirés (champ JSON du document, table à part) ; (d) le sort des 5 CRH PARHAF et des codes « dans le corps » des synthétiques, qui ne sont pas des blocs détachables : conserver tel quel, exclure le document, ou masquer le code seul.
3. **Format JSON du codage.** Le JSON des synthétiques sert de modèle (CADRAGE §4.2), mais il n'a ni catégorie, ni règle, ni code Z, ni positions. Options : (a) reprendre sa forme « libellé (code) → formulations » en y ajoutant catégorie, règle, code Z et positions ; (b) une forme « liste de codes » avec, pour chaque code : code, libellé, catégorie (DP/DA/Z), preuves (texte cité, début, fin), et à côté la règle et le code Z ; (c) la forme (b) pour la base et une conversion vers (a) pour les prompts. Dans tous les cas, fixer la forme des codes (point ou non, extensions PMSI « +0 », « ni »), alignée sur recode-icd.
4. **Codage initial des synthétiques.** Options : les colonnes du scénario (DP, DAS, code Z, règle, acte), le JSON `formulations` (codes + citations), ou les deux fusionnées (colonnes pour la liste des codes et leur catégorie, JSON pour les preuves). Et que faire des 2 421 lignes où le JSON ajoute des codes hors scénario.
5. **Preuves du codage initial.** PARHAF n'en a pas. Les synthétiques ont des citations sans position, dont 5,7 % introuvables. Options : calculer les positions au chargement (première occurrence, toutes les occurrences) et marquer les introuvables ; ou stocker les citations seules.
6. **Périmètre des documents chargés.** PARHAF : 3 827 patients (décidé). Synthétiques : tout ou un échantillon ; avec ou sans les comptes rendus opératoires ; avec ou sans les variantes ; avec ou sans les 2 095 JSON non réparés.
7. **Métadonnées et champ RUM.** Décidé : peu de colonnes, un champ JSON RUM au format officiel, créé mais non alimenté. À fixer : la correspondance des modes d'entrée/sortie de PARHAF (tables ci-dessus) et des synthétiques (DOMICILE/URGENCES, DOMICILE/SMR/DECES) vers les codes RUM ; où ranger `type_of_care`, `coding_rule`, `situa`, `case_management_type`, les variables onco.
8. **Colonnes de recherche.** Décidé : spécialité et type de prise en charge. À fixer : la normalisation des 141 valeurs de `type_of_care` (PARHAF) et leur équivalent pour les synthétiques (`DPEC`, `TPEC`, `mode_hospit`, ou une famille D/T/S déduite de `coding_rule`).
9. **Identifiants.** PARHAF : `id` patient. Synthétiques : `source_row_id` (unique) ou `generation_id` ; conserver `id_scenario` et `variante` pour regrouper les variantes.
10. **Traçabilité des lots.** Ce que la table `lots` dit de chaque source : version (PARHAF 1.0.0 JSON ; synthétiques run08 du 7 octobre 2026), ce qu'elle contient (texte seul + DP ; texte + DP + DAS + code Z + règle + citations), règles de nettoyage appliquées.
