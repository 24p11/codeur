-- Migration 12 : préparation du chargement de la livraison recode-icd (lot B3, partie index et formulations).
-- Référence : docs/SCHEMA.md §6 et §10 (points 9, 10, 16) ; docs/referentiels/README.md.

-- ---------------------------------------------------------------- fiches : statuts MCO
alter table public.fiches
  add column statut_mco   text,
  add column interdit_dp  boolean,
  add column interdit_dr  boolean,
  add column interdit_das boolean;
comment on column public.fiches.statut_mco is 'Statut d''autorisation au kit ATIH (codable, cause_externe, pere_interdit, interdit_dp_dr, interdit_dp, supprime), tel que livré par recode-icd (codes.csv).';
comment on column public.fiches.interdit_dp is 'Vrai si le code est interdit en diagnostic principal (kit ATIH).';
comment on column public.fiches.interdit_dr is 'Vrai si le code est interdit en diagnostic relié (kit ATIH).';
comment on column public.fiches.interdit_das is 'Vrai si le code est interdit en diagnostic associé (kit ATIH) ; équivaut à « non codable ».';
-- Lecture de fiches : droit de table (toutes colonnes) déjà accordé aux testeurs ; les nouvelles colonnes en héritent.

-- ---------------------------------------------------------------- synonymes : version de la livraison, unicité
alter table public.synonymes add column version_livraison text;
comment on column public.synonymes.version_livraison is 'Version de la livraison recode-icd dont la formulation est issue (ex. 65701d6_atih-2025).';
alter table public.synonymes add constraint synonymes_code_formulation_source_unique unique (code, formulation, source);

-- ---------------------------------------------------------------- descendants_codables
create table public.descendants_codables (
  noeud             text not null references public.fiches (code),
  code              text not null references public.fiches (code),
  libelle           text not null,
  ordre_kit         integer not null,
  version_livraison text not null,
  constraint descendants_codables_pkey primary key (noeud, code)
);
comment on table  public.descendants_codables is 'Pour un code (nœud) proposé non codable ou codable mais moins précis, ses descendants codables dans l''ordre du kit ATIH : la matière de la boucle de correction et de l''affinage (SCHEMA.md §3.10). Livré par recode-icd (descendants_codables.csv).';
comment on column public.descendants_codables.noeud is 'Le code de départ (forme codeur, sans point).';
comment on column public.descendants_codables.code is 'Un descendant codable du nœud (forme codeur).';
comment on column public.descendants_codables.libelle is 'Libellé officiel du descendant.';
comment on column public.descendants_codables.ordre_kit is 'Rang du descendant dans le kit ATIH (ordre d''affichage).';
comment on column public.descendants_codables.version_livraison is 'Version de la livraison recode-icd.';
create index descendants_codables_code_idx on public.descendants_codables (code);

-- Droits : lecture seule pour les testeurs connectés, rien pour les visiteurs ; chargement par les scripts (clé secrète).
alter table public.descendants_codables enable row level security;
grant select on public.descendants_codables to authenticated;
create policy "descendants_codables : lecture par les testeurs"
  on public.descendants_codables for select to authenticated using (true);
