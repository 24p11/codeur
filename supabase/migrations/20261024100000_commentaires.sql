-- Migration 24 : table `commentaires` (brief 8, suite du 24 octobre 2026).
-- Les commentaires quittent le JSON du codage (qui les recopiait à chaque ligne) pour une table : un commentaire est rattaché
-- au document et, s'il porte sur un code, au code lui-même (pas d'identifiant nouveau pour les codes) ; des fils de discussion
-- sont possibles (reponse_a). Insertion seulement : ni modification ni suppression ; un commentaire se retire par une ligne de
-- type « retrait » qui lui répond. Les explications de l'IA (codes, mode de prise en charge) sont des commentaires.
create table public.commentaires (
  id           bigint generated always as identity primary key,
  cree_le      timestamptz not null default now(),
  document     bigint not null references public.documents (id),
  utilisateur  uuid not null references auth.users (id),
  objet        text not null check (objet in ('sejour', 'code', 'mode_prise_en_charge', 'regle')),
  code         text,
  auteur       text not null check (auteur in ('humain', 'ia', 'outil')),
  type         text not null check (type in ('explication', 'remarque', 'discussion', 'alerte', 'retrait')),
  codage       bigint references public.codages (id),
  appel_llm    uuid references public.appels_llm (id),
  reponse_a    bigint references public.commentaires (id),
  texte        text not null,
  constraint commentaires_code_coherent check ((objet = 'sejour') = (code is null)),
  constraint commentaires_retrait_repond check (type <> 'retrait' or reponse_a is not null),
  constraint commentaires_explication_ia_appel check (not (auteur = 'ia' and type = 'explication') or appel_llm is not null)
);
comment on table  public.commentaires is 'Les commentaires sur un travail de codage : sur le séjour, sur un code, sur le mode de prise en charge ou sur la règle ; écrits par le testeur, par l''IA (explications) ou par l''outil (alertes). Insertion seulement ; un retrait est une ligne de type retrait qui répond au commentaire retiré.';
comment on column public.commentaires.document is 'La version du document concernée.';
comment on column public.commentaires.utilisateur is 'Le testeur dont c''est le travail (aussi pour les commentaires de l''IA et de l''outil écrits pendant son travail).';
comment on column public.commentaires.objet is 'sejour (le dossier entier), code (un code CIM du codage), mode_prise_en_charge, regle.';
comment on column public.commentaires.code is 'Le code CIM concerné (forme codeur) ; pour le mode de prise en charge, DP ou le code Z ; pour la règle, son code (T3, S1-Chronic) ; vide pour le séjour. Pour un code à choisir, le code proposé par l''IA (code_propose_non_codable), ou le séjour s''il n''y en a pas. Un commentaire reste attaché au code sur lequel il a été écrit.';
comment on column public.commentaires.auteur is 'humain, ia ou outil.';
comment on column public.commentaires.type is 'explication (de l''IA), remarque (du testeur), discussion (réponse dans un fil), alerte (de l''outil), retrait (retire le commentaire désigné par reponse_a).';
comment on column public.commentaires.codage is 'La ligne de codage au moment de laquelle le commentaire est écrit (vide si aucune).';
comment on column public.commentaires.appel_llm is 'Pour un commentaire de l''IA, l''appel dont il vient ; obligatoire pour une explication de l''IA (contrainte), pour la confronter à l''appel réel.';
comment on column public.commentaires.reponse_a is 'Le commentaire auquel celui-ci répond (fil de discussion), ou celui qu''il retire (type retrait).';
comment on column public.commentaires.texte is 'Le texte du commentaire ; pour un retrait, le motif ou « retiré ».';
create index commentaires_document_utilisateur_idx on public.commentaires (document, utilisateur);
create index commentaires_codage_idx on public.commentaires (codage);
create index commentaires_reponse_a_idx on public.commentaires (reponse_a);

alter table public.commentaires enable row level security;
revoke all on public.commentaires from public, anon, authenticated;
grant select, insert on public.commentaires to authenticated;
-- Un testeur lit les commentaires de son travail (les siens, ceux de l'IA et de l'outil écrits pendant son travail).
create policy "commentaires : lecture de son travail"
  on public.commentaires for select to authenticated using (utilisateur = (select auth.uid()));
-- Il ajoute des commentaires à son travail ; un retrait ne peut viser qu'un de ses propres commentaires d'auteur humain.
create policy "commentaires : ajout sur son travail"
  on public.commentaires for insert to authenticated
  with check (utilisateur = (select auth.uid())
              and (type <> 'retrait' or exists (select 1 from public.commentaires c
                                                 where c.id = reponse_a and c.utilisateur = (select auth.uid()) and c.auteur = 'humain')));
