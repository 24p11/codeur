-- Migration 20 : evaluations.version_grille (brief 7, étape 4 : notation de la qualité du compte rendu par le testeur).
-- La grille (cinq dimensions, cinq niveaux avec un repère chacun) est le fichier versionné web/grille_qualite.md
-- (repère <!-- version: grille_v1 -->) ; la même grille servira plus tard à l'évaluation par le LLM.
-- Droits : inchangés. Les testeurs ont déjà insert et select sur la table entière (migration 5), la sécurité par ligne
-- limite l'ajout à leurs propres lignes et la relecture à leurs évaluations d'auteur humain (migration 5).
alter table public.evaluations add column version_grille text;
comment on column public.evaluations.version_grille is
  'La version de la grille de qualité utilisée (repère de version de web/grille_qualite.md, par exemple grille_v1). Même grille pour le testeur et, plus tard, pour l''évaluation par le LLM ; vide pour les lignes antérieures.';
