# Mode d'emploi — résolveur de codes (`recode-icd resoudre`)

> Le résolveur est le **point d'entrée officiel des consommateurs** :
> toute écriture d'un code CIM-10 → la fiche, ou la **raison motivée**
> de son absence. Aucun traitement aval ne doit joindre « à la main »
> sur le code.

## Invocation

```bash
uv run recode-icd resoudre I64 W0009 O0490 A18.1        # lisible
uv run recode-icd resoudre A18.1 --json                  # sortie machine
uv run recode-icd resoudre CODE --journal usage.jsonl    # journalise les négatives
```

En Python : `recode_icd.couverture.resoudre_code(code, ctx)`.

## Écritures acceptées

Compacte ATIH (`O0490`, `W0009`), pointée (`O04.90`, `A18.1`), maître
(`O04.-0.9`). La traduction entre écritures est déclarée dans
`notations_codes.yaml` — ne jamais insérer un point soi-même :
`S37.8-0` (nœud) et `S37.80` (feuille) sont deux codes différents.

## Les réponses

| Statut | Sens | Ce que porte la réponse |
|---|---|---|
| `fiche` | le code a sa fiche | chemin de la fiche (et un avertissement si `codable_mco=False`) |
| `compose` | code composé du chapitre XX | le **tronc** avec fiche + lieu/activité/précision décomposés et libellés |
| `composition_invalide` | composition impossible | la position fautive et les valeurs admises sous ce tronc |
| `intermediaire` | nœud non terminal | ses feuilles qui ont une fiche |
| `pere_interdit` | type 3 ATIH (ex. `U07.1`) | ses subdivisions avec fiche (`U07.10`…`U07.15`) |
| `supprime` | code supprimé du kit | le millésime de suppression |
| `inconnu_atih` | connu du maître, inconnu du kit | non codable en MCO — pas de fiche, et c'est voulu |
| `sans_ligne` / `absent_du_maitre` / `inconnu` | hors référentiel | l'ancêtre le plus proche, le cas échéant |
| `notation_invalide` | écriture non parsable | — |

**Une réponse négative n'est pas une erreur du résolveur** : c'est une
information de codage (le code ne se code pas tel quel en MCO). Le bon
réflexe applicatif est de suivre la piste donnée (feuilles, tronc,
subdivisions), pas de retenter des variantes d'écriture.

## Journal d'usage

`--journal <fichier.jsonl>` ajoute une ligne par réponse **négative**.
Remonter ce journal avec vos retours : c'est la mesure d'usage qui
priorise les évolutions de la couverture.

## Exemples

```
I64    → fiche      IX/I64.md
W0009  → compose    tronc W00 + lieu 0 « domicile » + activité 9 — fiche XX/W00.md
W0005  → composition_invalide : activité 5 hors table sous W00 (admises : 0,1,2,3,4,8,9)
O0490  → fiche      XV/O04.-0.9.md (écriture maître de « O04.90 »)
U07.1  → pere_interdit : coder une subdivision — U07.10…U07.15 ont une fiche
```
