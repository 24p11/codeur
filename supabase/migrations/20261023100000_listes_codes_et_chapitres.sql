-- Migration 21 : tables de référence `listes_codes` et `chapitres` (brief 8, étape 1).
-- Les fichiers du dépôt (docs/referentiels/cim/listes_codes/*.csv, docs/referentiels/cim/chapitres.csv) restent la source ;
-- la base en reçoit une copie chargée par scripts/chargement/listes_charger.py (rechargeable sans doublon).
-- Droits : lecture seule pour les testeurs connectés, rien pour les visiteurs (règle de docs/base_de_donnees.md : aucun droit
-- par défaut, droits explicites) ; écriture par les scripts (clé secrète) seulement.

-- ---------------------------------------------------------------- listes_codes
create table public.listes_codes (
  liste      text not null,
  nature     text not null check (nature in ('cim', 'ccam')),
  code       text not null,
  libelle    text,
  source     text,
  version    text,
  charge_le  timestamptz not null default now(),
  constraint listes_codes_pkey primary key (liste, code)
);
comment on table  public.listes_codes is 'Les listes de codes citées par le guide des situations cliniques (et les listes à venir) : une ligne par code et par liste. Copie des fichiers docs/referentiels/cim/listes_codes/ (nature cim) et docs/referentiels/ccam/listes_actes/ (nature ccam), qui restent la source.';
comment on column public.listes_codes.liste is 'Nom de la liste : le nom du fichier sans extension (par exemple icd_codes_legal_abortion).';
comment on column public.listes_codes.nature is 'cim (code CIM-10, forme codeur, contrôlé contre fiches) ou ccam (acte).';
comment on column public.listes_codes.code is 'Le code. Pour la CIM, une catégorie sans subdivision (Z95) désigne la catégorie et ses descendants codables.';
comment on column public.listes_codes.libelle is 'Libellé officiel (index recode-icd pour la CIM).';
comment on column public.listes_codes.source is 'Provenance de la liste (par exemple projet Stream).';
comment on column public.listes_codes.version is 'Version du fichier chargé (date ou commit).';
comment on column public.listes_codes.charge_le is 'Date du chargement ou du dernier rechargement de la ligne.';
create index listes_codes_code_idx on public.listes_codes (code);

alter table public.listes_codes enable row level security;
revoke all on public.listes_codes from public, anon, authenticated;
grant select on public.listes_codes to authenticated;
create policy "listes_codes : lecture par les testeurs"
  on public.listes_codes for select to authenticated using (true);

-- ---------------------------------------------------------------- chapitres
create table public.chapitres (
  numero        text primary key,
  ordre         integer not null unique,
  intitule      text not null,
  premier_code  text not null,
  dernier_code  text not null
);
comment on table  public.chapitres is 'Les 22 chapitres de la CIM-10 : numéro romain, ordre, intitulé, premier et dernier code (catégories à trois caractères). Copie de docs/referentiels/cim/chapitres.csv ; sert à lire « chapitres I à XVII » dans le guide des situations cliniques (fonction regles_compatibles).';
comment on column public.chapitres.numero is 'Numéro romain du chapitre (I à XXII).';
comment on column public.chapitres.ordre is 'Rang du chapitre (1 à 22).';
comment on column public.chapitres.intitule is 'Intitulé officiel du chapitre.';
comment on column public.chapitres.premier_code is 'Première catégorie du chapitre (par exemple C00).';
comment on column public.chapitres.dernier_code is 'Dernière catégorie du chapitre (par exemple D48).';

alter table public.chapitres enable row level security;
revoke all on public.chapitres from public, anon, authenticated;
grant select on public.chapitres to authenticated;
create policy "chapitres : lecture par les testeurs"
  on public.chapitres for select to authenticated using (true);
