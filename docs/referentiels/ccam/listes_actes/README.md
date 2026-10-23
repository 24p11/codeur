# Listes d'actes CCAM

Dossier prévu pour les listes d'actes de la CCAM citées par le guide des situations cliniques, au format commun `code,libelle` (nature `ccam` dans la table `listes_codes`).

**Aucune liste n'est disponible pour l'instant** (23 octobre 2026) : `codeur` ne recueille pas d'actes. Les deux listes attendues du projet Stream sont :

| Liste attendue | Règle du guide | État |
|---|---|---|
| `procedure_curitherapy` | T10-irradiations (curiethérapie) | à fournir |
| `procedure_single_irradiation` | T10-irradiations (irradiation en dose unique) | à fournir |

Tant qu'elles manquent, la règle T10-irradiations est chargée dans `regles_situations` mais signalée **non évaluable** : elle n'est jamais proposée parmi les règles compatibles avec une pathologie principale.
