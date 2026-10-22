# Charger les corpus dans la base

*Mode d'emploi des scripts de `scripts/chargement/`. Le schéma est décrit dans `docs/SCHEMA.md` ; la connexion à la base dans `docs/base_de_donnees.md`.*

Le chargement d'un corpus se fait en deux temps, par deux scripts distincts : la **préparation**, qui lit les fichiers sources et écrit, hors du dépôt, un fichier par dossier prêt à charger ; puis le **chargement**, qui lit ces fichiers et les insère dans la base avec la clé secrète. Un script de vérification relit ensuite la base. Les fichiers sources de `donnees/` ne sont jamais modifiés.

## 1. PARHAF (lot `parhaf-1.0.0`)

### 1.1 Préparer

```
uv run python -I scripts/chargement/parhaf_preparer.py
```

Lit `donnees/parhaf/standalone/patients.json` et les textes (version JSON de PARHAF, téléchargée par `scripts/exploration/01_telecharger_parhaf.py`). Ne se connecte pas à la base. Produit dans `donnees/prepare/parhaf/` (hors dépôt) :

- `documents/<id_source>.json` : un fichier par dossier retenu, avec le texte de référence, les colonnes de recherche, le champ `nettoyage` et le codage initial ;
- `rapport.md` : effectifs, passages retirés par règle, normalisations, dossiers à corriger, longueurs, codes DP ;
- `codes_dp_a_verifier.csv` : les codes de diagnostic principal distincts, à confronter à l'index de recode-icd au lot B3.

Ce que fait la préparation, dans l'ordre (`docs/SCHEMA.md` §2 et §3.7) : sélection des patients (tous sauf ceux dont le dossier n'est que de l'anatomopathologie : 3 827 retenus sur 4 259) ; retrait des blocs parasites de chaque document d'origine (règles A « Résumé structuré », B « Diagnostics fréquemment associés », cas C nominatif), avec conservation des passages retirés et de leurs positions ; normalisation (NFC, suppression de U+200B, U+FEFF, U+00AD, remplacement de U+00A0 et U+202F par une espace, retrait des blancs de fin de document) ; concaténation dans l'ordre du fichier avec un intitulé devant chaque document quand le dossier en compte plusieurs ; codage initial réduit au diagnostic principal du scénario. Les 5 CRH contenant des codes dans leur corps sont chargés tels quels et signalés `a_corriger` dans `nettoyage.anomalies`.

### 1.2 Charger

```
uv run python -I scripts/chargement/parhaf_charger.py --essai    # 10 dossiers variés, pour vérifier
uv run python -I scripts/chargement/parhaf_charger.py            # chargement complet, par paquets de 100
```

Insère la ligne du lot, un document par dossier (version 1, `cree_par` vide) et un codage `scenario` par document (`valide` faux, utilisateur et compteurs vides). Relançable sans risque : un dossier déjà présent (même lot, `id_source`, version) est signalé et passé, après contrôle que son empreinte en base est celle du texte préparé ; un document sans codage `scenario` reçoit le sien. À la première erreur, le script s'arrête en indiquant le paquet concerné ; une relance reprend sans doublon. Il ne modifie ni ne supprime jamais rien.

Pour charger une nouvelle version de PARHAF, créer un nouveau lot (identifiant distinct) plutôt que de modifier celui-ci.

### 1.3 Vérifier

```
uv run python -I scripts/tests/verifier_parhaf.py
```

Lecture seule. Contrôle les effectifs (documents et codages `scenario` égaux au nombre de dossiers préparés, aucun doublon, aucun document sans codage), les empreintes (égales au SHA-256 du texte en base et aux textes préparés), l'absence des caractères normalisés et des blocs retirés, les 5 dossiers signalés à corriger, et la conformité des codages `scenario`. Le script se termine en erreur si un contrôle échoue.

### 1.4 Résultat du chargement du 18 octobre 2026

- Lot `parhaf-1.0.0` ; 3 827 documents (5 752 documents d'origine concaténés) ; 3 827 codages `scenario`.
- Passages retirés : règle A 12, règle B 49, cas C 1. Dossiers signalés à corriger : HEMATOLOGIE-CLINIQUE-00049, -00072, -00105, MEDECINE-GERIATRIQUE-00038, -00192.
- 28 contrôles réussis sur 28 ; seconde exécution du chargement : 3 827 dossiers déjà présents, aucune insertion.
- 1 107 codes DP distincts à vérifier au lot B3 (`donnees/prepare/parhaf/codes_dp_a_verifier.csv`).

## 2. Les référentiels recode-icd (lot B3, partie index et formulations)

### 2.1 La livraison

La livraison recode-icd (`<commit>_<millésime kit>`, aujourd'hui `65701d6_atih-2025`, kit ATIH 2025) est rangée **hors du dépôt** dans `donnees/referentiels/recode-icd/<version>/` : l'archive, et sa décompression dans `extrait/` (`docs/referentiels/README.md`). Elle n'est jamais modifiée. On en charge pour l'instant : `codes.csv` (tous les codes du kit, 42 897, clé `code_atih` sans point et extension collée, déjà à la forme de `codeur`), `formulations.csv` (109 987 formulations, avec leur source ; **non redistribuables : base oui, dépôt jamais**) et `descendants_codables.csv` (19 974 couples nœud → descendant codable, pour la boucle de correction). Les fiches (`cards_library/`) attendront la revue par l'IA.

### 2.2 Charger

```
uv run python -I scripts/chargement/referentiels_charger.py --controler   # contrôles seuls, aucune écriture
uv run python -I scripts/chargement/referentiels_charger.py               # contrôles puis chargement (clé secrète)
```

Correspondance : `fiches` ← `codes.csv` (code, libellé, codable, `statut_mco`, `interdit_dp/dr/das`, `version_livraison` ; `contenu` vide pour l'instant) ; `synonymes` ← `formulations.csv` (`origine` = `index` pour la source « CIM-10 index », `synonyme` pour les autres ; `source` conservée) **plus une ligne par code avec son libellé officiel** (`origine` = `libelle`, `source` = « ATIH kit 2025 »), pour que la recherche par mots trouve aussi les libellés ; `descendants_codables` ← le fichier tel quel.

Contrôles avant chargement (le chargement est refusé si l'un échoue) : forme de tous les codes ; chaque formulation et chaque descendant renvoient à un code de l'index ; chaque descendant est codable ; confrontation des DP de PARHAF à l'index (ci-dessous).

**Le rechargement ne supprime jamais rien** : les lignes sont insérées ou mises à jour sur leurs clés (`fiches.code` ; `synonymes` code + formulation + source ; `descendants_codables` nœud + code). **Changer de livraison** (nouveau commit recode-icd ou nouveau millésime) est une opération à part, à préparer avec l'accord du responsable : elle peut retirer des codes, des formulations ou des descendants, ce que ce script ne fait pas.

### 2.3 Vérifier

```
uv run python -I scripts/tests/verifier_referentiels.py
```

Connecté comme testeur (compte de test créé puis supprimé) : recherche par code exact, descendants codables d'un code (`Z992` → `Z992+0`, `+1`, `+8`), code non codable (`C50`, père interdit, avec ses descendants), code inconnu, recherche par mots dans `formulation_normalisee` insensible aux accents et à la casse (`hypertension`, `HTA`, `hernie inguinale`), présence des libellés officiels, écriture refusée. 15 vérifications sur 15 le 22 octobre 2026.

### 2.4 Résultat du chargement du 22 octobre 2026

- `fiches` : 42 897 codes (40 419 codables, 2 478 non codables) ; `synonymes` : 152 884 lignes (109 987 formulations, 42 897 libellés) ; `descendants_codables` : 19 974.
- **DP de PARHAF** : 3 806 dossiers sur 3 827 ont un DP codable. **21 dossiers sont à traiter à part dans les analyses** : 20 dont le DP du scénario est un code « père interdit » (non codable tel quel) et 1 dont le DP est inconnu du kit (coquille probable du scénario). Leur codage initial n'est pas modifié et ils restent proposés aux testeurs. La liste nominative (identifiant et DP) est **hors dépôt**, dans `donnees/prepare/referentiels/parhaf_dp_a_traiter_a_part.csv` : elle révélerait le codage initial de ces dossiers, qui ne doit jamais figurer dans la documentation publique.
- 6 codes DP ont dans PARHAF un libellé légèrement différent du libellé officiel : sans conséquence, le libellé de l'index fait foi.

## 3. CRH synthétiques (lot B2)

Source : `donnees/synthetiques/run08_scenarios_reports_merged_20261007_160916.parquet` (100 000 lignes, 97 colonnes, hors git, jamais modifié ; inventaire dans `docs/exploration/inventaire_corpus.md` §2). Les fichiers intermédiaires vont dans `donnees/prepare/synthetiques/` (hors git). Fonctions partagées : `scripts/chargement/synthetiques_commun.py`.

### 3.1 Confrontation des codes du générateur à l'index (`synthetiques_codes.py`)

Lecture seule, sur les 100 000 lignes, contre `fiches` et `descendants_codables` (livraison `65701d6_atih-2025`). Produit `donnees/prepare/synthetiques/codes_confrontation.md`. Constaté le 22 octobre 2026 :

| | codable | affinable | père interdit | supprimé | inconnu du kit | total |
|---|---|---|---|---|---|---|
| DP | 97 755 | 2 245 | 0 | 0 | 0 | 100 000 |
| DAS | 212 383 | 9 073 | 0 | 0 | 1 599 | 223 055 |
| code Z de `case_management_type` (29 829 lignes, 70 171 à « DP ») | 29 577 | 252 | 0 | 0 | 0 | 29 829 |

- Aucun DP ni code Z non codable. Les 1 599 DAS inconnus se réduisent à trois formes (`M1427`, `M1467`, `M1426`) : un cinquième caractère de siège ajouté par le générateur à M14.2 et M14.6, que le kit n'a pas ; 1 421 scénarios touchés.
- Clés du JSON `formulations.diagnostics` : 318 264 clés avec code ; après rattachement aux codes du scénario (SCHEMA.md §3.8 : égalité, puis extension ignorée, puis préfixe) : 315 356 égales, 2 583 à l'extension près, 313 par préfixe, 12 non rattachées (codes ajoutés par le générateur, tous codables). 87 clés (78 lignes) n'ont pas de code reconnaissable en fin de clé (paires « (G30.9 + F00.9) », crochets, tiret, « (M14.-) », acte CCAM).
- JSON analysable avec les réparations simples : 97 897 lignes.

**Règle retenue (22 octobre 2026).** N'entrent dans le tirage que les lignes propres : JSON réparable, tous les codes du scénario (DP, DAS, code Z) codables dans le kit, toutes les clés du JSON avec un code reconnu et rattaché au scénario. Lignes écartées : 3 760 (JSON non réparable 2 103, code non codable ou inconnu 1 599, clé sans code reconnu 78, code ajouté par le générateur 12 ; une ligne peut cumuler) ; **lignes éligibles : 96 240** (86 346 scénarios distincts). Ainsi aucun code non codable n'entre dans un codage `scenario` (SCHEMA.md §3.10) et aucun code hors scénario n'est à inventer.

**Codes « affinables ».** Un code de la référence est dit affinable quand le kit le marque codable mais qu'il a des descendants codables plus précis dans `descendants_codables` (par exemple `K635` → `K635+0`, `F1724` → `F17240`, `Z992` → `Z992+0`). On ne change rien à la référence. Pour les analyses (lot B5), un code plus précis que la référence, descendant du code de référence dans `descendants_codables`, devra être compté à part, et non comme un désaccord. Le rapport de préparation indique le nombre de documents de l'échantillon qui ont au moins un code affinable.

### 3.2 Échantillon de 500 (`synthetiques_echantillon.py`)

Décidé le 22 octobre 2026. Lignes éligibles (§3.1), texte présent, **une variante par scénario** (pour chaque `id_scenario`, la ligne dont `variante` est la plus petite, à `generation_id` croissant en cas d'égalité) : 86 346 lignes. **Répartition mixte** entre les six gabarits (`template_name`) : 40 dossiers au minimum par gabarit, le reste (260) au prorata des effectifs éligibles ; arrondi ajusté sur le gabarit le plus nombreux. **Tirage** sans remise dans chaque gabarit, sur la liste triée des `generation_id`, avec `random.Random(20261022)` (graine = date de la décision). La liste des 500 `generation_id` est dans `donnees/prepare/synthetiques/echantillon_500.csv` (hors git) ; le script sans `--ecrire` affiche les trois répartitions étudiées (proportionnelle, égale, mixte) sans rien écrire.

| Gabarit | lignes éligibles (une variante par scénario) | poids | échantillon |
|---|---|---|---|
| medical_outpatient | 34 131 | 39,5 % | 143 |
| medical_inpatient | 26 784 | 31,0 % | 121 |
| surgery_outpatient | 11 345 | 13,1 % | 74 |
| surgery_inpatient | 9 315 | 10,8 % | 68 |
| medical_outpatient_onco | 4 038 | 4,7 % | 52 |
| medical_inpatient_onco | 733 | 0,8 % | 42 |
| total | 86 346 | 100 % | 500 |

**L'échantillon n'a pas les proportions du corpus** (les gabarits rares sont surreprésentés). Pour le lot B5 : les résultats par gabarit se lisent directement ; un résultat global doit être pondéré par le poids de chaque gabarit dans les lignes éligibles (colonne « poids » ci-dessus), et non calculé sur les 500 dossiers confondus.

Diversité de l'échantillon retenu : 12 règles de codage distinctes (`other` 214, T3 141, T1 42, S1-Chronic 37, D1 24, vide 14…), 40 spécialités (36 dossiers sans spécialité), DAS : 213 sans, 108 avec un, 69 avec deux, 110 avec trois ou plus ; 234 HC / 266 HP ; 146 dossiers avec un code Z de prise en charge ; 49 dossiers avec au moins un code affinable.

### 3.3 Nettoyage, codage initial et colonnes (`synthetiques_preparer.py`)

Lit `echantillon_500.csv`, écrit un JSON par document dans `donnees/prepare/synthetiques/documents/<generation_id>.json` (même forme que PARHAF : lot, id_source, version, specialite, type_prise_en_charge, texte, nettoyage, codage), puis `rapport.md`, `preuves_introuvables.csv` et `codes_ajoutes.csv`. Ne touche ni à la source ni à la base (l'index est seulement lu). Décisions du 22 octobre 2026 :

- **Règle D** : une ligne-titre « Dictionnaire(s) des formulations » (en gras ou en titre markdown, avec ou sans « : ») et tout ce qui la suit jusqu'à la fin, avec la ligne `---` collée au bloc et les lignes vides qui précèdent. Dans l'échantillon : 10 textes, où le bloc se réduit à la ligne-titre (le générateur a mis le contenu dans la clé `formulations`) ; aucun JSON ni clôture ``` recopiés. Les `---` de section des autres textes ne sont pas touchés.
- **Règle E** : un code CIM-10 entre parenthèses ou crochets dans le corps du texte (forme stricte : lettre, deux chiffres, point ou chiffres, extension « +n »), retiré seul avec l'espace qui le précède. Dans l'échantillon : 1 cas (« (F83) »). « (V617F) », mutation de JAK2, n'est pas un code et n'est pas touché.
- **Rubriques « Diagnostic »** : 68 titres `### Diagnostic` de comptes rendus opératoires, tous narratifs ; rien à retirer. Aucune rubrique en gras, aucune mention « CIM-10 » dans les 500.
- **Normalisation** identique à PARHAF (SCHEMA.md §2) ; dans l'échantillon, seuls des blancs de fin (16 textes). Les marques markdown (`###`, `**`, `-`, `---`) sont conservées et comptent dans les positions.
- **Contrôle final** : toute forme ressemblant à un code et toute mention « CIM-10 » restantes sont listées à chaque exécution, **sans liste d'exceptions** ; la liste est jugée à chaque fois. Le 22 octobre 2026 : 24 formes, toutes des faux positifs (jours de protocole J10 à J28, heures de vie H12 et H24, vitamine B12, parvovirus B19, vertèbres T10 et T11).
- Tout retrait est tracé dans `nettoyage.retraits` (règle, positions dans le texte d'origine, passage retiré) ; `nettoyage.documents_origine` compte un seul document (`chemin` = `report[generation_id=…]`) ; `anomalies` vide.

**Codage `scenario`** (SCHEMA.md §3.4 et §3.8) : DP en `pathologie_principale`, chaque DAS en `diagnostic_associe`, avec le **libellé officiel de l'index** ; `mode_prise_en_charge` = `case_management_type` (« DP » ou code Z, forme codeur) ; `regle_hierarchisation` = `coding_rule`, **`null` quand elle vaut `other` ou est vide**, valeur brute sinon ; `commentaires` vides ; pas de `passages_non_codes`. Les citations du JSON `formulations.diagnostics` sont rattachées aux codes du scénario (§3.8) et deviennent les preuves du code, qui garde sa forme complète. La clé `informations` du JSON (nom, âge, NFS…) n'est pas utilisée.

**Preuves** : recherche dans le texte nettoyé et normalisé, positions en points de code (`debut` inclus, `fin` exclu), **toutes les occurrences**, chacune **bornée par des non-lettres** (mot entier : « HTA » n'est pas trouvé dans « HTAP »), sans chevauchement. Quatre niveaux de tolérance, essayés dans l'ordre à chaque occurrence : identique ; casse et espaces près ; accents près ; marques de gras markdown (`*`, `_`) ignorées. **Quel que soit le niveau, la preuve enregistre le texte tel qu'il est dans le document entre les positions trouvées** (étoiles intérieures comprises). Une citation introuvable (paraphrase du générateur, citation avec « [...] ») est gardée avec `introuvable: true`, son texte, et sans positions. Chiffres de l'échantillon (3 616 citations distinctes ; 3 doublons dans une même clé écartés) :

| niveau | citations | part |
|---|---|---|
| identique | 2 987 | 82,6 % |
| casse et espaces | 411 | 11,4 % |
| gras markdown | 23 | 0,6 % |
| accents | 0 | 0 % |
| introuvable | 195 | 5,4 % |

Occurrences : 2 496 citations une fois, 544 deux fois, 279 trois fois, 102 quatre fois ou plus ; 4 875 preuves positionnées au total. Codes sans aucune citation retrouvée : aucun DP, 3 DAS (plus 3 DAS sans citation dans le JSON) ; **laissés tels quels** (décision du 22 octobre 2026). Codes ajoutés par le générateur : aucun possible, par construction de la règle d'éligibilité (`codes_ajoutes.csv` reste vide). Aucune clé du JSON ne se rattache à un code Z dans l'échantillon. Contrôle automatique avant écriture : pour chaque preuve positionnée, `texte[debut:fin]` est égal au texte enregistré ; une seule pathologie principale ; tous les codes codables.

**Règles de hiérarchisation** : 12 valeurs dans l'échantillon (`other` 214, T3 141, T1 42, S1-Chronic 37, D1 24, vide 14, D9 9, D5 9, T2-R52 4, D3-1 4, T5 1, T11 1). **La confrontation au guide des situations cliniques reste à faire** quand il sera livré (`docs/referentiels/situations_cliniques/`, table `regles_situations` vide au 22 octobre 2026) ; `other` sera à interpréter à ce moment-là.

**Colonnes de recherche** (décision du 22 octobre 2026) : `specialite` ← `specialty` (identique à `department` sur les 464 documents qui en ont une ; `null` pour les 36 sans spécialité, `specialite_source` = « repli », sans colonne de secours) ; `type_prise_en_charge` ← « `DPEC`, mode en clair » (`mode_hospit` HC → « en hospitalisation complète », HP → « en hospitalisation partielle »), valeurs brutes, 8 valeurs : « Médecine adultes < 3 nuits, en hospitalisation complète » 119, « HDJ médecine adultes, en hospitalisation partielle » 98, « Chirurgie adultes < 3 nuits » HP 73 / HC 68, « Interventionnel adultes < 3 nuits » HP 59 / HC 40, « Séances simples » HP 36 / HC 7 (les 7 séances en hospitalisation complète sont une bizarrerie du générateur, gardée telle quelle).

### 3.4 Chargement (`synthetiques_charger.py`) et vérification (`scripts/tests/verifier_synthetiques.py`)

Même mécanique que PARHAF (§1) : `--blanc` prépare tout et affiche le bilan sans rien écrire ; sinon une ligne `lots` (`synthetiques-run08-e500`, source, version `run08-20261007`, description, `contenu` et `regles_nettoyage`), les documents en version 1 par paquets de 100 (empreinte vérifiée au retour), un codage `scenario` par document (utilisateur vide, compteurs vides). Rechargeable sans doublon : un document déjà présent est passé après contrôle de son empreinte, un document sans codage reçoit son codage ; **jamais de suppression ni de modification**. `contenu.echantillon` porte la graine, la règle de la variante, la répartition, les lignes tirées (500), les lignes éligibles (86 346) et, par gabarit, le couple éligibles / tirées, pour pondérer un résultat global depuis la base (§3.2).

Chargé le 22 octobre 2026 : 500 documents, 500 codages, 1 623 ensembles, 4 875 preuves positionnées, 195 introuvables, 11 retraits. Second passage le même jour : 500 « déjà là », aucune écriture. `verifier_synthetiques.py` : 35 contrôles sur 35 (lot, documents identiques aux fichiers préparés, empreintes, caractères interdits, blocs et codes absents, colonnes de recherche, codages conformes et preuves relisibles, vue des testeurs). `verifier_schema.py` et `tester_acces.py` (59 essais sur 59, dont, sur le lot synthétique vu par un testeur : texte lisible, `nettoyage` refusé, codage `scenario` invisible, 500 dossiers dans `dossiers_disponibles`, 36 spécialités à `null`) passés le même jour.

**Point relevé** : la page construit ses listes de filtre (spécialité, type de prise en charge) par une seule requête limitée à 10 000 lignes, mais PostgREST en renvoie au plus 1 000 ; avec 4 322 dossiers, les valeurs propres aux synthétiques peuvent manquer dans les listes (à traiter avec le filtre par source, lot A6 ou suivant).
