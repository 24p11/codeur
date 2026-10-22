-- Migration 13 : relier les tours d'un même codage dans appels_llm (docs/SCHEMA.md §3.10 et §5.2).
-- Le premier appel (tour de codage) a appel_initial vide ; chaque tour de correction porte l'UUID du premier appel.
-- La ligne codages.appel_llm pointe sur le dernier tour (celui dont la réponse a donné le codage enregistré).
alter table public.appels_llm add column appel_initial uuid references public.appels_llm (id);
comment on column public.appels_llm.appel_initial is
  'Pour un tour de correction (boucle du §3.10), l''identifiant du premier appel du même codage ; vide pour ce premier appel. Permet de relier les tours et de mesurer la fréquence des corrections.';
create index appels_llm_appel_initial_idx on public.appels_llm (appel_initial);
-- Droits : les testeurs insèrent leurs propres lignes (droit de table INSERT, règle par ligne existante) ; la nouvelle
-- colonne en hérite. Aucune lecture pour les testeurs, comme pour le reste de la table.
