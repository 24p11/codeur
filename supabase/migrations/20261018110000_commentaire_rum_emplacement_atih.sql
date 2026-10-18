-- Migration 7 : met à jour le commentaire de la colonne rum.rum, qui citait l'ancien emplacement
-- du fichier ATIH, déplacé dans docs/referentiels/atih/ (docs/referentiels/README_referentiels.md).
comment on column public.rum.rum is 'JSON : les variables officielles du RUM sous leur nom (DP, DR, DA, modes d''entrée et de sortie…), d''après docs/referentiels/atih/formats_mco_2026.xlsx. Format : SCHEMA.md §4.';
