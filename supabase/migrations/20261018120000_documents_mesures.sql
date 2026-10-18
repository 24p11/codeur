-- Migration 8 : colonne documents.mesures (docs/SCHEMA.md §2, version 1.1).
-- Lue par les testeurs connectés (la lecture de la table documents est déjà accordée), jamais écrite par eux :
-- on remplace le droit d'insertion sur toute la table par un droit d'insertion limité aux colonnes qu'un testeur
-- peut renseigner quand il crée une nouvelle version d'un document (page d'édition, lot A6).
alter table public.documents add column mesures jsonb not null default '{}'::jsonb;

comment on column public.documents.mesures is
  'JSON : les mesures fixes calculées sur le texte (nombre de mots, de phrases, rubriques présentes, passages répétés…), avec la version du calcul (version_calcul). Vide pour l''instant : remplie plus tard par un script Python reprenant les calculs du projet de génération, puis à terme par une API de diagnostic. Contrat entre le calcul et l''outil : le format reste le même quel que soit le calcul. Lue par la page pour l''évaluation du document ; écrite uniquement par les scripts (SCHEMA.md §2).';

revoke insert on public.documents from authenticated;
grant insert (lot, id_source, version, version_precedente, motif_version, specialite, type_prise_en_charge, texte, nettoyage, cree_par)
  on public.documents to authenticated;
