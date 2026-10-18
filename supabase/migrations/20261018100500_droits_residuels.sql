-- Migration 6 : retirer aux testeurs les droits de table que Supabase accorde par défaut et que
-- docs/SCHEMA.md §7 ne prévoit pas : TRUNCATE (vider une table, non filtré par les règles par ligne),
-- TRIGGER (poser un déclencheur) et REFERENCES (créer une clé étrangère vers la table).
revoke truncate, trigger, references on all tables in schema public from authenticated;

-- À partir de maintenant, plus aucun droit n'est accordé automatiquement sur les tables à venir,
-- ni aux testeurs connectés (authenticated) ni aux visiteurs non connectés (anon).
-- Règle du projet (docs/base_de_donnees.md) : toute nouvelle table reçoit explicitement ses droits
-- et ses règles par ligne dans sa propre migration.
alter default privileges for role postgres in schema public revoke all on tables from authenticated;
alter default privileges for role postgres in schema public revoke all on tables from anon;
