# Référentiels de qualité

Ce dossier reçoit les deux référentiels qui servent à juger la qualité d'un document et d'un codage.

- `grille_qualite.md` : la **grille de qualité du CRH**, cinq dimensions (organisation du document, langage, cohérence médicale, capacité de synthèse, qualité générale), chacune notée de 1 à 5 avec un court repère pour chaque niveau. Elle est utilisée par le LLM à l'ouverture du dossier et par le testeur à la fin (`CADRAGE.md` §2.5 ; table `evaluations`, `docs/SCHEMA.md` §5.3). À rédiger (lots A2 et A5).
- `controles_pmsi.md` : les **règles de contrôle qualité PMSI** appliquées au RUM (cohérence entre la règle de hiérarchisation et la pathologie principale, incompatibilités avec l'âge ou le sexe, statuts MCO des codes…), avec leur version. Leur résultat est enregistré dans la colonne `controles` de la table `rum` (`docs/SCHEMA.md` §4). À rédiger (lot A4).

État et version : voir `docs/referentiels/README.md`, §3.3.
