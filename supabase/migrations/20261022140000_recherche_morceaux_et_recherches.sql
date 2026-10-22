-- Migration 16 : (1) recherche de codes « par morceaux de mots » pour la recherche 🔍 de la page ;
-- (2) table recherches : journal des recherches des testeurs (texte tapé, résultats, code choisi) pour alimenter
-- plus tard un dictionnaire de synonymes. Insertion par le testeur, aucune relecture (SCHEMA.md §7, règle « jamais relu »).

-- ---------------------------------------------------------------- (1) rechercher_codes_morceaux
-- Le texte tapé est normalisé (minuscules, sans accents) et découpé en morceaux (espaces). On garde les formulations
-- qui contiennent TOUS les morceaux, n'importe où (LIKE '%m%' pour chaque morceau : l'index trigrammes de
-- synonymes.formulation_normalisee est utilisé). Classement, par code codable (un résultat par code, sa meilleure
-- formulation) : 1. les codes dont le libellé officiel contient tous les morceaux ; 2. ceux qui ne les ont que dans une
-- autre formulation ; puis 3. les morceaux trouvés en début de mot ; puis 4. les formulations les plus courtes.
-- Décision du 22 octobre : ordre 1. morceaux en début de mot, 2. libellé officiel, 3. autre formulation, 4. la plus courte ;
-- un morceau de trois lettres ou moins (abréviation : HTA, IDM, FA) ne compte qu'en début de mot.
-- La requête est construite à l'exécution (une condition LIKE par morceau), les morceaux étant passés en littéraux
-- protégés (format %L). Droits de l'appelant ; chemin de recherche vide, noms complets.
create or replace function public.rechercher_codes_morceaux(recherche text, limite integer default 40)
returns table (code text, libelle text, formulation text, dans_libelle boolean, debut_mot boolean)
language plpgsql
stable
set search_path = ''
as $$
declare
  morceaux text[];
  conds text := 'true';
  debuts text := 'true';
  m text;
begin
  morceaux := pg_catalog.regexp_split_to_array(pg_catalog.btrim(public.normaliser_texte(recherche)), '\s+');
  morceaux := pg_catalog.array_remove(morceaux, '');
  if morceaux is null or pg_catalog.array_length(morceaux, 1) is null then
    return;
  end if;
  foreach m in array morceaux loop
    if pg_catalog.length(m) <= 3 then
      -- abréviation : seulement en début de mot (le LIKE sert à l'index, le motif à la frontière de mot)
      conds := conds || pg_catalog.format(' and s.formulation_normalisee like %L and s.formulation_normalisee ~ %L', '%' || m || '%',
                                          '(^|[^a-z0-9])' || pg_catalog.regexp_replace(m, '([.^$*+?()\[\]{}|\\])', '\\\1', 'g'));
    else
      conds := conds || pg_catalog.format(' and s.formulation_normalisee like %L', '%' || m || '%');
    end if;
    debuts := debuts || pg_catalog.format(' and s.formulation_normalisee ~ %L', '(^|[^a-z0-9])' || pg_catalog.regexp_replace(m, '([.^$*+?()\[\]{}|\\])', '\\\1', 'g'));
  end loop;
  return query execute pg_catalog.format(
    'with lignes as (
       select s.code, s.formulation, (s.origine = ''libelle'') as dans_libelle, (%s) as debut_mot,
              pg_catalog.length(s.formulation_normalisee) as longueur
       from public.synonymes s where %s),
     meilleur as (select distinct on (l.code) l.* from lignes l order by l.code, l.debut_mot desc, l.dans_libelle desc, l.longueur)
     select b.code, f.libelle, b.formulation, b.dans_libelle, b.debut_mot
     from meilleur b join public.fiches f on f.code = b.code
     where f.codable
     order by b.debut_mot desc, b.dans_libelle desc, b.longueur, b.code
     limit %s', debuts, conds, pg_catalog.greatest(1, pg_catalog.least(coalesce(limite, 40), 200)));
end;
$$;
comment on function public.rechercher_codes_morceaux(text, integer) is
  'Recherche 🔍 de la page : codes codables dont une formulation contient tous les morceaux du texte tapé (accents et casse ignorés), un résultat par code ; classés : morceaux en début de mot d''abord, puis libellé officiel, puis autre formulation, puis formulation la plus courte ; un morceau de trois lettres ou moins ne compte qu''en début de mot. Au plus `limite` codes (200 maximum).';
revoke all on function public.rechercher_codes_morceaux(text, integer) from public, anon;
grant execute on function public.rechercher_codes_morceaux(text, integer) to authenticated;

-- ---------------------------------------------------------------- (2) recherches
create table public.recherches (
  id           bigint generated always as identity primary key,
  cree_le      timestamptz not null default now(),
  utilisateur  uuid not null references auth.users (id),
  document     bigint references public.documents (id),
  texte        text not null,
  mode         text not null check (mode in ('morceaux', 'ressemblance', 'code')),
  nb_resultats integer not null,
  code_choisi  text,
  contexte     text
);
comment on table  public.recherches is 'Journal des recherches de codes faites par les testeurs dans la page (🔍, nouveau code, code à choisir), pour alimenter plus tard un dictionnaire de synonymes. Insertion par le testeur, jamais relu par lui.';
comment on column public.recherches.id is 'Identifiant de la ligne.';
comment on column public.recherches.cree_le is 'Date et heure de la recherche.';
comment on column public.recherches.utilisateur is 'Le testeur.';
comment on column public.recherches.document is 'Le document ouvert au moment de la recherche (vide si hors dossier).';
comment on column public.recherches.texte is 'Le texte tapé.';
comment on column public.recherches.mode is 'Mode ayant donné les résultats : morceaux, ressemblance (secours), code (début de code).';
comment on column public.recherches.nb_resultats is 'Nombre de codes proposés.';
comment on column public.recherches.code_choisi is 'Le code choisi par le testeur, ou vide si aucun.';
comment on column public.recherches.contexte is 'D''où vient la recherche : changement de code, nouveau code, code à choisir.';
create index recherches_utilisateur_idx on public.recherches (utilisateur, cree_le);
alter table public.recherches enable row level security;
grant insert on public.recherches to authenticated;
create policy "recherches : ajout de ses propres lignes"
  on public.recherches for insert to authenticated with check (utilisateur = (select auth.uid()));
