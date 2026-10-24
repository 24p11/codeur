-- Migration 25 : correction de la règle d'ajout de la table commentaires (migration 24).
-- La règle vérifiait le commentaire retiré par une sous-requête sur la même table, ce que PostgreSQL refuse (récursion de
-- règle de sécurité). La vérification passe par une fonction en droits du propriétaire, au chemin de recherche fixé, qui dit
-- seulement si le commentaire visé est un commentaire d'auteur humain du testeur connecté.
create or replace function public.commentaire_retirable(cible bigint)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (select 1 from public.commentaires c
                 where c.id = cible and c.utilisateur = (select auth.uid()) and c.auteur = 'humain');
$$;
comment on function public.commentaire_retirable(bigint) is
  'Vrai si le commentaire visé est un commentaire d''auteur humain du testeur connecté : seul cas où une ligne de type retrait peut le viser. Droits du propriétaire, chemin de recherche fixé ; ne révèle rien d''autre.';
revoke all on function public.commentaire_retirable(bigint) from public, anon;
grant execute on function public.commentaire_retirable(bigint) to authenticated;

drop policy "commentaires : ajout sur son travail" on public.commentaires;
create policy "commentaires : ajout sur son travail"
  on public.commentaires for insert to authenticated
  with check (utilisateur = (select auth.uid()) and (type <> 'retrait' or public.commentaire_retirable(reponse_a)));
