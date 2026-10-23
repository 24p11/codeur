# La CIM-10 à usage PMSI dans `codeur`

## Ce que c'est

La **CIM-10** est la classification internationale des maladies de l'OMS, 10e révision. En France, les séjours hospitaliers (PMSI) sont codés avec la **CIM-10 à usage PMSI** : la version française, publiée chaque année par l'ATIH, qui ajoute à la classification de l'OMS des subdivisions (cinquième et sixième caractères) et des **extensions PMSI**, et qui dit pour chaque code s'il peut être employé dans un résumé de séjour en MCO. `codeur` utilise le **kit ATIH 2025**, par l'intermédiaire de la livraison recode-icd `65701d6_atih-2025`.

## La forme des codes dans `codeur`

Un code est écrit **sans point**, et une extension PMSI est **collée après un « + »** : `I10`, `K409`, `Z992+0`, `F03+00`. C'est la forme `code_atih` de recode-icd ; c'est celle de la base, des prompts et de l'écran. Un code écrit avec un point par le modèle (`I10.0`) est ramené à cette forme par la page avant toute vérification. Il n'existe pas d'extension « ni » : les anciennes formes comme `E11ni` ne correspondent à aucun code du kit.

## Où est l'index des codes

L'index (tous les codes du kit, 42 897, avec leur libellé et leur statut), les formulations (langage réel des comptes rendus) et les fiches de codes viennent de la livraison recode-icd, rangée **hors du dépôt** dans `donnees/referentiels/recode-icd/<version>/` (voir `recode-icd/README.md` dans ce dossier). L'index et les formulations sont chargés dans la base (`fiches`, `synonymes`, `descendants_codables`, `docs/chargement.md` §2) ; les fiches ne sont pas encore chargées.

## Codables, « père interdit », extensions

- Un code **codable** peut être employé dans un RUM en MCO (`fiches.codable`). Le statut `statut_mco` précise les cas : `codable`, `cause_externe` (chapitre XX, codable comme diagnostic associé seulement), `interdit_dp_dr`, `interdit_dp`.
- Un code **« père interdit »** (`pere_interdit`) est une catégorie ou sous-catégorie que l'ATIH a subdivisée : il faut employer un de ses descendants (`C50` → `C504`, `E11` → `E1190`…). Un code **supprimé** (`supprime`) a disparu du kit. Aucun code non codable n'entre dans un codage (`docs/SCHEMA.md` §3.10) : la page propose les descendants codables (`descendants_codables`) et fait corriger le modèle.
- Une **extension PMSI** distingue des situations que l'OMS ne sépare pas (`Z992+0` hémodialyse, `Z992+1` dialyse péritonéale) ; le code souche reste parfois codable (`Z992`), mais plus précis vaut mieux (`recode-icd/extensions_preambule.md`).
- Dans une **liste de codes**, une catégorie sans subdivision (`Z95`, `Z80`) désigne la catégorie et tous ses descendants codables.

## Les sous-dossiers

| Dossier ou fichier | Contenu |
|---|---|
| `chapitres.csv` | Les 22 chapitres de la CIM-10 : numéro romain, ordre, intitulé, premier et dernier code. Vérifié contre l'index : chaque code du kit tombe dans un et un seul chapitre. Chargé dans la table `chapitres` |
| `listes_codes/` | Une liste de codes CIM-10 par fichier, au format `code,libelle` ; `README.md` donne la source, l'usage et les codes retirés à la conversion. Chargées dans `listes_codes` (nature `cim`) |
| `recode-icd/` | La documentation de la livraison recode-icd (sans données) et son `README.md` |

Les listes d'actes CCAM sont dans `../ccam/listes_actes/`, le guide des situations cliniques dans `../situations_cliniques/`.
