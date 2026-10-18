-- Migration 5 : les règles d'accès (docs/SCHEMA.md §7), appliquées par la base elle-même.
--
-- Deux niveaux se complètent :
--  1. les droits de table (GRANT/REVOKE) : ce qu'un rôle peut tenter (lire, insérer, modifier, supprimer) ;
--  2. la sécurité par ligne (RLS) : parmi les lignes, lesquelles il voit ou peut écrire.
-- Un testeur connecté a le rôle « authenticated » ; un visiteur non connecté a le rôle « anon » ;
-- les scripts du responsable utilisent la clé secrète, qui passe outre ces règles.

-- ---------------------------------------------------------------- droits de table
-- Seuls les utilisateurs connectés accèdent aux tables : aucun droit pour les visiteurs non connectés.
revoke all on all tables in schema public from anon;

-- Tables de référence : lecture seule pour les testeurs.
revoke insert, update, delete on public.lots, public.fiches, public.synonymes, public.regles_situations from authenticated;

-- Documents : lecture et ajout d'une nouvelle version ; jamais de modification ni de suppression.
revoke update, delete on public.documents from authenticated;

-- Codages, RUM, appels au LLM, évaluations : jamais de modification ni de suppression.
revoke update, delete on public.codages, public.rum, public.appels_llm, public.evaluations from authenticated;

-- Appels au LLM : ajout seulement, sans relecture.
revoke select on public.appels_llm from authenticated;

-- Profils : pas de suppression.
revoke delete on public.profils from authenticated;

-- ---------------------------------------------------------------- sécurité par ligne
alter table public.lots              enable row level security;
alter table public.documents         enable row level security;
alter table public.fiches            enable row level security;
alter table public.synonymes         enable row level security;
alter table public.regles_situations enable row level security;
alter table public.profils           enable row level security;
alter table public.appels_llm        enable row level security;
alter table public.codages           enable row level security;
alter table public.rum               enable row level security;
alter table public.evaluations       enable row level security;

-- Tables de référence : un testeur connecté lit tout.
create policy "lots : lecture par les testeurs"
  on public.lots for select to authenticated using (true);
create policy "fiches : lecture par les testeurs"
  on public.fiches for select to authenticated using (true);
create policy "synonymes : lecture par les testeurs"
  on public.synonymes for select to authenticated using (true);
create policy "regles_situations : lecture par les testeurs"
  on public.regles_situations for select to authenticated using (true);

-- Documents : lecture de tous les documents ; ajout d'une nouvelle version seulement (page d'édition, lot A6),
-- signée par le testeur lui-même.
create policy "documents : lecture par les testeurs"
  on public.documents for select to authenticated using (true);
create policy "documents : ajout d'une nouvelle version par son auteur"
  on public.documents for insert to authenticated
  with check (cree_par = (select auth.uid()) and version > 1 and version_precedente is not null);

-- Codages : ses propres lignes seulement, et jamais l'étape scenario, ni en lecture ni en écriture.
create policy "codages : lecture de ses propres lignes hors scenario"
  on public.codages for select to authenticated
  using (utilisateur = (select auth.uid()) and etape <> 'scenario');
create policy "codages : ajout de ses propres lignes hors scenario"
  on public.codages for insert to authenticated
  with check (utilisateur = (select auth.uid()) and etape <> 'scenario');

-- RUM : ses propres lignes.
create policy "rum : lecture de ses propres lignes"
  on public.rum for select to authenticated using (cree_par = (select auth.uid()));
create policy "rum : ajout de ses propres lignes"
  on public.rum for insert to authenticated with check (cree_par = (select auth.uid()));

-- Appels au LLM : ajout de ses propres lignes ; aucune règle de lecture, donc aucune relecture.
create policy "appels_llm : ajout de ses propres lignes"
  on public.appels_llm for insert to authenticated with check (utilisateur = (select auth.uid()));

-- Évaluations : ajout de ses propres lignes ; relecture de celles dont il est l'auteur humain, jamais celles de l'IA.
create policy "evaluations : ajout de ses propres lignes"
  on public.evaluations for insert to authenticated with check (utilisateur = (select auth.uid()));
create policy "evaluations : relecture de ses propres évaluations humaines"
  on public.evaluations for select to authenticated
  using (utilisateur = (select auth.uid()) and auteur = 'humain');

-- Profils : lire, créer et modifier son propre profil.
create policy "profils : lecture de son profil"
  on public.profils for select to authenticated using (id = (select auth.uid()));
create policy "profils : création de son profil"
  on public.profils for insert to authenticated with check (id = (select auth.uid()));
create policy "profils : modification de son profil"
  on public.profils for update to authenticated
  using (id = (select auth.uid())) with check (id = (select auth.uid()));
