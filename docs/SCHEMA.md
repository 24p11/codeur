# Schéma de la base de données

*Version 1.1 — 18 octobre 2026 (précisions de mise en œuvre de la base, §10).*

*Version 1.0 — 18 octobre 2026. Établi lors de la séance sur le schéma, à partir de la note `docs/exploration/inventaire_corpus.md`. Ce document fait foi pour la structure de la base ; `CADRAGE.md` décrit le projet dans son ensemble.*

Ce document décrit comment les informations sont rangées dans la base Supabase (PostgreSQL) : quelles tables, quelles colonnes, quel contenu dans les champs JSON, et qui a le droit de lire ou d'écrire quoi. Il est écrit pour être relu par un médecin DIM autant que par un développeur.

---

## 1. Les principes

1. **Trois tables principales**, qui suivent le chemin d'un dossier :
   - **les documents** : ce que l'on code ;
   - **les codages** : toutes les versions successives du travail de codage ;
   - **les RUM** : le produit final, construit à partir d'un codage validé.
2. **On n'écrase jamais rien.** Chaque modification ajoute une nouvelle ligne. Corriger un texte crée une nouvelle version du document ; chaque étape du codage crée une nouvelle ligne de codage ; reconstruire un RUM crée une nouvelle ligne de RUM. L'historique complet est donc toujours disponible.
3. **Le texte d'un document est figé.** Les éléments de preuve sont repérés par leur position dans le texte : si le texte changeait, toutes les positions deviendraient fausses.
4. **Peu de colonnes, des champs JSON pour le reste.** Les sources futures n'auront pas toutes le niveau de détail de PARHAF. Les colonnes sont réservées à ce qu'on recherche ou filtre souvent ; le reste est rangé dans des champs JSON, indexés et interrogeables.
5. **Le testeur ne voit que ce qu'un codeur voit en réalité** : le texte du compte rendu. Le codage initial (celui du scénario), les évaluations de qualité faites par le LLM et les réponses brutes du LLM restent dans la base, inaccessibles aux testeurs.
6. **Les codes CIM-10 sont toujours écrits sans point**, avec l'éventuelle extension PMSI collée au code, comme dans le RUM : `K409`, `I5009`, `K635+0`, `E11ni`.

---

## 2. La table des documents

Une ligne correspond à **une version d'un texte à coder**. Pour PARHAF, un document réunit tous les documents d'un même patient (consultation, compte rendu opératoire, CRH…), mis bout à bout. Pour les CRH synthétiques, un document correspond à une ligne de la source.

| Colonne | Contenu | Exemple |
|---|---|---|
| `id` | Identifiant interne, attribué par la base | 1254 |
| `lot` | Le lot d'origine (renvoie à la table `lots`) | `parhaf-1.0.0` |
| `id_source` | L'identifiant du document dans sa source : il permet de retrouver l'original | `CARDIOLOGIE-00133` |
| `version` | Numéro de version du texte | 1, puis 2 après une correction |
| `version_precedente` | La ligne dont cette version est issue | vide pour la version 1 |
| `motif_version` | La raison de la correction | « codes recopiés dans le corps du texte » |
| `specialite` | Pour rechercher les dossiers | `Cardiologie` |
| `type_prise_en_charge` | Pour rechercher les dossiers ; valeur brute de la source | `Prise en charge médicale, en hospitalisation complète` |
| `texte` | Le texte de référence, nettoyé et figé | |
| `empreinte` | Une « signature » calculée à partir du texte (SHA-256), qui permet de vérifier qu'il n'a jamais changé | |
| `nettoyage` | JSON : les passages retirés au chargement, avec la règle appliquée et leur position dans le texte d'origine ; les anomalies signalées. Jamais affiché | |
| `cree_le`, `cree_par` | Date et auteur de cette version (le script de chargement pour la version 1) | |

**Règles :**

- Un même couple `lot` + `id_source` + `version` ne peut exister qu'une fois. Charger deux fois le même document est donc impossible.
- Le texte d'une ligne n'est jamais modifié. Corriger un texte (lot A6, page d'édition) ajoute une nouvelle ligne, avec `version` augmentée de 1 et `version_precedente` renseignée. Les nouveaux codages se font sur la version la plus récente.
- **Intitulés.** Quand un document réunit plusieurs documents d'origine, chacun est précédé, dans le texte lui-même, d'un intitulé court et normalisé, sur sa propre ligne : `— Consultation —`, `— Compte rendu opératoire —`, `— Compte rendu d'hospitalisation —`, `— Urgences —`, `— Accouchement —`, `— Maternité —`. Ces intitulés font partie du texte de référence : le texte enregistré est exactement le texte affiché, ce qui garantit que les positions sont les mêmes à l'écran et dans la base. Un document qui ne réunit qu'un seul document d'origine n'a pas d'intitulé.
- **Ordre.** Pour PARHAF, les documents d'origine sont mis bout à bout dans l'ordre du fichier, qui est l'ordre chronologique.
- **Markdown.** Les marques de mise en forme des CRH synthétiques (`###`, `**`) sont conservées dans le texte. Elles comptent dans les positions. L'affichage pourra les rendre en mise en forme, à condition que le surlignage reste correctement placé (point à traiter avec la mise en forme de l'affichage).
- **Normalisation au chargement**, avant de figer le texte : forme Unicode NFC (accents composés) ; suppression des caractères de largeur nulle (U+200B), du BOM (U+FEFF) et du trait d'union conditionnel (U+00AD) ; remplacement des espaces insécables (U+00A0, U+202F) par une espace simple.

**Ce qui n'est pas dans la base :** le scénario de génération, les variantes d'un même scénario, le nom de l'auteur ou du relecteur, le résumé structuré de PARHAF. Toute la traçabilité de la génération reste dans la base source (aujourd'hui sur Google Drive, demain sur Hugging Face), à laquelle `lot` + `id_source` permettent de revenir.

---

## 3. La table des codages

### 3.1 Le principe : un codage complet à chaque étape

Une ligne correspond à **l'état complet du codage d'un document, à l'issue d'une étape**. Chaque étape ajoute une ligne. On ne suit pas chaque code individuellement : on enregistre le codage entier, et ce qui est arrivé à chaque code se retrouve en **comparant deux lignes successives**.

### 3.2 Les étapes

| Étape | Qui produit le codage | Quand |
|---|---|---|
| `scenario` | Le script de chargement | Le codage initial, tiré de la source (jamais visible des testeurs) |
| `humain` | L'humain seul, sans IA | Campagne d'annotation (cahier des charges n° 1) |
| `ia` | L'IA seule, sur tout le texte | Pré-codification |
| `ia_humain` | L'IA, sur les passages surlignés par l'humain | Clic sur « Faire le codage » |
| `revue_humain` | L'humain | Après qu'il a accepté, corrigé, retiré ou ajouté des codes |
| `revue_ia` | L'IA | Avis de l'IA sur le codage de l'humain : le codage qu'elle recommande, avec ses commentaires |
| `revue_humain_ia` | L'humain | Le codage final, après sa réponse aux recommandations de l'IA |

**Parcours principal du prototype :**

`ia_humain` → `revue_humain` → (`ia_humain` → `revue_humain`)… → `revue_ia` → `revue_humain_ia`

**Parcours de pré-codification :** `ia` → `revue_humain` → `revue_ia` → `revue_humain_ia`.

### 3.3 Les colonnes

| Colonne | Contenu |
|---|---|
| `id` | Identifiant de la ligne |
| `document` | La **version précise** du document codée |
| `etape` | Une des valeurs du §3.2 |
| `utilisateur` | Qui a produit la ligne. Pour une étape de l'IA, le testeur qui a déclenché l'appel. Vide pour l'étape `scenario` |
| `cree_le` | Date et heure |
| `codage_precedent` | La ligne dont celle-ci est la suite ; permet de suivre le fil d'un même travail. Vide pour la première ligne d'un travail |
| `appel_llm` | Pour une étape de l'IA, l'appel enregistré dans la table `appels_llm` |
| `valide` | Vrai pour la ligne que l'utilisateur a validée comme codage final de son travail |
| `compteurs` | JSON : l'écart avec la ligne précédente (§3.6), calculé à l'enregistrement |
| `codage` | JSON : le contenu du codage (§3.4) |

Les lignes de cette table ne sont **jamais modifiées ni supprimées** ; seules des lignes nouvelles peuvent être ajoutées.

### 3.4 Le contenu du JSON

```json
{
  "regle_hierarchisation": "T3",
  "mode_prise_en_charge": "DP",
  "commentaires": [
    { "auteur": "humain", "etape": "revue_humain", "texte": "Séjour ambulatoire programmé." }
  ],
  "ensembles": [
    {
      "code": "K409",
      "libelle": "Hernie inguinale unilatérale ou SAI, sans occlusion ni gangrène",
      "categorie": "pathologie_principale",
      "preuves": [
        { "debut": 1532, "fin": 1560, "texte": "hernie inguinale droite" }
      ],
      "confiance": null,
      "explication": null,
      "commentaires": [
        { "auteur": "ia", "etape": "revue_ia", "texte": "Le côté ne change pas le code ; K409 est adapté." }
      ]
    },
    {
      "code": "I10",
      "libelle": "Hypertension essentielle (primitive)",
      "categorie": "diagnostic_associe",
      "preuves": [ { "debut": 210, "fin": 225, "texte": "HTA traitée" } ],
      "confiance": null,
      "explication": null,
      "commentaires": []
    }
  ]
}
```

| Champ | Contenu |
|---|---|
| `regle_hierarchisation` | Le code de la règle du guide des situations cliniques (`D1`, `T3`, `S1-Chronic`…), ou vide |
| `mode_prise_en_charge` | Le code Z de prise en charge, ou `DP` quand le diagnostic principal motive lui-même le séjour, ou vide |
| `commentaires` | Commentaires sur l'ensemble du codage |
| `ensembles` | La liste des codes, chacun avec ses éléments de preuve |
| `code` | Sans point, extension PMSI collée |
| `libelle` | Le libellé officiel, au moment du codage |
| `categorie` | `pathologie_principale` (une seule par codage) ou `diagnostic_associe` |
| `preuves` | Les éléments de preuve : position de début et de fin dans le texte, et texte cité. Un champ facultatif `introuvable: true` signale une citation qui n'a pas pu être retrouvée dans le texte |
| `confiance`, `explication` | Remplis par l'IA quand elle propose un code ; vides sinon |
| `commentaires` | Commentaires sur ce code |

**Les commentaires** portent toujours leur auteur (`ia`, `humain`, ou `generateur` pour les remarques issues du chargement des CRH synthétiques) et l'étape où ils ont été écrits. Ils passent d'une version à la suivante, sauf si le code auquel ils sont attachés est retiré.

Le même format sert pour **toutes les étapes**, ce qui rend toutes les versions comparables entre elles.

### 3.5 Les appels répétés à l'IA

L'utilisateur peut surligner de nouveaux passages après une première revue et cliquer de nouveau sur « Faire le codage ». Pour **garantir** que ses choix sont conservés, la garantie repose sur l'outil et non sur le modèle :

1. l'outil n'envoie au modèle **que les passages surlignés qui ne sont rattachés à aucun code** ;
2. les codes déjà retenus sont transmis **en lecture seule**, comme contexte (par exemple pour que le modèle sache qu'une pathologie principale est déjà choisie) ;
3. **c'est l'outil qui assemble** le nouveau codage : codes déjà retenus inchangés, plus les nouvelles propositions ;
4. l'outil écarte toute proposition qui ne porte pas sur un des nouveaux passages, et tout code invalide.

Un passage surligné qui chevauche un ensemble déjà codé complète les preuves de cet ensemble : il n'est pas envoyé au modèle.

Chaque appel crée une nouvelle ligne `ia_humain` contenant le codage assemblé.

### 3.6 Comparer deux versions : les compteurs

Pour savoir ce qui est arrivé à chaque code entre deux lignes successives, on **apparie les ensembles par leurs éléments de preuve** : deux ensembles dont les preuves se chevauchent dans le texte portent sur la même chose.

| Situation | Interprétation |
|---|---|
| Ensemble présent dans les deux lignes, même code et même catégorie | Conservé |
| Ensemble présent dans les deux lignes, code ou catégorie différent | Modifié |
| Ensemble présent dans les deux lignes, preuves différentes | Preuves modifiées |
| Ensemble présent seulement dans la ligne précédente | Retiré (rejeté) |
| Ensemble présent seulement dans la nouvelle ligne | Ajouté |
| Plusieurs appariements possibles, ou ensembles sans preuves | Appariement incertain |

Les compteurs sont enregistrés dans la ligne :

```json
{ "conserves": 3, "modifies": 1, "preuves_modifiees": 0, "retires": 1, "ajoutes": 2, "incertains": 0,
  "regle_modifiee": false, "mode_prise_en_charge_modifie": false }
```

### 3.7 Le codage initial (étape `scenario`)

- **PARHAF** : un seul ensemble, le diagnostic principal du scénario, en `pathologie_principale`, sans preuves. Règle et mode de prise en charge vides.
- **CRH synthétiques** : les codes sont tirés des **colonnes du scénario**, avec leur extension PMSI : DP (`pathologie_principale`), DAS (`diagnostic_associe`), mode de prise en charge (`case_management_type` : `DP` ou code Z), règle (`coding_rule`, laissée vide quand elle vaut `other`). **Le scénario fait référence pour les codes ; le JSON `formulations.diagnostics` ne fournit que les preuves.**
  - **Rattachement d'une clé du JSON à un code du scénario** (opération interne au chargement, qui ne sert qu'à retrouver les preuves) : d'abord en ignorant l'extension PMSI (`Z992` ↔ `Z992+0`), sinon au code du scénario qui commence par la clé (`M142` ↔ `M1427`). Les citations de la clé deviennent les preuves du code du scénario, **qui garde sa forme complète**. Les positions sont calculées au chargement, et les citations introuvables sont marquées `introuvable`.
  - **Codes ajoutés par le générateur** (clés qui ne se rattachent à aucun code du scénario : `G20` à côté de `F023`, `G301` à côté de `F001`, `G992`, un `I10`) : **conservés dans le codage initial**, en `diagnostic_associe`, avec leurs citations, car ils enrichissent le codage. Chacun porte un commentaire d'auteur `generateur` (« Code ajouté par le générateur, absent du scénario »), pour rester repérable. Deux conditions : le code doit être **codable** (§3.9), et il ne doit pas être une simple reformulation d'un code du scénario (cas des 2 `M148` écrits pour `M1427` : leurs citations deviennent des preuves de `M1427`).
  - L'analyse (script `14_codes_hors_scenario_synthetiques.py`) a montré que les 2 460 codes du JSON absents du scénario sont à 99,5 % des codes du scénario privés de leur extension (2 202) ou arrondis à un niveau moins fin (247).

### 3.8 Les deux niveaux de comparaison des codes

| Niveau | Usage |
|---|---|
| **Code complet**, extension PMSI comprise (`Z992+0`) | Le seul niveau qui fait foi : compteurs, contrôles, construction du RUM |
| **Catégorie à trois caractères** (`Z99`) | Statistiques uniquement, jamais pour les contrôles |

Un code privé de son extension (`Z992` au lieu de `Z992+0`) n'est **pas** une variante acceptable : ce n'est pas un code codable, et il mettrait le RUM en erreur. Il n'y a donc pas de niveau de comparaison « sans extension ».

**Les fiches d'identité** sont recherchées par le **code complet**. Les fiches de catégorie de recode-icd ne sont pas utilisées : l'objectif est de coder au niveau du code, pas de la catégorie.

### 3.9 N'accepter que des codes codables

L'analyse des CRH synthétiques montre que les LLM connaissent mal la CIM-10 PMSI : ils omettent les extensions et arrondissent à un niveau moins précis. L'outil doit donc garantir que **seuls des codes codables** entrent dans un codage, quelle que soit leur origine. Cette garantie repose sur l'outil, pas sur le modèle :

1. **Vérification systématique** : tout code proposé par le LLM est comparé à la liste des codes codables. Cette liste est tirée de **l'index de la livraison recode-icd** (contrat d'interface : « la liste des codes, c'est l'index »), et non de la présence d'une fiche : une fiche peut être vide ou absente quand elle n'apporte rien, sans que le code cesse d'être codable. Un code non codable n'est jamais enregistré comme tel.
2. **Boucle de correction par le modèle** : si la réponse contient des codes non codables, l'outil renvoie au modèle un message qui les signale et lui fournit, pour chacun, **les codes codables qui en descendent** (pour `Z992` : `Z992+0`, `Z992+1`…) ou, à défaut, **les codes codables de sa catégorie**, avec leurs libellés. Le modèle choisit parmi eux, en s'appuyant sur le texte. La réponse est de nouveau vérifiée. La boucle s'arrête dès que tous les codes sont codables, et au plus après **2 tours de correction**. Chaque tour est un appel enregistré dans `appels_llm`, relié au même travail.
3. **Dernier recours** : si un code reste non codable après la boucle, l'outil présente à l'utilisateur la liste des codes codables possibles, et c'est lui qui choisit.
4. **Côté prompt** (à mettre au point au lot B4) : fournir au modèle, pour chaque passage surligné, une liste de **codes candidats** tirés de la table des synonymes, et lui rappeler explicitement l'existence des extensions PMSI, pour réduire le nombre de corrections nécessaires.
5. **Évolution possible** : donner au modèle de véritables outils qu'il appelle lui-même (rechercher des codes par mots-clés, lister les codes d'une catégorie, lire une fiche). Plus souple, mais plus complexe ; à envisager une fois la boucle simple éprouvée.

Chaque correction de ce type est enregistrée : la fréquence des codes non codables proposés est un indicateur de la qualité du modèle.

---

## 4. La table des RUM

Une ligne correspond à **un RUM construit à partir d'une ligne validée de la table des codages**.

| Colonne | Contenu |
|---|---|
| `id` | Identifiant |
| `document` | La version du document |
| `codage` | **La ligne de la table des codages** dont les diagnostics sont repris |
| `cree_le`, `cree_par` | Date et auteur |
| `version_format` | `023` (format ATIH « RSS non groupé ») |
| `rum` | JSON : les variables officielles du RUM, sous leur nom, y compris DP, DR et DA |
| `controles` | JSON : le résultat des contrôles qualité PMSI, avec la version des règles appliquées |
| `derogation`, `motif_derogation` | Vrai si l'utilisateur a passé outre une alerte bloquante ; le motif est alors obligatoire |

**Règles :**

- Le RUM **n'est jamais modifié directement**. Il est toujours construit à partir d'un codage validé. Si le codage est modifié après validation, un nouveau RUM est construit.
- **Construction des diagnostics** : la règle de hiérarchisation sert à traduire les quatre catégories du codage (règle, mode de prise en charge, pathologie principale, diagnostics associés) en DP, DR et DA.
- **Dans le prototype**, un **RUM partiel** est construit à chaque validation : les diagnostics sont remplis, les variables administratives restent vides tant que leur alimentation n'est pas mise en place. Les contrôles qui n'ont besoin que des diagnostics peuvent ainsi fonctionner.
- Le format JSON reprend les noms, les types et les listes de valeurs du format officiel (fichier `docs/referentiels/atih/formats_mco_2026.xlsx`), mais pas les positions fixes du fichier ATIH, qui ne serviront qu'à fabriquer le fichier attendu par la fonction groupage.
- Un dossier correspond à un seul RUM (simplification assumée du prototype ; un séjour réel peut en compter plusieurs).

**Deux sortes de contrôles, à ne pas confondre :**

| Sorte | Exemples | Où | Enregistré ? |
|---|---|---|---|
| Vérifications de saisie | Code inexistant, code non codable | Dans l'interface, au moment de la saisie ou de la proposition de l'IA | Non : un code invalide n'entre pas dans le codage |
| Contrôles qualité PMSI | Cohérence entre la règle et la pathologie principale, incompatibilité avec l'âge ou le sexe, contrôles plus complexes à venir | Sur le RUM | Oui, dans la colonne `controles` du RUM |

Le résultat du groupage, quand il sera mis en place, sera rangé dans la table des RUM.

---

## 5. Les tables de suivi

### 5.1 `profils`

Les informations saisies à l'inscription. Une ligne par compte. Colonnes : `id` (le compte Supabase), `nom`, `prenom`, `statut` (medecin_dim, tim, autre_medecin, interne, etudiant, autre), `etablissement`, `accord_le` (date de l'accord pour l'utilisation des annotations à des fins de recherche), `cree_le`.

### 5.2 `appels_llm`

Chaque appel au LLM, pour toutes les tâches.

| Colonne | Contenu |
|---|---|
| `id` | **UUID fourni par la page avant l'insertion** (valeur par défaut générée par la base pour les scripts), afin que la page puisse relier un codage à son appel sans avoir à relire l'appel |
| `cree_le`, `utilisateur`, `document` | `utilisateur` et `document` obligatoires |
| `tache` | `evaluation_document`, `caracteristiques_sejour`, `codage`, `revue` |
| `fournisseur`, `modele` | Par exemple `mistral`, `mistral-large-latest` ; la version exacte si le service l'indique |
| `version_prompt` | Le nom et la version du fichier de prompt utilisé |
| `requete` | JSON : ce qui a été envoyé (sans la clé) |
| `reponse` | La réponse brute complète |
| `tokens_entree`, `tokens_sortie`, `tokens_total` | Tels qu'indiqués par le service |
| `duree_ms` | Durée de l'appel |
| `erreur` | Le message d'erreur éventuel |

### 5.3 `evaluations`

Une seule table pour les deux évaluations de la qualité d'un document : celle du LLM à l'ouverture du dossier, celle du testeur à la fin.

| Colonne | Contenu |
|---|---|
| `id`, `cree_le`, `utilisateur`, `document` | |
| `auteur` | `ia` ou `humain` |
| `appel_llm` | Pour une évaluation de l'IA |
| `mesures` | JSON : les mesures fixes calculées sur le texte (évaluation de l'IA uniquement) |
| `notes` | JSON : une note de 1 à 5 pour chacune des cinq dimensions (organisation, langage, cohérence médicale, synthèse, qualité générale) |
| `verdict` | Pour l'IA : `exploitable`, `douteux`, `non_exploitable` |
| `commentaire` | La raison du verdict (IA) ou le commentaire libre (testeur) |
| `poursuite` | Pour l'IA : le testeur a-t-il choisi de coder le document après l'avertissement ? |

---

## 6. Les tables de référence

| Table | Contenu |
|---|---|
| `lots` | Chaque lot chargé : `id` (`parhaf-1.0.0`…), source, version, `description` (texte libre), `contenu` (JSON : ce que le lot apporte — texte seul, DP, DAS, règle, preuves…), `regles_nettoyage` (JSON : les règles appliquées), `charge_le` |
| `fiches` | L'index des codes de recode-icd et leurs fiches : code (complet, sans point), libellé, **codable ou non**, contenu de la fiche (vide si elle n'apporte rien), version de la livraison (`version_livraison`), date de chargement (`charge_le`). La liste des codes codables est tirée de cette table. Le format exact dépend du chantier ouvert dans recode-icd pour les besoins de `codeur` |
| `synonymes` | Les formulations associées à chaque code : `origine` (type : libelle, inclusion, index, synonyme), **`source` (provenance : CépiDc, AP-HP, LLM…)**, le code (qui doit exister dans `fiches`), et une forme normalisée indexée pour une recherche insensible aux accents et tolérante aux fautes de frappe |
| `regles_situations` | Le guide des situations cliniques, une ligne par règle : code, famille (tirée de la colonne « Type d'hospitalisation » du guide), libellé, type, spécificité, pathologie, code Z, détails (JSON), version |

---

## 7. Les règles d'accès

Ces règles sont appliquées **par la base elle-même**, et non seulement par l'affichage : le code de la page étant public, un testeur ne doit pas pouvoir obtenir par un autre moyen ce que l'interface ne lui montre pas.

| Table | Un testeur connecté peut… |
|---|---|
| `documents`, `lots`, `fiches`, `synonymes`, `regles_situations` | lire ; ajouter une nouvelle version de document (page d'édition) |
| `codages` | lire et ajouter **ses propres lignes**, sauf l'étape `scenario`, qu'il ne peut ni lire ni écrire. Aucune ligne ne peut être modifiée ni supprimée |
| `rum` | lire et ajouter ses propres lignes |
| `appels_llm` | ajouter ses propres lignes, sans pouvoir les relire |
| `evaluations` | ajouter ses propres lignes ; relire uniquement celles dont il est l'auteur humain, jamais celles de l'IA |
| `profils` | créer (à l'inscription), lire et modifier son propre profil |

Le chargement des données de référence et du codage initial se fait par les scripts Python, avec la clé secrète, sur l'ordinateur du responsable du projet.

Pas de gestion des rôles dans le prototype : tous les testeurs ont les mêmes droits.

---

## 8. Les index

- Index de recherche sur les champs JSON `codage` (codages) et `rum` (RUM), pour pouvoir les interroger (par exemple : tous les codages dont la pathologie principale est dans le chapitre II).
- Index sur `documents (lot, id_source, version)` (unicité), `documents (specialite)`, `documents (type_prise_en_charge)`.
- Index sur `codages (document, utilisateur, etape)`.
- Index de recherche textuelle sur `synonymes`, insensible aux accents et tolérant aux fautes de frappe.

---

## 9. Questions restant ouvertes

*Réglées le 18 octobre 2026 :*

1. **Identifiant des CRH synthétiques** : `generation_id`. Toutes les données sur la génération restent gérées dans le projet de génération.
2. **Codes du JSON absents du scénario** : voir §3.7.
3. **Espaces insécables** (U+00A0, U+202F) : remplacés par une espace simple au chargement.
4. **Correspondance détaillée entre le scénario et le RUM** : reportée à l'alimentation du RUM.
5. **Les 5 CRH de PARHAF contenant des codes dans leur corps** : chargés dans leur version d'origine (version 1), signalés « à corriger » dans le champ `nettoyage` (`"a_corriger": true`, avec le motif), et non proposés aux testeurs tant qu'ils n'ont pas de version corrigée. Rémi les corrige avec la page d'édition (lot A6), ce qui crée les versions 2 et éprouve le mécanisme des versions en conditions réelles.

---

## 10. Précisions de mise en œuvre

Interprétations retenues lors de la création de la base (migrations de `supabase/migrations/`, 18 octobre 2026). Elles complètent les sections précédentes et font foi au même titre.

1. **Identifiants** : entiers attribués par la base pour les tables de travail, sauf `appels_llm.id` (UUID fourni par la page). Pour `lots`, `fiches` et `regles_situations`, la clé est un texte (`parhaf-1.0.0`, `K409`, `T3`).
2. **Auteurs** : `documents.cree_par`, `rum.cree_par`, `codages.utilisateur`, `appels_llm.utilisateur` et `evaluations.utilisateur` font référence au compte Supabase. Ils sont vides quand la ligne est écrite par un script, sauf pour les appels et les évaluations, où l'utilisateur est obligatoire.
3. **Empreinte** : `documents.empreinte` est calculée automatiquement par la base (SHA-256 hexadécimal) ; elle ne peut être ni oubliée ni falsifiée.
4. **Texte figé, garanti par la base** : un déclencheur refuse toute modification de `documents.texte`, quel que soit le rôle, y compris avec la clé secrète.
5. **Versions de documents** : `version = 1` si et seulement si `version_precedente` est vide.
6. **Codage initial** : `codages.utilisateur` est vide si et seulement si l'étape est `scenario`.
7. **Dérogation** : `rum.derogation` (booléen) et `rum.motif_derogation` (obligatoire si la dérogation est vraie).
8. **Appels au LLM** : `appels_llm.document` est obligatoire.
9. **Fiches** : la table contient tout l'index de recode-icd (codes non codables et codes sans fiche compris), une seule livraison à la fois ; clé = code ; `codable` booléen obligatoire ; `contenu` texte, vide pour un code sans fiche ; `version_livraison` en colonne.
10. **Synonymes** : `origine` ∈ {libelle, inclusion, index, synonyme} ; `source` obligatoire ; `code` doit exister dans `fiches` ; colonne calculée `formulation_normalisee`, indexée par trigrammes.
11. **Guide des situations cliniques** : `famille` est un texte libre issu de la colonne « Type d'hospitalisation » du guide, sans liste de valeurs imposée.
12. **Statuts des profils** : medecin_dim, tim, autre_medecin, interne, etudiant, autre.
13. **Visiteurs non connectés** : aucun droit sur aucune table.
14. **Nouvelle version de document par un testeur** : autorisée seulement pour une version supérieure à 1, signée de son compte ; la version 1 est réservée aux scripts de chargement.
15. **Index JSON** : index GIN général sur `codages.codage` et `rum.rum` ; les requêtes par chapitre demanderont un index dédié le moment venu. Index supplémentaires sur les liens entre tables.
16. **Aucun droit par défaut** (migration `20261018100500_droits_residuels.sql`) : les droits `TRUNCATE`, `TRIGGER` et `REFERENCES` accordés par défaut par Supabase sont retirés, et plus aucun droit n'est accordé automatiquement aux tables futures. **Toute nouvelle table doit définir explicitement, dans sa propre migration, ses droits, l'activation de la sécurité par ligne, ses règles par ligne et ses commentaires.**
17. **Ne jamais créer de table depuis l'interface web de Supabase.** Le rôle interne `supabase_admin` conserve des droits par défaut vers les visiteurs et les testeurs : une table créée à la main hériterait de droits non prévus. Toute évolution du schéma passe par une migration du dépôt.

*Base créée le 18 octobre 2026 : projet `codeur`, région Irlande (Union européenne), PostgreSQL 17 ; sept migrations appliquées (la septième ne fait que mettre à jour le commentaire de `rum.rum` après le déplacement du fichier ATIH) ; vérification du schéma conforme ; tests d'accès : 32 essais réussis sur 32 (commit `3918a2c`).*
