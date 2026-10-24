-- Migration 23 : fonction regles_compatibles(code) (brief 8, étape 4).
-- À partir de la pathologie principale (forme codeur, ou null : aucune pathologie principale), renvoie les lignes du guide des
-- situations cliniques compatibles, avec le motif : « aucune pathologie principale » (colonne Pathologie « Aucun »), le chapitre
-- de la pathologie, un intervalle de codes, un code (préfixe), ou une liste de listes_codes (code exact ou catégorie de la liste).
-- Les règles non évaluables (T10-irradiations) ne sont jamais renvoyées. La page l'appelle au lieu de charger les listes
-- (plafond de 1 000 lignes, SCHEMA.md §10 point 28). Droits de l'appelant, chemin de recherche fixé, testeurs connectés.
create or replace function public.regles_compatibles(code text default null)
returns table (regle text, regle_officielle text, famille text, type text, libelle text, specificite text,
               pathologie text, code_z text, motif text, details jsonb)
language sql
stable
set search_path = ''
as $$
  with pp as (
    select nullif(upper(regexp_replace(coalesce(code, ''), '[^A-Za-z0-9+]', '', 'g')), '') as c
  ),
  chap as (
    select ch.numero
    from public.chapitres ch, pp
    where pp.c is not null and left(pp.c, 3) between ch.premier_code and ch.dernier_code
  ),
  motifs as (
    select r.code as regle,
      case
        when pp.c is null and (r.details -> 'pathologie' ->> 'aucun')::boolean then 'aucune pathologie principale'
        when pp.c is not null then coalesce(
          (select 'chapitre ' || chap.numero from chap where r.details -> 'pathologie' -> 'chapitres' ? chap.numero limit 1),
          (select 'intervalle ' || (iv ->> 0) || '-' || (iv ->> 1) from jsonb_array_elements(r.details -> 'pathologie' -> 'intervalles') iv
             where left(pp.c, 3) between (iv ->> 0) and (iv ->> 1) limit 1),
          (select 'code ' || k from jsonb_array_elements_text(r.details -> 'pathologie' -> 'codes') k where pp.c like k || '%' limit 1),
          (select 'liste ' || l from jsonb_array_elements_text(r.details -> 'pathologie' -> 'listes') l
             join public.listes_codes lc on lc.liste = l and lc.nature = 'cim'
             where pp.c = lc.code or pp.c like lc.code || '%' limit 1))
      end as motif
    from public.regles_situations r, pp
    where r.evaluable
  )
  select r.code, r.regle_officielle, r.famille, r.type, r.libelle, r.specificite, r.pathologie, r.code_z, m.motif, r.details
  from public.regles_situations r
  join motifs m on m.regle = r.code
  where m.motif is not null
  order by r.type, r.code;
$$;

comment on function public.regles_compatibles(text) is
  'Les lignes du guide des situations cliniques compatibles avec la pathologie principale donnée (forme codeur ; null = aucune pathologie principale), avec le motif de compatibilité (chapitre, intervalle, code, liste, ou absence de pathologie). Règles non évaluables exclues. Droits de l''appelant, chemin de recherche fixé.';

revoke all on function public.regles_compatibles(text) from public, anon;
grant execute on function public.regles_compatibles(text) to authenticated;
