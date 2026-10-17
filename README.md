# codeur

Prototype d'aide au codage CIM-10 assisté par un LLM, destiné à une centaine
de testeurs. L'utilisateur ouvre un compte rendu d'hospitalisation fictif,
surligne des passages, le LLM propose des codes, l'utilisateur décide, puis
le LLM revoit le codage. Toutes les actions sont enregistrées pour analyse.

Architecture : page web statique (GitHub Pages), base Supabase (PostgreSQL,
région européenne), appels au LLM depuis le navigateur avec la clé de chaque
testeur. Des scripts Python préparent et chargent les données.

Le document de référence est [CADRAGE.md](CADRAGE.md).

Ce dépôt est public : il ne contient ni données (CRH, codages) ni secrets.
Les données sont rangées dans `donnees/` et les clés dans `.env`, tous deux
exclus de git (voir `.env.exemple`).
