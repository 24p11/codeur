# codeur

Prototype d'aide au codage CIM-10 assisté par un LLM, destiné à une centaine
de testeurs. L'utilisateur ouvre un compte rendu d'hospitalisation fictif,
surligne des passages, le LLM propose des codes, l'utilisateur décide, puis
le LLM revoit le codage. Toutes les actions sont enregistrées pour analyse.

Architecture : page web statique (GitHub Pages), base Supabase (PostgreSQL,
région européenne), appels au LLM depuis le navigateur avec la clé de chaque
testeur. Des scripts Python préparent et chargent les données.

**Pour les testeurs** : `codeur` est un outil d'aide au codage CIM-10 des comptes rendus d'hospitalisation. Le codeur surligne dans un compte rendu fictif les passages à coder ; l'IA regroupe ces passages par affection, propose les codes, puis la règle de hiérarchisation du guide des situations cliniques et le mode de prise en charge ; le codeur accepte, corrige ou complète, commente et note le compte rendu. Le test se fait en ligne, sur le site **<https://24p11.github.io/codeur/>** (rien à installer : un navigateur, une adresse de courriel et une clé d'accès au LLM suffisent). Tout est expliqué pas à pas dans le **[guide du testeur](docs/guide_testeur.md)** (connexion, réglage de l'accès à l'IA, surlignage, codage, correction, commentaires, notation).

Le document de référence est [CADRAGE.md](CADRAGE.md).

Ce dépôt est public : il ne contient ni données (CRH, codages) ni secrets.
Les données sont rangées dans `donnees/` et les clés dans `.env`, tous deux
exclus de git (voir `.env.exemple`).
