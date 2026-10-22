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

## 3. CRH synthétiques

À venir (lot B2).
