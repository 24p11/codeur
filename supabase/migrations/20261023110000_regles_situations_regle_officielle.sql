-- Migration 22 : guide des situations cliniques, version 1 (brief 8, étape 3).
-- Deux colonnes pour la table regles_situations : la règle officielle du guide méthodologique à laquelle la ligne se rattache
-- (les sous-règles du projet Stream D3-1, T2-R52, S1-Chronic… affinent une règle officielle ; IVG et ITG n'en ont pas),
-- et un indicateur « évaluable » (faux pour T10-irradiations tant que les listes d'actes CCAM manquent : la règle est chargée
-- mais jamais proposée parmi les règles compatibles). Droits inchangés : lecture seule pour les testeurs connectés (migration 5).
alter table public.regles_situations
  add column regle_officielle text,
  add column evaluable boolean not null default true;
comment on column public.regles_situations.regle_officielle is
  'La règle officielle du guide méthodologique MCO (étiquette [Règle X] : D1 à D9, T1 à T15, S1 à S4, SD1, SD2) à laquelle la ligne se rattache ; vide pour IVG et ITG, qui n''ont pas d''étiquette. Sert à retrouver les extraits officiels (docs/referentiels/situations_cliniques/extraits_guide_methodologique_2026.csv).';
comment on column public.regles_situations.evaluable is
  'Vrai si la compatibilité de la règle avec la pathologie principale peut se juger (fonction regles_compatibles). Faux pour une règle fondée sur une liste d''actes CCAM absente (T10-irradiations) : chargée, jamais proposée.';
