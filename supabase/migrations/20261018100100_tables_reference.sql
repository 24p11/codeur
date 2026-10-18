-- Migration 2 : les tables de référence (docs/SCHEMA.md §2 et §6).
-- Chargées par les scripts Python avec la clé secrète ; les testeurs les lisent seulement.

-- ---------------------------------------------------------------- lots
create table public.lots (
  id               text primary key,
  source           text not null,
  version          text not null,
  description      text,
  contenu          jsonb not null default '{}'::jsonb,
  regles_nettoyage jsonb not null default '[]'::jsonb,
  charge_le        timestamptz not null default now()
);
comment on table  public.lots is 'Chaque lot de documents chargé dans la base (SCHEMA.md §6).';
comment on column public.lots.id is 'Identifiant du lot, par exemple « parhaf-1.0.0 » ; référencé par documents.lot.';
comment on column public.lots.source is 'Origine du lot : PARHAF (Hugging Face), CRH synthétiques (Google Drive)…';
comment on column public.lots.version is 'Version de la source, par exemple « 1.0.0 » ou « run08 du 7 octobre 2026 ».';
comment on column public.lots.description is 'Description en français du lot.';
comment on column public.lots.contenu is 'JSON : ce que le lot fournit (texte seul, DP, DAS, règle, code Z, preuves…). Format : SCHEMA.md §6.';
comment on column public.lots.regles_nettoyage is 'JSON : les règles de nettoyage appliquées au chargement (inventaire_corpus.md §1.6 et §2.5).';
comment on column public.lots.charge_le is 'Date et heure du chargement.';

-- ---------------------------------------------------------------- documents
create table public.documents (
  id                   bigint generated always as identity primary key,
  lot                  text not null references public.lots (id),
  id_source            text not null,
  version              integer not null default 1 check (version >= 1),
  version_precedente   bigint references public.documents (id),
  motif_version        text,
  specialite           text,
  type_prise_en_charge text,
  texte                text not null,
  empreinte            text not null generated always as (public.empreinte_texte(texte)) stored,
  nettoyage            jsonb,
  cree_le              timestamptz not null default now(),
  cree_par             uuid references auth.users (id),
  constraint documents_lot_id_source_version_unique unique (lot, id_source, version),
  constraint documents_version_precedente_coherente check (
    (version = 1 and version_precedente is null) or (version > 1 and version_precedente is not null)
  )
);
comment on table  public.documents is 'Une ligne = une version d''un texte à coder. Le texte est figé : corriger crée une nouvelle version (SCHEMA.md §2).';
comment on column public.documents.id is 'Identifiant interne, attribué par la base.';
comment on column public.documents.lot is 'Le lot d''origine (table lots).';
comment on column public.documents.id_source is 'Identifiant du document dans sa source, pour retrouver l''original (ex. CARDIOLOGIE-00133).';
comment on column public.documents.version is 'Numéro de version du texte : 1, puis 2 après une correction.';
comment on column public.documents.version_precedente is 'La ligne dont cette version est issue ; vide pour la version 1.';
comment on column public.documents.motif_version is 'La raison de la correction (ex. « codes recopiés dans le corps du texte »).';
comment on column public.documents.specialite is 'Spécialité médicale, pour rechercher les dossiers.';
comment on column public.documents.type_prise_en_charge is 'Type de prise en charge, valeur brute de la source, pour rechercher les dossiers.';
comment on column public.documents.texte is 'Le texte de référence, nettoyé et figé. Toutes les positions des preuves s''y rapportent. Intitulés et markdown inclus (SCHEMA.md §2).';
comment on column public.documents.empreinte is 'SHA-256 du texte (hexadécimal), calculé automatiquement : permet de vérifier que le texte n''a jamais changé.';
comment on column public.documents.nettoyage is 'JSON : passages retirés au chargement (règle, position dans le texte d''origine) et anomalies signalées. Jamais affiché. Format : SCHEMA.md §2.';
comment on column public.documents.cree_le is 'Date et heure de création de cette version.';
comment on column public.documents.cree_par is 'Auteur de cette version (compte utilisateur) ; vide quand c''est le script de chargement.';

-- Le texte d''une ligne ne doit jamais être modifié (SCHEMA.md §1 et §2) : la base le refuse, quel que soit le rôle.
create or replace function public.refuser_modification_texte()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if new.texte is distinct from old.texte then
    raise exception 'Le texte d''un document est figé : créer une nouvelle version (SCHEMA.md §2).';
  end if;
  return new;
end;
$$;
comment on function public.refuser_modification_texte() is 'Déclencheur : interdit toute modification de documents.texte.';

create trigger documents_texte_fige
  before update on public.documents
  for each row execute function public.refuser_modification_texte();

-- ---------------------------------------------------------------- fiches
create table public.fiches (
  code              text primary key,
  libelle           text not null,
  codable           boolean not null,
  contenu           text,
  version_livraison text not null,
  charge_le         timestamptz not null default now()
);
comment on table  public.fiches is 'Tout l''index des codes CIM-10 de recode-icd, codes non codables compris, avec la fiche d''identité quand elle existe. Une seule livraison chargée à la fois. La liste des codes codables est tirée de cette table (SCHEMA.md §6 et §3.9).';
comment on column public.fiches.code is 'Code complet, sans point, extension PMSI collée (ex. K409, I5009, K635+0, E11ni).';
comment on column public.fiches.libelle is 'Libellé officiel du code.';
comment on column public.fiches.codable is 'Vrai si le code peut figurer dans un RUM ; faux pour une catégorie ou un code non terminal.';
comment on column public.fiches.contenu is 'Contenu de la fiche d''identité (texte) ; vide pour un code sans fiche. Format : contrat d''interface recode-icd.';
comment on column public.fiches.version_livraison is 'Version de la livraison recode-icd dont la fiche est issue.';
comment on column public.fiches.charge_le is 'Date et heure du chargement.';

-- ---------------------------------------------------------------- synonymes
create table public.synonymes (
  id                     bigint generated always as identity primary key,
  code                   text not null references public.fiches (code),
  formulation            text not null,
  origine                text not null check (origine in ('libelle', 'inclusion', 'index', 'synonyme')),
  source                 text not null,
  formulation_normalisee text not null generated always as (public.normaliser_texte(formulation)) stored
);
comment on table  public.synonymes is 'Les formulations associées à chaque code, pour la recherche par mots (SCHEMA.md §6 ; CADRAGE.md §4.5).';
comment on column public.synonymes.id is 'Identifiant de la ligne.';
comment on column public.synonymes.code is 'Le code CIM-10 (table fiches).';
comment on column public.synonymes.formulation is 'La formulation telle qu''elle sera affichée.';
comment on column public.synonymes.origine is 'Type de formulation : libelle, inclusion, index ou synonyme.';
comment on column public.synonymes.source is 'Provenance de la formulation : CépiDc, AP-HP, LLM…';
comment on column public.synonymes.formulation_normalisee is 'Formulation en minuscules sans accents, calculée automatiquement ; c''est elle qui est indexée pour la recherche.';

-- ---------------------------------------------------------------- regles_situations
create table public.regles_situations (
  code        text primary key,
  famille     text,
  libelle     text,
  type        text,
  specificite text,
  pathologie  text,
  code_z      text,
  details     jsonb,
  version     text
);
comment on table  public.regles_situations is 'Le guide des situations cliniques, une ligne par règle de hiérarchisation (SCHEMA.md §6 ; CADRAGE.md §4.4 et §7).';
comment on column public.regles_situations.code is 'Code de la règle : D1, T3, S1-Chronic… (valeur de codage.regle_hierarchisation).';
comment on column public.regles_situations.famille is 'Famille de la règle, tirée de la colonne « Type d''hospitalisation » du guide au chargement (D diagnostic, T traitement, S surveillance…). Pas déduite du code : contre-exemples « Règle IVG », « Règle ITG ».';
comment on column public.regles_situations.libelle is 'Intitulé de la règle.';
comment on column public.regles_situations.type is 'Type de situation, tel que défini par le guide.';
comment on column public.regles_situations.specificite is 'Spécificité de la règle, telle que définie par le guide.';
comment on column public.regles_situations.pathologie is 'Pathologie ou liste de pathologies concernées.';
comment on column public.regles_situations.code_z is 'Code Z de prise en charge associé, le cas échéant.';
comment on column public.regles_situations.details is 'JSON : le reste du contenu de la règle, tel que fourni par le guide corrigé.';
comment on column public.regles_situations.version is 'Version du guide dont la règle est issue.';
