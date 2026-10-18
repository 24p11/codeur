-- Migration 11 : version de la mention d'information acceptée (profils.version_mention), et garantie que
-- accord_le et version_mention ne changent qu'en acceptant la mention.
--
-- Garantie en trois pièces :
--  1. la modification de profils par un testeur est limitée, colonne par colonne, à nom, prenom, statut et
--     etablissement : accord_le et version_mention ne sont pas modifiables directement ;
--  2. l'acceptation (première ou nouvelle) passe par la fonction accepter_mention(version), seule à pouvoir écrire
--     accord_le et version_mention, et uniquement sur la ligne du testeur connecté, avec l'heure de la base ;
--  3. à l'inscription (insertion), un déclencheur impose accord_le = heure de la base, quelle que soit la valeur envoyée.

alter table public.profils add column version_mention text;
comment on column public.profils.version_mention is
  'Version de la mention d''information acceptée par le testeur (repère <!-- version: … --> en tête de docs/mention_information.md). Écrite à l''inscription, puis uniquement par accepter_mention(). Si elle diffère de la version du fichier, la page redemande l''accord.';
comment on column public.profils.accord_le is
  'Date de l''accord pour l''utilisation des annotations à des fins de recherche : heure de la base, posée à l''inscription (déclencheur) puis par accepter_mention() à chaque nouvelle acceptation.';

-- 1. Droits colonne par colonne pour la modification.
revoke update on public.profils from authenticated;
grant update (nom, prenom, statut, etablissement) on public.profils to authenticated;

-- 3. À l'inscription, l'heure d'accord est celle de la base.
create or replace function public.profils_accord_heure_base()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.accord_le := now();
  return new;
end;
$$;
comment on function public.profils_accord_heure_base() is 'Déclencheur : accord_le prend l''heure de la base à l''insertion d''un profil.';
create trigger profils_accord_heure_base
  before insert on public.profils
  for each row execute function public.profils_accord_heure_base();

-- 2. L'acceptation de la mention. « security definer » : la fonction s'exécute avec les droits de son propriétaire
-- (elle peut écrire accord_le et version_mention), mais elle ne touche que la ligne du testeur connecté.
create or replace function public.accepter_mention(version text)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  utilisateur uuid := auth.uid();
begin
  if utilisateur is null then
    raise exception 'Aucun utilisateur connecté.';
  end if;
  if version is null or btrim(version) = '' then
    raise exception 'Version de la mention manquante.';
  end if;
  update public.profils
     set accord_le = now(), version_mention = version
   where id = utilisateur;
  if not found then
    raise exception 'Aucun profil pour cet utilisateur : utiliser la fiche d''inscription.';
  end if;
end;
$$;
comment on function public.accepter_mention(text) is
  'Enregistre l''acceptation de la mention d''information par le testeur connecté : accord_le = heure de la base, version_mention = version donnée. Seule voie de modification de ces deux colonnes (SCHEMA.md §5.1).';
revoke all on function public.accepter_mention(text) from public, anon;
grant execute on function public.accepter_mention(text) to authenticated;
