-- Migration 18 : les deux fonctions de recherche renvoient aussi la source et l'origine de la formulation affichée
-- (infobulle de la page : « CepiDc 2015, synonyme », « CIM-10 index, index », « ATIH kit 2025, libelle »…).
-- Définitions identiques pour le reste (migrations 15 et 17).

drop function if exists public.rechercher_codes(text, integer, real);
create or replace function public.rechercher_codes(recherche text, limite integer default 60, seuil real default 0.3)
returns table (code text, libelle text, formulation text, score real, source text, origine text)
language plpgsql
stable
set search_path = ''
as $$
begin
  perform pg_catalog.set_config('pg_trgm.similarity_threshold', greatest(0.05, least(coalesce(seuil, 0.3), 1.0))::text, true);
  return query
  with q as (select public.normaliser_texte(recherche) as t),
  candidats as (
    select s.code, s.formulation, s.source, s.origine, extensions.similarity(s.formulation_normalisee, q.t) as score
    from public.synonymes s, q
    where s.formulation_normalisee operator(extensions.%) q.t
  ),
  meilleur as (
    select distinct on (c.code) c.code, c.formulation, c.score, c.source, c.origine
    from candidats c
    order by c.code, c.score desc
  )
  select m.code, f.libelle, m.formulation, m.score, m.source, m.origine
  from meilleur m join public.fiches f on f.code = m.code
  where f.codable
  order by m.score desc, m.code
  limit greatest(1, least(coalesce(limite, 60), 200));
end;
$$;
comment on function public.rechercher_codes(text, integer, real) is
  'Codes codables dont une formulation (synonymes) ressemble au texte donné, classés par ressemblance décroissante (trigrammes, accents et casse ignorés), un résultat par code avec sa meilleure formulation. `seuil` : 0,15 pour la boucle de correction, 0,3 pour la recherche de la page. Au plus `limite` codes (200 maximum).';
revoke all on function public.rechercher_codes(text, integer, real) from public, anon;
grant execute on function public.rechercher_codes(text, integer, real) to authenticated;

drop function if exists public.rechercher_codes_morceaux(text, integer);
create function public.rechercher_codes_morceaux(recherche text, limite integer default 40)
returns table (code text, libelle text, formulation text, dans_libelle boolean, debut_mot boolean, mot_entier boolean, source text, origine text)
language plpgsql
stable
set search_path = ''
as $$
declare
  morceaux text[];
  conds text := 'true';
  debuts text := 'true';
  entiers text := 'true';
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
    entiers := entiers || pg_catalog.format(' and s.formulation_normalisee ~ %L', '(^|[^a-z0-9])' || pg_catalog.regexp_replace(m, '([.^$*+?()\[\]{}|\\])', '\\\1', 'g') || '($|[^a-z0-9])');
  end loop;
  return query execute pg_catalog.format(
    'with lignes as (
       select s.code, s.formulation, s.source, s.origine, (s.origine = ''libelle'') as dans_libelle, (%s) as debut_mot, (%s) as mot_entier,
              pg_catalog.length(s.formulation_normalisee) as longueur
       from public.synonymes s where %s),
     meilleur as (select distinct on (l.code) l.* from lignes l order by l.code, l.mot_entier desc, l.debut_mot desc, l.dans_libelle desc, l.longueur)
     select b.code, f.libelle, b.formulation, b.dans_libelle, b.debut_mot, b.mot_entier, b.source, b.origine
     from meilleur b join public.fiches f on f.code = b.code
     where f.codable
     order by b.mot_entier desc, b.debut_mot desc, b.dans_libelle desc, b.longueur, b.code
     limit %s', debuts, entiers, conds, greatest(1, least(coalesce(limite, 40), 200)));
end;
$$;
comment on function public.rechercher_codes_morceaux(text, integer) is
  'Recherche 🔍 de la page : codes codables dont une formulation contient tous les morceaux du texte tapé (accents et casse ignorés), un résultat par code ; classés : morceaux trouvés comme mots entiers d''abord, puis en début de mot, puis libellé officiel, puis autre formulation, puis formulation la plus courte ; un morceau de trois lettres ou moins ne compte qu''en début de mot. Au plus `limite` codes (200 maximum).';
revoke all on function public.rechercher_codes_morceaux(text, integer) from public, anon;
grant execute on function public.rechercher_codes_morceaux(text, integer) to authenticated;
