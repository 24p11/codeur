-- Migration 14 : fonction de recherche de codes par ressemblance avec un texte (trigrammes), pour la boucle de
-- correction (candidats « dont une formulation ressemble au libellé du modèle », SCHEMA.md §3.10) et pour la
-- recherche 🔍 de la page. Lue avec les droits de l'appelant (security invoker) : un testeur ne lit que ce que les
-- règles de synonymes et fiches lui permettent (tout, en lecture).
-- Le seuil de ressemblance (pg_trgm.similarity_threshold, 0,3 par défaut) est abaissé à 0,15 pour la durée de l'appel
-- par set_config(..., true) : le rôle des migrations ne peut pas le fixer dans la définition de la fonction, mais
-- l'opérateur % reste indexé (index trigrammes de synonymes.formulation_normalisee).
create or replace function public.rechercher_codes(recherche text, limite integer default 60)
returns table (code text, libelle text, formulation text, score real)
language plpgsql
stable
set search_path = ''
as $$
begin
  perform pg_catalog.set_config('pg_trgm.similarity_threshold', '0.15', true);
  return query
  with q as (select public.normaliser_texte(recherche) as t),
  candidats as (
    select s.code, s.formulation, extensions.similarity(s.formulation_normalisee, q.t) as score
    from public.synonymes s, q
    where s.formulation_normalisee % q.t
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
comment on function public.rechercher_codes(text, integer) is
  'Codes codables dont une formulation (synonymes) ressemble au texte donné, classés par ressemblance décroissante (trigrammes, accents et casse ignorés, seuil 0,15), un résultat par code avec sa meilleure formulation. Sert à la boucle de correction et à la recherche de la page. Au plus `limite` codes (200 maximum).';
revoke all on function public.rechercher_codes(text, integer) from public, anon;
grant execute on function public.rechercher_codes(text, integer) to authenticated;
