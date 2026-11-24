# codeur

Avant toute chose, lire **`CARNET_DE_BORD.md`** à la racine : il dit ce qu'est le projet, les règles à ne jamais
enfreindre (§2), la façon de travailler (§3), où sont les choses (§4), l'état du travail (§5), les décisions fixées (§6),
ce qui reste à faire (§7), les pièges connus (§8) et le journal des séances (§9). Il renvoie à la documentation
détaillée (`docs/`). Le mettre à jour en fin de séance (§5, §7, §8, §9).

Rappels qui ne souffrent aucune exception :

- Le dépôt est public : aucun secret, aucune donnée ; `.env` n'est jamais affiché, `donnees/` jamais suivi par git.
- Aucun `git push` sans l'accord explicite de Rémi.
- Aucune commande qui supprime ou vide des données de la base sans accord explicite ; toute évolution de la base passe
  par une migration, avec essai à blanc montré avant `npx supabase db push`.
- En début de séance : `git pull`, et signaler ce qui a changé.
