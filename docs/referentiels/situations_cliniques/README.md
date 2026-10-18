# Guide des situations cliniques

Ce dossier reçoit le **guide des situations cliniques**, c'est-à-dire la liste des règles de hiérarchisation (`D1`, `T3`, `S1-Chronic`…) avec, pour chacune, sa famille (tirée de la colonne « Type d'hospitalisation »), son libellé, son type, sa spécificité, la ou les pathologies concernées et l'éventuel code Z de prise en charge.

- Fichier attendu : `guide_situations_cliniques.csv`, version corrigée par Rémi (doublons S2/S3, codes Z95/Z96, règles D5/D6, pathologie de S4, noms de listes à remplacer par leur contenu ; voir `CADRAGE.md` §7).
- Usage dans l'outil : proposition de la règle de hiérarchisation par le LLM, contrôle de cohérence entre la règle et la pathologie principale, valeur du champ `regle_hierarchisation` du codage.
- Chargé dans la table `regles_situations` par un script du lot B3 (`docs/SCHEMA.md` §6 et §10.11).
- État et version : voir `docs/referentiels/README.md`, §3.2.
