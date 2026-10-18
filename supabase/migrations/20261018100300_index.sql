-- Migration 4 : les index (docs/SCHEMA.md §8), plus les index sur les liens entre tables.

-- Index demandés par SCHEMA.md §8.
-- (L'unicité documents (lot, id_source, version) est déjà un index, créé par la contrainte de la migration 2.)
create index documents_specialite_idx on public.documents (specialite);
create index documents_type_prise_en_charge_idx on public.documents (type_prise_en_charge);
create index codages_document_utilisateur_etape_idx on public.codages (document, utilisateur, etape);

-- Index de recherche sur les champs JSON : permettent les requêtes de contenu (@>, ?, chemins).
create index codages_codage_gin_idx on public.codages using gin (codage);
create index rum_rum_gin_idx on public.rum using gin (rum);

-- Recherche dans les synonymes : trigrammes sur la formulation normalisée (sans accents, minuscules),
-- ce qui tolère les fautes de frappe légères (opérateurs % et similarity de pg_trgm, et LIKE/ILIKE).
create index synonymes_formulation_trgm_idx on public.synonymes using gin (formulation_normalisee extensions.gin_trgm_ops);
create index synonymes_code_idx on public.synonymes (code);

-- Index sur les liens entre tables (PostgreSQL ne les crée pas automatiquement) : accélèrent les jointures
-- et les vérifications d'intégrité lors des suppressions.
create index documents_lot_idx on public.documents (lot);
create index documents_version_precedente_idx on public.documents (version_precedente);
create index codages_codage_precedent_idx on public.codages (codage_precedent);
create index codages_appel_llm_idx on public.codages (appel_llm);
create index rum_document_idx on public.rum (document);
create index rum_codage_idx on public.rum (codage);
create index rum_cree_par_idx on public.rum (cree_par);
create index appels_llm_utilisateur_document_idx on public.appels_llm (utilisateur, document);
create index evaluations_document_utilisateur_idx on public.evaluations (document, utilisateur);
create index evaluations_appel_llm_idx on public.evaluations (appel_llm);
