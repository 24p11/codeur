# Prototype d'aide au codage CIM-10 par l'IA — Fiche de cadrage

*Version 0.4 — octobre 2026 — dépôt GitHub : `codeur`*

Ce document décrit le petit outil de test de l'aide au codage. Il sert de référence pour le développement avec Claude Code. Il dit **ce que fait l'outil**, **comment les données sont organisées** et **dans quel ordre on construit**.

**Ce qui change par rapport à la version 0.3** : table des synonymes pour la recherche de codes (§4.5) ; codage enregistré au format JSON, sur le modèle de celui des CRH générés (§4.2) ; séance de travail dédiée au schéma de la base au début du projet (§6) ; mesures fixes sans seuil (§2.5) ; une fiche par code, qui contient elle-même les codes voisins (§5) ; nom du dépôt : `codeur`.

**Apports de la version 0.3** : le document est évalué à l'ouverture de chaque dossier, par des mesures fixes et par le LLM, qui joue le rôle de garde-fou avant le codage (§2.5) ; plus aucun appel au LLM n'est fait en lot : tout passe par la page, comme dans un véritable outil de codage.

**Rappel des apports de la version 0.2** : caractéristiques du séjour (règle de hiérarchisation et code Z) ; second statut « revue » pour chaque code ; fiche d'inscription des testeurs ; codage d'origine des CRH, conservé pour l'analyse mais jamais affiché ; notation de la qualité du CRH en cinq dimensions ; connecteur LLM générique ; travail sur les prompts ; découpage en deux projets parallèles.

---

## 1. Pourquoi ce prototype

Les outils décrits dans les cahiers des charges n° 1 (outil d'annotation) et n° 2 (outil de codage assisté par l'IA) associent de nombreux partenaires. Leur développement prendra du temps.

Ce prototype permet, sans attendre :

- de **tester l'aide au codage par l'IA** : l'utilisateur surligne, le LLM propose des codes (aide 2 du cahier des charges n° 2) ;
- de **tester la revue du codage par le LLM**, à partir des fiches d'identité des codes ;
- de **partager l'outil** avec une centaine de testeurs ;
- de **recueillir des données** : comparaison des codages des testeurs avec le codage d'origine des CRH, qualité des propositions du LLM, qualité des CRH.

Il est construit pour **ne pas être jetable** : le format des données suit le cahier des charges n° 2 (§13), afin que les briques puissent être reprises.

---

## 2. Le déroulement d'un dossier

### 2.1 Les étapes

1. **Connexion.** Le testeur saisit son adresse électronique, reçoit un lien par courriel et clique dessus. Aucun mot de passe.
2. **Inscription (la première fois).** Il renseigne son nom, son prénom, son statut et son établissement. Il lit une courte mention d'information et donne son accord pour l'utilisation de ses annotations à des fins de recherche.
3. **Réglages (la première fois).** Il indique son accès au LLM : adresse du service, nom du modèle et clé. Mistral est proposé par défaut. Son navigateur mémorise ces réglages sur son ordinateur.
4. **Choix d'un CRH** dans la liste.
5. **Évaluation du document (automatique).** Dès l'ouverture, la page calcule des mesures simples sur le texte, puis demande au LLM d'évaluer le document. Si le LLM le juge douteux ou non exploitable, le testeur voit un avertissement et choisit de continuer ou non (§2.5).
6. **Caractéristiques du séjour.** Il choisit la règle de hiérarchisation dans la liste du guide des situations cliniques et, le cas échéant, le code Z. Il peut aussi demander une proposition au LLM, accompagnée d'une courte justification rédigée.
7. **Surlignage.** Il surligne des passages. Chaque passage forme un « ensemble » ; il peut ajouter un passage à un ensemble existant quand plusieurs passages décrivent la même affection.
8. **Propositions de codes.** Il clique sur « Proposer des codes ». Le LLM renvoie, ensemble par ensemble, quelques codes possibles, chacun avec une catégorie, un degré de confiance et une courte explication.
9. **Décisions.** Pour chaque ensemble, il accepte un code proposé, le corrige ou rejette les propositions. Pour corriger un code ou en ajouter un lui-même, il le recherche en tapant quelques mots : l'outil cherche dans les libellés et dans la table des synonymes (§4.5).
10. **Revue du codage.** Il clique sur « Vérifier le codage ». L'outil applique des contrôles fixes, puis demande au LLM une revue à partir des fiches d'identité des codes choisis et du guide des situations cliniques. Il affiche les alertes. Le testeur corrige ou maintient son choix en indiquant pourquoi.
11. **Qualité du CRH.** Il note le CRH de 1 à 5 sur cinq dimensions, et peut ajouter un commentaire.
12. **Fin du dossier.**

### 2.2 Ce que le testeur ne voit jamais

- **Le codage d'origine du CRH**, quand il existe. Il est conservé uniquement pour les analyses.
- **Les notes de qualité attribuées par le LLM et la raison de son verdict.** Elles sont enregistrées, mais pas affichées. Le testeur ne voit qu'un avertissement général lorsque le document est jugé douteux ou non exploitable (§2.5).

### 2.3 Les catégories d'information

Chaque dossier comprend les quatre catégories du modèle d'annotation des cahiers des charges :

| Catégorie | Comment elle est renseignée |
|---|---|
| Règle de hiérarchisation | Choisie dans la liste du guide des situations cliniques, sans surlignage |
| Mode de prise en charge (code Z) | Choisi parmi les codes du chapitre XXI, sans surlignage |
| Pathologie principale | Un ensemble surligné et son code ; une seule par dossier |
| Diagnostics associés | Des ensembles surlignés et leurs codes |

Le diagnostic relié n'est pas saisi : il se déduit de la règle de hiérarchisation.

### 2.4 Les deux statuts de chaque code

> **Remplacé par `docs/SCHEMA.md` (§3).** Lors de la séance sur le schéma, les statuts par code ont été abandonnés au profit d'un modèle par étapes : chaque étape (`ia_humain`, `revue_humain`, `revue_ia`, `revue_humain_ia`…) enregistre le codage complet, et ce qui est arrivé à chaque code se retrouve en comparant deux étapes successives. Le texte ci-dessous est conservé pour mémoire.

Chaque code porte **deux statuts indépendants**.

Le **statut d'origine** dit d'où vient le code :

| Statut d'origine | Signification |
|---|---|
| Humain seul | Code saisi par le testeur lui-même |
| IA validée | Code proposé par le LLM et retenu tel quel |
| IA corrigée | Code proposé par le LLM puis modifié (on garde la proposition initiale) |
| IA rejetée | Code proposé par le LLM et écarté (conservé pour l'analyse) |

Le **statut de revue** dit ce que la revue en a dit et ce que le testeur en a fait :

| Statut de revue | Signification |
|---|---|
| Non revu | La revue n'a pas encore été lancée |
| Validé par la revue | Aucune alerte sur ce code |
| Maintenu après alerte | Alerte émise, code gardé, motif indiqué |
| Modifié après revue | Code changé à la suite d'une alerte (on garde la version d'avant) |
| Supprimé après revue | Code retiré à la suite d'une alerte |

Les mêmes statuts s'appliquent à la règle de hiérarchisation et au code Z.

### 2.5 L'évaluation du document et la qualité du CRH

**Pourquoi évaluer le document avant de le coder.** Cette évaluation a deux rôles. C'est d'abord une mesure de la qualité du CRH. C'est surtout un **garde-fou** : avant que le LLM ne propose des codes, on vérifie que le document est bien un CRH exploitable, pour ne pas coder n'importe quoi.

**Les mesures fixes.** À l'ouverture du dossier, la page calcule des indicateurs objectifs sur le texte :

- la longueur : nombre de mots, de phrases, longueur moyenne des phrases ;
- la structure : présence des rubriques attendues d'un CRH (motif d'hospitalisation, antécédents, histoire de la maladie, examen clinique, évolution, conclusion, traitement de sortie) ;
- des signes d'anomalie : passages répétés à l'identique, caractères inhabituels, texte qui n'est pas en français.

Ces mesures reprennent les calculs simples déjà utilisés dans le projet de génération de CRH. **Aucun seuil n'est fixé dans ce projet** : les indicateurs sont enregistrés et transmis au LLM, qui s'en sert pour son évaluation, mais l'outil ne déclare pas lui-même un document « atypique ». Les seuils pourront être établis plus tard, à partir des données recueillies.

Ces mesures sont calculées **dans la page**, et non à l'avance. Elles donnent toujours le même résultat pour un même texte, mais les calculer dans la page rend l'outil autonome : il pourra plus tard évaluer un document qui n'a pas été préparé à l'avance, par exemple un texte collé par l'utilisateur.

**L'évaluation par le LLM.** Juste après, la page transmet au LLM le texte et les indicateurs, et lui demande :

- une note de 1 à 5 sur chacune des cinq dimensions ci-dessous ;
- un **verdict** : « exploitable pour le codage », « douteux » ou « non exploitable », avec une courte raison.

Elle est refaite à chaque dossier, avec l'accès LLM du testeur. Quand plusieurs testeurs ouvrent le même CRH, on obtient plusieurs évaluations du même document, ce qui permet aussi de mesurer la stabilité du jugement du LLM.

**Ce que voit le testeur.** Si le verdict est « douteux » ou « non exploitable », il voit un simple message : « Ce document semble atypique. Voulez-vous le coder quand même ? ». Il ne voit ni les notes ni la raison détaillée, pour que sa propre notation, à la fin du dossier, ne soit pas influencée. Son choix de continuer ou non est enregistré.

**Le verdict sert aussi aux appels suivants.** Si le document a été jugé douteux, on le précise au LLM au moment de lui demander des propositions, pour qu'il soit plus prudent.

**Les cinq dimensions**, notées de 1 à 5, chaque niveau étant accompagné d'un court repère :

1. **Organisation du document**
2. **Langage** : clarté et compréhensibilité du texte
3. **Cohérence médicale**
4. **Capacité de synthèse**
5. **Qualité générale**

Le testeur note le CRH sur ces mêmes dimensions à la fin de chaque dossier.

---

## 3. L'organisation technique

### 3.1 Les trois morceaux

| Où ? | Quoi ? |
|---|---|
| **GitHub Pages** | La page web, publiée gratuitement depuis le dépôt public. Tout le programme s'exécute dans le navigateur du testeur. |
| **Supabase** (région européenne) | Les comptes et profils des testeurs, les CRH, les codages d'origine, les fiches, le guide des situations cliniques, et tout ce que les testeurs enregistrent. |
| **Le LLM** | Mistral par défaut. Chaque testeur utilise son propre accès. |

Il n'y a **aucun serveur à administrer**.

### 3.2 Le connecteur LLM générique

L'outil ne dépend d'aucun fournisseur. De nombreux services, dont Mistral, acceptent les demandes dans un format commun ; c'est aussi le cas des serveurs de modèles qu'on installe soi-même. Le connecteur est donc décrit par trois réglages : **l'adresse du service, le nom du modèle et la clé**. Chaque appel enregistre le fournisseur, le modèle et la version du prompt utilisés.

La clé reste sur l'ordinateur du testeur. Elle n'est **jamais envoyée à Supabase**. Un bouton **« Oublier mes réglages »** permet de l'effacer, en particulier sur un PC partagé.

**Point à vérifier dès le lot A2** : si le fournisseur refuse d'être appelé directement depuis une page web, une petite fonction hébergée chez Supabase servira de relais. Elle transmettra la clé du testeur **sans la conserver**.

### 3.3 Les comptes et les règles d'accès

- **Inscription ouverte**, par lien envoyé par courriel, avec la fiche d'inscription décrite au §2.1.
- Chaque testeur **voit tous les CRH** mais **ne voit et ne modifie que ses propres dossiers**.
- **Les codages d'origine sont inaccessibles aux testeurs.** Ce n'est pas seulement une question d'affichage : la base de données elle-même refuse de les leur transmettre. C'est indispensable, puisque le code de la page est public.
- **Les évaluations du document par le LLM** sont enregistrées par la page au moment de l'appel, mais la base ne permet pas au testeur de les relire ensuite.
- Le responsable du projet accède à l'ensemble des données depuis l'interface de Supabase et par des scripts d'export.
- Les protections standard de Supabase contre les inscriptions en masse sont activées.

### 3.4 Les choix techniques

- **La page** : du JavaScript simple, sans outil de construction. Les fichiers du dépôt sont publiés tels quels.
- **Les scripts de préparation, de chargement et d'export** : en Python.
- **Les données ne sont jamais placées dans le dépôt GitHub**, qui est public. Les scripts lisent les fichiers sur l'ordinateur de celui qui les lance et les chargent dans Supabase.

---

## 4. Les données

### 4.1 Le principe : un format commun

Les CRH arrivent par **lots**, dans des formats différents :

- **PARHAF**, publié sur Hugging Face ;
- **les CRH synthétiques**, stockés sur Google Drive.

Certains lots contiennent un **codage avec des éléments de preuve**, d'autres **seulement le texte**. Plutôt que de faire connaître tous ces formats à l'outil, on convertit chaque lot vers **un format commun**, puis on charge ce format dans la base. L'outil ne connaît que le format commun.

Ce format commun est le **contrat** entre les deux projets décrits au §5 : il doit être fixé en premier.

### 4.2 Le format commun d'un document

**Décisions issues de l'exploration de PARHAF :**

- **Un dossier = un patient.** Dans PARHAF, chaque situation clinique comprend un à trois documents (CRH, compte rendu opératoire, de consultation, d'anatomopathologie…), qui forment un mini-dossier patient. Ces documents sont **concaténés en un seul texte**, que le testeur code comme un tout. Les limites de chaque document sont conservées (type et position de début et de fin dans le texte concaténé), et chaque document est précédé d'un intitulé visible indiquant son type.
- **Quatre codages par dossier**, de même forme pour PARHAF et pour les CRH synthétiques :

| Codage | PARHAF | CRH synthétiques |
|---|---|---|
| **Codage initial** | Le diagnostic principal du scénario | Les diagnostics figurant à la fin du document |
| **Codage proposé par l'IA** | Les propositions du LLM, le cas échéant | Idem |
| **Codage validé par l'utilisateur** | Le codage final du testeur | Idem |

  Dans les deux cas, le codage initial correspond aux **diagnostics du scénario** qui a servi à rédiger ou à générer le texte. Pour PARHAF, on considère le diagnostic principal du scénario comme le vrai diagnostic principal : quelques vérifications ont montré qu'il correspondait bien au texte. Le codage initial est simplement plus complet pour les CRH synthétiques que pour PARHAF.

- **Version de PARHAF chargée** : le JSON (version de référence déclarée par les auteurs). Les deux versions ne diffèrent que sur des patients d'anatomopathologie, qui sont exclus.
- **Patients chargés** : tous, **sauf les patients dont le dossier ne comprend que de l'anatomopathologie**. Les consultations seules et les parcours obstétricaux sont conservés.
- **Nettoyage du texte avant chargement.** Le texte de référence est établi **une fois, avant le chargement** ; toutes les positions sont calculées sur lui, et il n'est plus jamais modifié ensuite. Le nettoyage comprend :
  - la normalisation des caractères (forme NFC, espaces insécables, caractères de largeur nulle, BOM) ;
  - le retrait de tout ce qui n'est pas le compte rendu lui-même : résumé structuré recopié en fin de texte, listes de « diagnostics fréquemment associés », et tout autre bloc de même nature.
  
  Le fichier source n'est jamais modifié. Chaque retrait est tracé (règle appliquée, passage retiré), et le passage retiré est conservé à part, sans jamais être affiché.
- **Ce que voit le testeur : uniquement ce qu'un codeur voit en réalité, c'est-à-dire le texte du compte rendu.** Toutes les autres informations restent dans la base.
- **Peu de colonnes.** Les sources intégrées plus tard n'auront pas toutes le même niveau de détail que PARHAF. La table des dossiers garde donc un minimum de colonnes ; le reste est rangé dans des champs JSON, indexés et interrogeables.
- **Un champ JSON « RUM »**, prévu dès maintenant, qui contiendra les variables du résumé d'unité médicale, **selon son format officiel** : données administratives, modes d'entrée et de sortie, etc. Il ne contient que des variables du RUM. Il servira au groupage et aux simulations de codage. À terme, ces informations seront soit fournies à l'outil, soit extraites automatiquement du texte par le modèle. Pour PARHAF, elles pourraient être reprises du scénario. **Dans le démonstrateur, le champ est créé mais son alimentation est reportée.**
- **Deux colonnes pour trouver les dossiers à coder** : la **spécialité médicale** et le **type de prise en charge** (`type_of_care` pour PARHAF), qui n'est pas une variable du RUM. Elles servent à rechercher et filtrer les dossiers, comme un codeur cherche ses séjours. Elles ne sont pas affichées dans le dossier lui-même, à côté du texte.
- **Forme des codes** : alignée sur celle des fiches recode-icd.

**Décisions issues de l'exploration des CRH synthétiques :**

- **Les comptes rendus opératoires** produits par les gabarits chirurgicaux sont **conservés**.
- **`coding_rule` à « other »** (56 745 lignes) : c'est normal, les règles du guide ne concernent que certaines situations. Ce n'est pas un critère d'exclusion.
- **Nettoyage** : même logique que pour PARHAF. On retire les blocs « Dictionnaires des formulations », les JSON recopiés dans le texte et les codes entre parenthèses ; on écarte les 2 095 lignes dont le JSON n'est pas réparable simplement.
- **`type_of_care`** : conservé sous sa valeur brute pour la recherche, sans correspondance avec les familles D, T et S du guide.
- **Hôpitaux réels cités dans les textes** : sans objection, les personnes étant fictives.
- **Les 5 CRH de PARHAF dont le corps contient des codes** : relus et corrigés par Rémi, plutôt qu'exclus.

Le détail du format reste à fixer lors de la séance sur le schéma.

Chaque document est décrit par :

- **son identité** : lot, source, identifiant d'origine ;
- **son texte**, normalisé une fois pour toutes (sauts de ligne uniformes), puis **jamais modifié**, car tous les éléments de preuve sont repérés par leur position dans le texte. Une empreinte du texte est enregistrée pour le garantir ;
- **ses métadonnées** éventuelles (spécialité, type de séjour, informations du scénario de génération…) ;
- **son codage d'origine, facultatif**, qui peut comprendre, selon ce que fournit le lot :
  - la règle de hiérarchisation ;
  - le code Z ;
  - les codes avec leur catégorie ;
  - pour chaque code, ses éléments de preuve (position de début et de fin, texte cité).

Chaque élément facultatif peut être absent. Le format indique explicitement ce que contient chaque lot, pour qu'une absence ne soit jamais confondue avec une donnée vide.

**Un même format JSON pour tous les codages.** Le codage est décrit par un objet JSON, sur le modèle de celui qui figure à la fin des CRH générés. Ce même format sert pour :

- le codage d'origine d'un document ;
- les réponses du LLM ;
- le codage final du testeur.

Ainsi, comparer deux codages revient à comparer deux objets de même forme. Le format exact sera fixé lors de la séance de travail sur le schéma (§6), à partir d'un exemple réel.

### 4.3 Les tables de la base

> **Remplacé par `docs/SCHEMA.md`**, qui fait foi pour la structure de la base. Le texte ci-dessous est conservé pour mémoire.

**Les données de référence**, chargées par les scripts :

| Table | Contenu | Visible des testeurs ? |
|---|---|---|
| `lots` | Les lots de CRH : nom, source, description, ce qu'ils contiennent, date de chargement | Oui |
| `documents` | Les CRH : lot, identifiant d'origine, texte, empreinte, métadonnées | Oui |
| `codages_origine` | Le codage d'origine d'un document : règle, code Z | **Non** |
| `codes_origine` | Les codes du codage d'origine, avec leur catégorie | **Non** |
| `preuves_origine` | Les éléments de preuve du codage d'origine | **Non** |
| `fiches` | Les fiches d'identité des codes : code, libellé, contenu, version | Oui |
| `synonymes` | Les formulations associées à chaque code, indexées par mot pour la recherche (§4.5) | Oui |
| `regles_situations` | Le guide des situations cliniques : règle, type, spécificité, pathologie, code Z | Oui |

**Les données produites par les testeurs** :

| Table | Contenu |
|---|---|
| `profils` | Nom, prénom, statut, établissement, date d'accord |
| `dossiers` | Le travail d'un testeur sur un CRH : testeur, document, état, dates ; règle et code Z retenus, avec leurs deux statuts |
| `ensembles` | Les ensembles surlignés d'un dossier |
| `preuves` | Les éléments de preuve d'un ensemble : position, texte cité, origine (testeur ou LLM) |
| `codes` | Le codage courant : ensemble, code, catégorie, statut d'origine, statut de revue, proposition d'origine éventuelle |
| `appels_llm` | Chaque appel : type, fournisseur, modèle, version du prompt, réponse complète, durée |
| `propositions` | Chaque code proposé par le LLM : ensemble, code, catégorie, confiance, explication, preuve introuvable ou non |
| `alertes` | Chaque alerte de revue : code concerné, source (contrôle fixe ou LLM), niveau, message, réponse du testeur, motif |
| `evaluations_document` | L'évaluation faite à l'ouverture du dossier : indicateurs fixes, notes et verdict du LLM, raison, choix du testeur de continuer ou non. **Le testeur peut l'enregistrer mais pas la relire.** |
| `notes_qualite` | La note du testeur sur les cinq dimensions, et son commentaire |
| `evenements` | Le journal de toutes les actions : qui, quand, quoi, avant, après, motif |

Le journal des événements garantit qu'aucune information n'est perdue : même si le codage courant change, on peut toujours retracer comment on en est arrivé là.

> **Schéma provisoire.** Ces tables donnent une première idée de l'organisation des données. Le schéma définitif sera établi lors d'une séance de travail dédiée, au début du projet (§6). Le choix entre des tables détaillées et des objets JSON y sera tranché : il est probable qu'on combine les deux, avec des tables pour ce qu'on interroge souvent (dossiers, codes, statuts) et du JSON pour les objets complets (codages, réponses du LLM).

### 4.4 Les autres données de référence

- **Les fiches d'identité des codes**, issues de recode-icd. Le script de chargement lit la liste des codes dans l'index de la livraison, conformément au contrat d'interface de recode-icd, et enregistre la version des fiches.
- **La liste des codes CIM-10 valides**, qui sert à vérifier que les codes proposés existent. Elle est tirée du même index que les fiches.
- **Le guide des situations cliniques**, après correction (voir §7).

### 4.5 La table des synonymes

**Le cas d'usage.** Le LLM a proposé un code pour un élément de preuve, mais le testeur veut le changer. Il doit pouvoir retrouver rapidement le bon code en tapant quelques mots, par exemple « diverticulite perforée », sans connaître le code ni son libellé officiel exact.

**Le principe.** La table associe à chaque code toutes ses formulations connues : libellé officiel, inclusions, entrées de l'index, synonymes issus de recode-icd. Chaque formulation est **découpée en mots**, et ces mots sont **indexés** : la base sait retrouver très vite toutes les formulations qui contiennent un mot donné, comme l'index à la fin d'un livre. La recherche tolère les accents, les majuscules et les fautes de frappe légères.

**Le résultat.** Le testeur tape ses mots, l'outil affiche les codes dont une formulation correspond, les plus pertinents en premier, avec la formulation trouvée. Il choisit le code et la correction est enregistrée.

Cette recherche fonctionne **sans le LLM** : elle reste disponible même si le service ne répond pas. C'est l'équivalent de l'aide 1 (le dictionnaire) des cahiers des charges.

---

## 5. Les prompts

L'outil fait appel au LLM pour **quatre tâches**, toutes depuis la page, comme le ferait un véritable outil de codage :

| Tâche | Moment | Ce qu'on envoie |
|---|---|---|
| Évaluer le document | À l'ouverture du dossier | Le texte, les indicateurs fixes, la grille des cinq dimensions |
| Proposer les caractéristiques du séjour | À la demande du testeur | Le texte, le guide des situations cliniques, le verdict de l'évaluation |
| Proposer des codes | À la demande du testeur | Le texte, les ensembles surlignés, le verdict de l'évaluation |
| Revoir le codage | À la demande du testeur | Le texte, le codage retenu, les fiches des codes choisis, le guide des situations cliniques |

**Les fiches transmises pour la revue.** On transmet une fiche par code choisi. Chaque fiche contient elle-même les codes voisins à ne pas choisir (exclusions, codes plus ou moins précis) : il n'est donc pas nécessaire d'envoyer les fiches des codes voisins.

Chaque prompt est un **fichier du dépôt, numéroté par version**, avec le format de réponse attendu. Chaque appel enregistre la version utilisée.

La mise au point des prompts est un travail à part entière. Les CRH dotés d'un codage d'origine offrent pour cela une ressource précieuse : un **banc d'essai** en Python peut faire tourner une version de prompt sur un échantillon de ces CRH, comparer les réponses au codage d'origine, et mesurer si une nouvelle version fait mieux que la précédente avant de la mettre en service.

---

## 6. L'organisation du travail : deux projets en parallèle

Le travail se répartit en **deux projets Claude Code distincts**, qui avancent en même temps. Ils ne dépendent l'un de l'autre que par le **format commun** et le **schéma de la base**, fixés au départ.

### Étape commune — Le socle

| Contenu | Résultat |
|---|---|
| Création du dépôt `codeur` et du projet Supabase (guide pas à pas). | L'infrastructure existe. |
| **Exploration des corpus avec Claude Code, pas à pas** : aller chercher les fichiers qui contiennent chaque corpus (PARHAF sur Hugging Face, CRH synthétiques sur Google Drive), en charger quelques documents, les regarder ensemble, faire l'inventaire de ce que chaque source contient (texte, codage, éléments de preuve, JSON de fin des CRH générés). | Une note d'inventaire de chaque source. |
| **Séance de travail sur le schéma**, à partir de cet inventaire, avant d'écrire le code de l'outil : format JSON du codage, contenu des tables, règles d'accès. C'est aussi l'occasion de clarifier le besoin. **Faite le 18 octobre 2026 : voir `docs/SCHEMA.md`.** | Le format commun et le schéma sont fixés et documentés. |
| Création des tables par Claude Code, à partir du schéma validé. | Les deux projets peuvent démarrer. |

### Projet A — L'outil web

| Lot | Contenu | Ce qu'on peut tester |
|---|---|---|
| **A1 — Lire et surligner** | Connexion par lien, fiche d'inscription, liste des CRH, affichage, surlignage, ensembles, sauvegarde. Mesures fixes sur le texte. Publication sur GitHub Pages. | Un testeur s'inscrit, surligne, retrouve son travail. **Test depuis un PC de l'AP-HP.** |
| **A2 — Évaluer et proposer** | Réglages du LLM, connecteur générique, évaluation du document et avertissement, propositions de codes et de caractéristiques du séjour, contrôle des codes et des preuves. | Le LLM évalue le document et propose des codes et une règle. |
| **A3 — Décider** | Accepter, corriger, rejeter, ajouter ; recherche de codes par mots dans la table des synonymes ; changer la catégorie ; règle et code Z ; statuts d'origine. | Le codage complet est enregistré. |
| **A4 — Revoir** | Contrôles fixes (codes valides, cohérence entre la règle et la pathologie principale), revue par le LLM, alertes, statuts de revue. | La revue signale les incohérences. |
| **A5 — Noter et diffuser** | Grille de qualité, guide du testeur, finitions. | L'outil peut être diffusé. |
| **A6 — Éditer les CRH** | Page d'édition du texte d'un document : correction, motif, enregistrement d'une nouvelle version. Possibilité de reprendre un codage existant sur la nouvelle version. | Un CRH peut être corrigé avant d'être codé. |

### Projet B — Les données et les prompts

| Lot | Contenu | Résultat |
|---|---|---|
| **B1 — PARHAF** | Récupération depuis Hugging Face, conversion vers le format commun, contrôles, chargement. | PARHAF est dans la base. |
| **B2 — CRH synthétiques** | Récupération depuis Google Drive, conversion, contrôles, chargement. | Les CRH synthétiques sont dans la base. |
| **B3 — Référentiels** | Chargement des fiches, de la liste des codes valides, des synonymes (avec leur index) et du guide des situations cliniques. | Les référentiels sont dans la base. |
| **B4 — Banc d'essai des prompts** | Comparaison des réponses du LLM au codage d'origine sur un échantillon. | Les prompts sont mis au point sur des mesures. |
| **B5 — Export et analyse** | Scripts d'export et premières analyses : accord avec le codage d'origine, qualité des propositions, évaluations des documents. | Les données sont exploitables. |

Le lot A1 peut démarrer avec quelques CRH chargés à la main, sans attendre le projet B.

---

## 7. Décisions et questions ouvertes

**Décisions prises :**

- **Statuts de la fiche d'inscription** : médecin DIM, TIM, autre médecin, interne, étudiant, autre.
- **Modèle par défaut** : `mistral-large-latest`. Ce nom désigne toujours la version la plus récente du modèle : des dossiers codés à quelques semaines d'intervalle peuvent donc l'avoir été avec deux versions différentes. Chaque appel enregistre le nom du modèle et la date, et la version exacte si le service l'indique dans sa réponse.
- **Guide des situations cliniques** : corrigé par Rémi avant le lot A2 (règles S2 et S3 en double, codes Z95 et Z96 pour S3, règles D5 et D6 de même spécificité, pathologie absente pour S4, noms de listes comme `icd_codes_legal_abortion` à remplacer par leur contenu ou par une description).

- **Fiches pour la revue** : une fiche par code choisi ; chaque fiche contient les codes voisins à ne pas choisir.
- **Mesures fixes** : calculs simples repris du projet de génération ; pas de seuil dans ce projet.
- **Nom du dépôt** : `codeur`.

- **Exploration des corpus** : faite pas à pas avec Claude Code, en regardant les documents réels ; le format du codage est décidé à l'issue de cette exploration.

- **Format du champ RUM** : format officiel ATIH « RSS non groupé », version 023 (fichier `formats_mco_2026.xlsx`, à placer dans le dépôt, dans `docs/referentiels/`). Sa traduction en champ JSON sera faite lors de la séance sur le schéma.
- **Codage et RUM : on garde les deux.** Le codage CIM est une étape de la construction du RUM. Les codages (initial, proposé par l'IA, validé par l'utilisateur) vivent dans le JSON du codage, avec leurs versions successives. Quand un codage est validé, ses diagnostics sont **reportés dans le RUM** (DP, DR et DA, déduits des quatre catégories selon la règle de hiérarchisation), à côté des variables administratives. Le RUM n'est jamais modifié directement : si le codage est modifié après validation, le RUM est reconstruit à partir de la nouvelle version, et l'on sait toujours de quelle version du codage il provient.

- **Organisation de la base proposée par Rémi** (point de départ de la séance sur le schéma) :
  - **table des documents** : un seul texte par situation clinique, avec quelques colonnes seulement (source, spécialité, type de prise en charge). **Pas de colonne « scénario »** : l'outil est un outil de codage, pas de génération. Les informations utiles du scénario sont réparties là où un outil de codage les attendrait : le diagnostic principal du scénario devient le codage initial (table des codages), les données administratives iront dans le RUM ;
  - **table des codages** : toutes les versions successives du codage, sans jamais rien écraser. Chaque ligne porte le document, l'origine du codage (initial, IA, utilisateur), la date et l'utilisateur, et le codage lui-même au format JSON (codes et éléments de preuve) ;
  - **table des RUM**, historisée de la même façon : chaque ligne porte le document, **la ligne de la table des codages dont elle reprend le codage**, la date et l'utilisateur, et le RUM au format JSON. Chaque codage validé peut ainsi produire son propre RUM, et plusieurs testeurs peuvent coder le même document.
- **Édition des CRH et versions des documents.** On édite le texte **avant** de le coder. L'enregistrement crée une **nouvelle version** du document, reliée à la précédente ; on code ensuite cette version. Un codage est toujours lié à une version précise, dont le texte n'est plus modifiable. Pour modifier un texte déjà codé, on crée une nouvelle version et on fait un nouveau codage ; l'ancien codage peut être repris comme point de départ, ses éléments de preuve étant retrouvés dans le nouveau texte grâce au texte cité (ceux qui ne s'y retrouvent plus sont signalés). Le schéma prévoit les versions de documents dès le départ ; la page d'édition fait l'objet du lot A6.
- **Pas de gestion des rôles dans cette version de test** : tout utilisateur connecté peut tout faire, y compris éditer un CRH. Les rôles identifiés au fil du travail sont simplement consignés ci-dessous, pour les versions suivantes.

**Rôles identifiés (non mis en œuvre dans le prototype) :**

| Rôle | Ce qu'il pourrait faire | Où il est apparu |
|---|---|---|
| Codeur (testeur) | Coder les dossiers, revoir son codage, noter la qualité du CRH | Rôle de base du prototype |
| Éditeur | Corriger le texte d'un CRH, créant une nouvelle version | Page d'édition (lot A6) |
| Responsable du projet | Paramétrer l'outil, charger les corpus, accéder à toutes les données et aux exports | Paramétrage, projet B |
| Arbitre, collège d'experts, administrateur de campagne | Organiser un double codage et arbitrer les désaccords | Cahier des charges n° 1 |

**À fournir au moment voulu :**

- **Les calculs de mesures fixes** utilisés dans le projet de génération (lot A1).

**Questions laissées ouvertes, à discuter pendant le développement** (les deux premières sont réglées par `docs/SCHEMA.md`, dont le §9 liste les questions restantes) **:**

1. **Le schéma de la base et le contenu des tables**, y compris le choix entre tables détaillées et objets JSON (séance dédiée, §6).
2. **Le format JSON du codage**.
