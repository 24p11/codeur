-- Migration 3 : les tables de travail (docs/SCHEMA.md §3, §4, §5).
-- Ordre imposé par les liens : profils, appels_llm, codages, rum, evaluations.

-- ---------------------------------------------------------------- profils
create table public.profils (
  id            uuid primary key references auth.users (id) on delete cascade,
  nom           text not null,
  prenom        text not null,
  statut        text not null check (statut in ('medecin_dim', 'tim', 'autre_medecin', 'interne', 'etudiant', 'autre')),
  etablissement text not null,
  accord_le     timestamptz not null,
  cree_le       timestamptz not null default now()
);
comment on table  public.profils is 'Les informations saisies à l''inscription, une ligne par compte (SCHEMA.md §5.1).';
comment on column public.profils.id is 'Le compte utilisateur (auth.users).';
comment on column public.profils.nom is 'Nom.';
comment on column public.profils.prenom is 'Prénom.';
comment on column public.profils.statut is 'Statut : medecin_dim, tim, autre_medecin, interne, etudiant, autre (CADRAGE.md §7).';
comment on column public.profils.etablissement is 'Établissement.';
comment on column public.profils.accord_le is 'Date de l''accord pour l''utilisation des annotations à des fins de recherche.';
comment on column public.profils.cree_le is 'Date et heure de création du profil.';

-- ---------------------------------------------------------------- appels_llm
create table public.appels_llm (
  id             uuid primary key default gen_random_uuid(),
  cree_le        timestamptz not null default now(),
  utilisateur    uuid not null references auth.users (id),
  document       bigint not null references public.documents (id),
  tache          text not null check (tache in ('evaluation_document', 'caracteristiques_sejour', 'codage', 'revue')),
  fournisseur    text,
  modele         text,
  version_prompt text,
  requete        jsonb,
  reponse        text,
  tokens_entree  integer,
  tokens_sortie  integer,
  tokens_total   integer,
  duree_ms       integer,
  erreur         text
);
comment on table  public.appels_llm is 'Chaque appel au LLM, pour toutes les tâches (SCHEMA.md §5.2). Jamais modifié ni supprimé.';
comment on column public.appels_llm.id is 'Identifiant de l''appel : un UUID généré par la page avant l''insertion (le testeur ne pouvant pas relire la ligne, la base ne peut pas le lui renvoyer).';
comment on column public.appels_llm.cree_le is 'Date et heure de l''appel.';
comment on column public.appels_llm.utilisateur is 'Le testeur qui a déclenché l''appel.';
comment on column public.appels_llm.document is 'La version du document concernée.';
comment on column public.appels_llm.tache is 'Tâche : evaluation_document, caracteristiques_sejour, codage, revue.';
comment on column public.appels_llm.fournisseur is 'Fournisseur du service, par exemple « mistral ».';
comment on column public.appels_llm.modele is 'Nom du modèle, par exemple « mistral-large-latest », et sa version exacte si le service l''indique.';
comment on column public.appels_llm.version_prompt is 'Nom et version du fichier de prompt utilisé.';
comment on column public.appels_llm.requete is 'JSON : ce qui a été envoyé au modèle, sans la clé. Format : SCHEMA.md §5.2.';
comment on column public.appels_llm.reponse is 'La réponse brute complète du modèle.';
comment on column public.appels_llm.tokens_entree is 'Jetons en entrée, tels qu''indiqués par le service.';
comment on column public.appels_llm.tokens_sortie is 'Jetons en sortie, tels qu''indiqués par le service.';
comment on column public.appels_llm.tokens_total is 'Total des jetons, tel qu''indiqué par le service.';
comment on column public.appels_llm.duree_ms is 'Durée de l''appel en millisecondes.';
comment on column public.appels_llm.erreur is 'Message d''erreur éventuel.';

-- ---------------------------------------------------------------- codages
create table public.codages (
  id               bigint generated always as identity primary key,
  document         bigint not null references public.documents (id),
  etape            text not null check (etape in ('scenario', 'humain', 'ia', 'ia_humain', 'revue_humain', 'revue_ia', 'revue_humain_ia')),
  utilisateur      uuid references auth.users (id),
  cree_le          timestamptz not null default now(),
  codage_precedent bigint references public.codages (id),
  appel_llm        uuid references public.appels_llm (id),
  valide           boolean not null default false,
  compteurs        jsonb,
  codage           jsonb not null,
  constraint codages_utilisateur_selon_etape check (
    (etape = 'scenario' and utilisateur is null) or (etape <> 'scenario' and utilisateur is not null)
  )
);
comment on table  public.codages is 'Une ligne = l''état complet du codage d''un document à l''issue d''une étape. Jamais modifiée ni supprimée (SCHEMA.md §3).';
comment on column public.codages.id is 'Identifiant de la ligne.';
comment on column public.codages.document is 'La version précise du document codée.';
comment on column public.codages.etape is 'Étape : scenario, humain, ia, ia_humain, revue_humain, revue_ia, revue_humain_ia (SCHEMA.md §3.2).';
comment on column public.codages.utilisateur is 'Qui a produit la ligne ; pour une étape de l''IA, le testeur qui a déclenché l''appel ; vide pour l''étape scenario.';
comment on column public.codages.cree_le is 'Date et heure.';
comment on column public.codages.codage_precedent is 'La ligne dont celle-ci est la suite ; vide pour la première ligne d''un travail.';
comment on column public.codages.appel_llm is 'Pour une étape de l''IA, l''appel enregistré dans appels_llm.';
comment on column public.codages.valide is 'Vrai pour la ligne validée par l''utilisateur comme codage final de son travail.';
comment on column public.codages.compteurs is 'JSON : l''écart avec la ligne précédente (conserves, modifies, preuves_modifiees, retires, ajoutes, incertains, regle_modifiee, mode_prise_en_charge_modifie). Format : SCHEMA.md §3.6.';
comment on column public.codages.codage is 'JSON : le codage complet (regle_hierarchisation, mode_prise_en_charge, commentaires, ensembles avec code, libelle, categorie, preuves, confiance, explication, commentaires). Format : SCHEMA.md §3.4.';

-- ---------------------------------------------------------------- rum
create table public.rum (
  id               bigint generated always as identity primary key,
  document         bigint not null references public.documents (id),
  codage           bigint not null references public.codages (id),
  cree_le          timestamptz not null default now(),
  cree_par         uuid references auth.users (id),
  version_format   text not null default '023',
  rum              jsonb not null,
  controles        jsonb,
  derogation       boolean not null default false,
  motif_derogation text,
  constraint rum_derogation_avec_motif check (not derogation or motif_derogation is not null)
);
comment on table  public.rum is 'Une ligne = un RUM construit à partir d''une ligne validée de codages. Jamais modifié directement : reconstruit si le codage change (SCHEMA.md §4).';
comment on column public.rum.id is 'Identifiant du RUM.';
comment on column public.rum.document is 'La version du document.';
comment on column public.rum.codage is 'La ligne de codages dont les diagnostics sont repris.';
comment on column public.rum.cree_le is 'Date et heure de construction.';
comment on column public.rum.cree_par is 'Auteur (compte utilisateur) ; vide quand c''est un script.';
comment on column public.rum.version_format is 'Version du format ATIH « RSS non groupé » : 023.';
comment on column public.rum.rum is 'JSON : les variables officielles du RUM sous leur nom (DP, DR, DA, modes d''entrée et de sortie…), d''après docs/referentiels/formats_mco_2026.xlsx. Format : SCHEMA.md §4.';
comment on column public.rum.controles is 'JSON : résultat des contrôles qualité PMSI, avec la version des règles appliquées. Format : SCHEMA.md §4.';
comment on column public.rum.derogation is 'Vrai si l''utilisateur a passé outre une alerte bloquante.';
comment on column public.rum.motif_derogation is 'Le motif de la dérogation ; obligatoire quand derogation est vrai.';

-- ---------------------------------------------------------------- evaluations
create table public.evaluations (
  id          bigint generated always as identity primary key,
  cree_le     timestamptz not null default now(),
  utilisateur uuid not null references auth.users (id),
  document    bigint not null references public.documents (id),
  auteur      text not null check (auteur in ('ia', 'humain')),
  appel_llm   uuid references public.appels_llm (id),
  mesures     jsonb,
  notes       jsonb,
  verdict     text check (verdict in ('exploitable', 'douteux', 'non_exploitable')),
  commentaire text,
  poursuite   boolean
);
comment on table  public.evaluations is 'Les évaluations de la qualité d''un document : par le LLM à l''ouverture du dossier, par le testeur à la fin (SCHEMA.md §5.3).';
comment on column public.evaluations.id is 'Identifiant de l''évaluation.';
comment on column public.evaluations.cree_le is 'Date et heure.';
comment on column public.evaluations.utilisateur is 'Le testeur concerné (celui qui a ouvert le dossier, ou qui note).';
comment on column public.evaluations.document is 'La version du document évaluée.';
comment on column public.evaluations.auteur is 'Qui évalue : ia ou humain.';
comment on column public.evaluations.appel_llm is 'Pour une évaluation de l''IA, l''appel enregistré dans appels_llm.';
comment on column public.evaluations.mesures is 'JSON : les mesures fixes calculées sur le texte (évaluation de l''IA uniquement). Format : SCHEMA.md §5.3 ; CADRAGE.md §2.5.';
comment on column public.evaluations.notes is 'JSON : une note de 1 à 5 pour chacune des cinq dimensions (organisation, langage, cohérence médicale, synthèse, qualité générale). Format : SCHEMA.md §5.3.';
comment on column public.evaluations.verdict is 'Pour l''IA : exploitable, douteux ou non_exploitable.';
comment on column public.evaluations.commentaire is 'La raison du verdict (IA) ou le commentaire libre (testeur).';
comment on column public.evaluations.poursuite is 'Pour l''IA : le testeur a-t-il choisi de coder le document malgré l''avertissement ?';
