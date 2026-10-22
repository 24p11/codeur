-- Migration 15 : corrige rechercher_codes (migration 14) : avec search_path vide, l'opérateur de ressemblance % de
-- pg_trgm doit être qualifié par son schéma : operator(extensions.%). Ajoute le seuil de ressemblance en paramètre :
-- 0,15 pour la boucle de correction (le rappel compte), 0,3 pour la recherche de la page pendant la frappe (vitesse).
drop function if exists public.rechercher_codes(text, integer);
create or replace function public.rechercher_codes(recherche text, limite integer default 60, seuil real default 0.3)
returns table (code text, libelle text, formulation text, score real)
language plpgsql
stable
set search_path = ''
as $$
begin
  perform pg_catalog.set_config('pg_trgm.similarity_threshold', greatest(0.05, least(coalesce(seuil, 0.3), 1.0))::text, true);
  return query
  with q as (select public.normaliser_texte(recherche) as t),
  candidats as (
    select s.code, s.formulation, extensions.similarity(s.formulation_normalisee, q.t) as score
    from public.synonymes s, q
    where s.formulation_normalisee operator(extensions.%) q.t
  ),
  meilleur as (
    select distinct on (c.code) c.code, c.formulation, c.score
    from candidats c
    order by c.code, c.score desc
  )
  select m.code, f.libelle, m.formulation, m.score
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
