-- Migration 10 : deux colonnes générées par la base à partir de nettoyage, lisibles par les testeurs, pour que la
-- vue dossiers_disponibles n'ait plus à lire nettoyage (jamais lisible par un testeur) et reste en mode
-- security_invoker : toute requête d'un testeur est soumise à ses propres droits, sans exception.
alter table public.documents
  add column nb_documents_origine integer not null
    generated always as (coalesce(jsonb_array_length(nettoyage -> 'documents_origine'), 1)) stored,
  add column a_corriger boolean not null
    generated always as (coalesce((nettoyage -> 'anomalies' ->> 'a_corriger')::boolean, false)) stored;

comment on column public.documents.nb_documents_origine is
  'Nombre de documents d''origine concaténés dans le texte, calculé par la base à partir de nettoyage.documents_origine (1 si absent). Lisible par les testeurs.';
comment on column public.documents.a_corriger is
  'Vrai si le document est signalé à corriger (nettoyage.anomalies.a_corriger ; SCHEMA.md §9.5) ; calculé par la base. Un document à corriger n''est pas proposé au codage tant qu''il n''a pas de version corrigée. Lisible par les testeurs.';

-- Droit de lecture explicite pour les testeurs (règle de docs/base_de_donnees.md : lecture de documents colonne par colonne).
grant select (nb_documents_origine, a_corriger) on public.documents to authenticated;

-- La vue lit désormais ces deux colonnes, et plus jamais nettoyage. Mêmes colonnes de sortie qu'avant.
create or replace view public.dossiers_disponibles
with (security_invoker = true)
as
select d.id,
       d.lot,
       d.id_source,
       d.version,
       d.specialite,
       d.type_prise_en_charge,
       d.nb_documents_origine,
       char_length(d.texte) as longueur,
       d.cree_le
from public.documents d
where not exists (select 1 from public.documents d2
                  where d2.lot = d.lot and d2.id_source = d.id_source and d2.version > d.version)
  and d.a_corriger = false;
