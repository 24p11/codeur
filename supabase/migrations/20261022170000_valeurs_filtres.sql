-- Migration 19 : fonction valeurs_filtres() pour les listes de filtre de la page (lot B2, suite).
-- La page construisait ses listes (spécialité, type de prise en charge) en lisant toutes les lignes de
-- dossiers_disponibles ; PostgREST en renvoie au plus 1 000, et la base en compte 4 322. La fonction renvoie
-- les valeurs distinctes et leur effectif, par lot, en une seule requête courte.
-- Droits de l'appelant (security invoker, par défaut) : la vue dossiers_disponibles est elle-même en
-- security_invoker, les règles de lecture de documents s'appliquent donc au testeur connecté.
create or replace function public.valeurs_filtres()
returns table (lot text, specialite text, type_prise_en_charge text, nb bigint)
language sql
stable
set search_path = ''
as $$
  select d.lot, d.specialite, d.type_prise_en_charge, count(*)
  from public.dossiers_disponibles d
  group by d.lot, d.specialite, d.type_prise_en_charge
  order by d.lot, d.specialite, d.type_prise_en_charge;
$$;

comment on function public.valeurs_filtres() is
  'Pour la liste des dossiers : par lot, les valeurs distinctes de specialite et type_prise_en_charge des dossiers disponibles, avec leur effectif (specialite peut être null). Droits de l''appelant, chemin de recherche fixé.';

revoke all on function public.valeurs_filtres() from public, anon;
grant execute on function public.valeurs_filtres() to authenticated;
