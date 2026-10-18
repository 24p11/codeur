-- Migration 9 : (1) la colonne documents.nettoyage n'est plus lisible par les testeurs (docs/SCHEMA.md §1 et §2 :
-- « jamais affiché » ; elle contient les blocs retirés, donc des codes du scénario) ; (2) une vue
-- dossiers_disponibles pour la liste des dossiers (CADRAGE.md §2.1 ; SCHEMA.md §9.5) : dernière version de chaque
-- document, sans les documents signalés à corriger, sans le texte, avec le nombre de documents d'origine et la longueur.

-- (1) Lecture de documents limitée aux colonnes visibles des testeurs.
revoke select on public.documents from authenticated;
grant select (id, lot, id_source, version, version_precedente, motif_version, specialite, type_prise_en_charge,
              texte, empreinte, mesures, cree_le, cree_par)
  on public.documents to authenticated;

-- (2) La vue. « security_invoker » : la vue est lue avec les droits et les règles par ligne du testeur qui l'interroge,
-- mais ses colonnes sont calculées par la base, de sorte que nettoyage n'est jamais transmis.
create view public.dossiers_disponibles
with (security_invoker = true)
as
select d.id,
       d.lot,
       d.id_source,
       d.version,
       d.specialite,
       d.type_prise_en_charge,
       coalesce(jsonb_array_length(d.nettoyage -> 'documents_origine'), 1) as nb_documents_origine,
       char_length(d.texte) as longueur,
       d.cree_le
from public.documents d
where not exists (select 1 from public.documents d2
                  where d2.lot = d.lot and d2.id_source = d.id_source and d2.version > d.version)
  and coalesce((d.nettoyage -> 'anomalies' ->> 'a_corriger')::boolean, false) = false;

comment on view public.dossiers_disponibles is
  'Les dossiers que la page propose au codage : dernière version de chaque document, sans les documents signalés à corriger (SCHEMA.md §9.5). Ne transmet ni le texte ni le champ nettoyage ; nb_documents_origine et longueur sont calculés par la base.';
comment on column public.dossiers_disponibles.nb_documents_origine is 'Nombre de documents d''origine concaténés dans le texte (1 si le champ nettoyage ne le précise pas).';
comment on column public.dossiers_disponibles.longueur is 'Longueur du texte de référence, en caractères (char_length).';

grant select on public.dossiers_disponibles to authenticated;
