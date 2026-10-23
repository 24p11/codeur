# Les extensions PMSI — préambule pour les consommateurs

> Généré du kit ATIH 2025 (360 codes à extension « + »,
> portés par 71 codes souches). Ne pas modifier à la main.

Une **extension PMSI** est un suffixe ajouté par l'ATIH à un code
CIM-10 pour distinguer des situations que l'OMS ne sépare pas. Dans la
forme `codeur` (sans point, extension collée), elle suit un « + » :
`Z992+0`, `K861+8`.

**Trois choses à savoir :**

1. **Il n'existe PAS de sémantique transversale des extensions.** Le
   « +0 » de `Z992+0` (hémodialyse) n'a rien à voir avec le « +0 »
   d'un autre code : le sens est porté par le LIBELLÉ de chaque
   extension. Pour savoir quelle information chercher dans le texte,
   lire les libellés des extensions du code — la fiche de navigation
   du code souche les rassemble avec le critère qui les départage.
2. **Un code souche à extensions peut être lui-même codable.**
   Exemple, la famille `Z992` (kit 2025) :

   | Code | Libellé | Codable |
   |---|---|---|
| `Z992` | DEPENDANCE ENVERS UNE DIALYSE RENALE | oui |
| `Z992+0` | DEPENDANCE ENVERS UNE HEMODIALYSE | oui |
| `Z992+1` | DEPENDANCE ENVERS UNE DIALYSE PERITONEALE | oui |
| `Z992+8` | DEPENDANCE ENVERS UNE DIALYSE RENALE, NCA | oui |

   Proposer `Z992` n'est donc pas une erreur de RUM : c'est un code
   valide, moins précis. L'affinage vers l'extension est proposé quand
   le texte porte l'information, jamais imposé. À l'inverse, un père
   interdit (`E11`, `R521`) n'est JAMAIS codable : la correction est
   obligatoire (`codes.csv`, colonne `codable_mco`).
3. **L'extension « ni » n'existe pas au kit 2025** (0 code sur
   42897). Une forme comme `E11ni` ne se résoudra jamais ;
   seul « + » introduit une extension.
