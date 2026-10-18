-- Migration 1 : extensions et fonctions utilitaires.
-- Référence : docs/SCHEMA.md §2 (empreinte du texte) et §6/§8 (recherche dans les synonymes).

-- unaccent : retire les accents ; pg_trgm : recherche par trigrammes, tolérante aux fautes de frappe.
-- Sur Supabase, les extensions sont installées dans le schéma « extensions ».
create extension if not exists unaccent with schema extensions;
create extension if not exists pg_trgm with schema extensions;

-- PostgreSQL ne déclare pas unaccent() comme « immutable » ; cette enveloppe le fait,
-- ce qui permet de l'utiliser dans une colonne calculée et dans un index.
create or replace function public.normaliser_texte(texte text)
returns text
language sql
immutable
parallel safe
set search_path = ''
as $$
  select lower(extensions.unaccent('extensions.unaccent'::regdictionary, coalesce(texte, '')));
$$;
comment on function public.normaliser_texte(text) is
  'Met en minuscules et retire les accents. Sert à la recherche dans la table des synonymes (SCHEMA.md §6).';

-- Empreinte SHA-256 d'un texte, en hexadécimal. convert_to() n'est pas « immutable » aux yeux de PostgreSQL
-- (elle dépend de l'encodage du serveur, qui est fixé à UTF-8) ; cette enveloppe permet une colonne calculée.
create or replace function public.empreinte_texte(texte text)
returns text
language sql
immutable
parallel safe
set search_path = ''
as $$
  select encode(sha256(convert_to(texte, 'UTF8')), 'hex');
$$;
comment on function public.empreinte_texte(text) is
  'Empreinte SHA-256 (hexadécimal) du texte, calculée automatiquement pour la colonne documents.empreinte (SCHEMA.md §2).';
