-- Migration 26 : enregistrer le test de connexion de l'écran « Réglages de l'IA » dans appels_llm (docs/SCHEMA.md §5.2).
-- Jusqu'ici ce test n'était pas enregistré : les pannes du service (HTTP 400 du 17 novembre 2026, puis « réponse sans
-- contenu ») n'y laissaient aucune trace. Le test se fait hors de tout dossier : la colonne document devient facultative
-- pour cette seule tâche, et reste obligatoire pour toutes les autres.
-- Aucune ligne existante n'est modifiée ; aucune donnée n'est supprimée.
alter table public.appels_llm drop constraint appels_llm_tache_check;
alter table public.appels_llm add constraint appels_llm_tache_check
  check (tache in ('evaluation_document', 'caracteristiques_sejour', 'codage', 'revue', 'test_connexion'));
alter table public.appels_llm alter column document drop not null;
alter table public.appels_llm add constraint appels_llm_document_obligatoire
  check (document is not null or tache = 'test_connexion');
comment on column public.appels_llm.tache is
  'Tâche : evaluation_document, caracteristiques_sejour, codage, revue, test_connexion (test de l''écran des réglages, hors de tout dossier).';
comment on column public.appels_llm.document is
  'La version du document concernée. Obligatoire, sauf pour la tâche test_connexion, faite hors de tout dossier.';
-- Droits : inchangés. Les testeurs ajoutent leurs propres lignes (droit INSERT, règle « appels_llm : ajout de ses propres
-- lignes ») et ne peuvent ni les relire, ni les modifier, ni les supprimer.
