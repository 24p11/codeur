// codeur — logique du codage par l'IA (lot A2) : construction de la demande, contrôles de la réponse,
// vérification des codes dans l'index, construction du JSON du codage (docs/SCHEMA.md §3.4), compteurs (§3.7),
// boucle de correction (§3.10). Fichier partagé entre la page (variable globale CodeurCodage) et les tests
// (scripts/tests/tester_codage.py via Node). Aucune position ne vient du modèle : tout est recopié des passages.
(function (racine) {
  "use strict";

  // Forme codeur d'un code : majuscules, sans point ni espace, extension « + » conservée.
  function normaliserCode(brut) {
    if (typeof brut !== "string") return "";
    return brut.toUpperCase().replace(/[\s.]/g, "").replace(/[^A-Z0-9+]/g, "");
  }

  // Message « utilisateur » envoyé au modèle : texte complet, puis liste numérotée des passages (1..n).
  function construireMessageUtilisateur(idSource, texte, passages, contexte) {
    const lignes = ["TEXTE DU DOSSIER (" + idSource + ") :", texte, "", "PASSAGES SURLIGNÉS :"];
    passages.forEach((p, i) => lignes.push((i + 1) + ". « " + p.texte + " »"));
    if (contexte && contexte.codesRetenus && contexte.codesRetenus.length) {
      lignes.push("", "CODAGE EXISTANT, EN LECTURE SEULE (ne pas le modifier, ne pas reproposer ces codes pour les mêmes passages ; "
        + "ton travail porte seulement sur les passages surlignés ci-dessus, à coder par de nouveaux codes, à rattacher à un code existant en le reproposant à l'identique, ou à déclarer non codés) :");
      contexte.codesRetenus.forEach((c) => {
        lignes.push("- " + c.code + " — " + c.libelle + (c.categorie === "pathologie_principale" ? " (pathologie principale, déjà désignée)" : " (diagnostic associé)"));
        for (const t of (c.preuves || [])) lignes.push("    preuve : « " + t + " »");
      });
    }
    if (contexte && contexte.rejetes && contexte.rejetes.length) {
      lignes.push("", "CODES REJETÉS PAR LE CODEUR :");
      contexte.rejetes.forEach((r) => lignes.push("- le codeur a rejeté le code " + r.code + (r.libelle ? " (" + r.libelle + ")" : "") + " pour le" + (r.passages.length > 1 ? "s passages n° " : " passage n° ")
        + r.passages.join(", ") + " : ne le repropose pas pour ces passages."));
    }
    return lignes.join("\n");
  }

  // Analyse de la réponse du modèle. Retourne { ok, erreur } ou { ok: true, ensembles, nonCodes, anomalies }.
  // `passages` : la liste envoyée (index 0 = passage n° 1). `options.pp` : règle quand plusieurs pathologies principales
  // (« confiance » : garder celle de plus forte confiance, les autres deviennent diagnostics associés).
  function analyserReponse(texteReponse, passages, options) {
    options = options || {};
    let obj;
    try {
      let t = String(texteReponse).trim();
      const fence = t.match(/^```(?:json)?\s*([\s\S]*?)\s*```$/i);
      if (fence) t = fence[1];
      obj = JSON.parse(t);
    } catch (e) {
      return { ok: false, erreur: "la réponse du modèle n'est pas un JSON lisible" };
    }
    if (!obj || typeof obj !== "object" || !Array.isArray(obj.ensembles)) {
      return { ok: false, erreur: "la réponse du modèle n'a pas la forme attendue (liste « ensembles » absente)" };
    }
    const n = passages.length;
    const anomalies = { passagesInconnus: [], passagesManquants: [], ensemblesSansPassage: 0, pathologiesPrincipalesMultiples: [], passagesMultiEnsembles: [], passagesTropCites: [], nonCodesRedondants: [] };
    const vus = new Map(); // n° de passage -> nombre d'ensembles
    const ensembles = [];
    for (const e of obj.ensembles) {
      if (!e || typeof e !== "object") continue;
      const nums = [], natures = {};
      for (const x of (Array.isArray(e.passages) ? e.passages : [])) {
        // v1 : un numéro ; v2 : { numero, preuve: "directe" | "indirecte" }
        const objet = x && typeof x === "object";
        const k = Number(objet ? x.numero : x);
        if (!Number.isInteger(k) || k < 1 || k > n) { anomalies.passagesInconnus.push(objet ? x.numero : x); continue; }
        if (!nums.includes(k)) nums.push(k);
        if (objet && (x.preuve === "directe" || x.preuve === "indirecte")) natures[k] = x.preuve;
      }
      if (!nums.length) { anomalies.ensemblesSansPassage += 1; continue; }
      for (const k of nums) vus.set(k, (vus.get(k) || 0) + 1);
      const confiance = typeof e.confiance === "number" && e.confiance >= 0 && e.confiance <= 1 ? e.confiance : null;
      ensembles.push({
        codeBrut: String(e.code || ""), code: normaliserCode(e.code), libelleModele: typeof e.libelle === "string" ? e.libelle : "",
        categorie: e.categorie === "pathologie_principale" ? "pathologie_principale" : "diagnostic_associe",
        passages: nums.sort((a, b) => a - b), natures, confiance, explication: typeof e.explication === "string" ? e.explication : "",
      });
    }
    const nonCodes = [];
    for (const x of (Array.isArray(obj.passages_non_codes) ? obj.passages_non_codes : [])) {
      const k = Number(x && x.passage);
      if (!Number.isInteger(k) || k < 1 || k > n) { anomalies.passagesInconnus.push(x && x.passage); continue; }
      if (vus.has(k)) { anomalies.nonCodesRedondants.push(k); continue; } // déjà dans un ensemble : l'ensemble l'emporte
      if (!nonCodes.some((y) => y.passage === k)) nonCodes.push({ passage: k, raison: typeof (x.raison) === "string" ? x.raison : "" });
    }
    for (let k = 1; k <= n; k++) {
      if (!vus.has(k) && !nonCodes.some((y) => y.passage === k)) anomalies.passagesManquants.push(k);
    }
    for (const [k, c] of vus) { if (c > 1) anomalies.passagesMultiEnsembles.push(k); if (c > 2) anomalies.passagesTropCites.push({ passage: k, nb: c }); }
    // Au plus une pathologie principale : on garde celle de plus forte confiance (la première à égalité).
    const pp = ensembles.filter((e) => e.categorie === "pathologie_principale");
    if (pp.length > 1) {
      let garde = pp[0];
      for (const e of pp) if ((e.confiance ?? -1) > (garde.confiance ?? -1)) garde = e;
      for (const e of pp) if (e !== garde) { e.categorie = "diagnostic_associe"; anomalies.pathologiesPrincipalesMultiples.push(e.code); }
      anomalies.pathologiesPrincipalesMultiples.unshift(garde.code);
    }
    return { ok: true, ensembles, nonCodes, anomalies };
  }

  // Vérification des codes dans l'index. `index(code)` -> { codable, libelle, statut } ou null (inconnu).
  // Ajoute à chaque ensemble : statut ('codable' | 'non_codable' | 'inconnu'), libelle officiel, affinable (descendants
  // plus précis existent, fourni par `descendants(code)` -> liste).
  function verifierCodes(ensembles, index, descendants) {
    for (const e of ensembles) {
      const f = e.code ? index(e.code) : null;
      if (!f) { e.statut = "inconnu"; e.libelle = null; }
      else { e.statut = f.codable ? "codable" : "non_codable"; e.libelle = f.libelle; e.statutMco = f.statut; }
      const d = descendants ? (descendants(e.code) || []) : [];
      e.descendants = d;
      e.affinable = e.statut === "codable" && d.length > 0;
    }
    return ensembles;
  }

  // Message de correction (SCHEMA.md §3.10) pour les codes non codables ou inconnus. `candidats(ensemble)` -> liste de
  // sections [{ titre, liste: [{code, libelle}] }] : les descendants codables (seule liste pour un code tronqué ou
  // père interdit) ; pour un code inconnu ou sans descendant, les codes de la catégorie et les codes dont une
  // formulation ressemble au libellé du modèle. Au plus LIMITE_CANDIDATS codes au total par code à corriger.
  const LIMITE_CANDIDATS = 60;
  function construireMessageCorrection(ensembles, candidats) {
    const lignes = ["Certains codes de ta réponse ne sont pas codables en MCO (catégorie, code tronqué ou inconnu de l'index ATIH 2025). " +
      "Pour chacun, choisis un code parmi les codes codables proposés ci-dessous, en t'appuyant sur le texte et les passages de l'ensemble. " +
      "Réponds uniquement par un objet JSON de la forme {\"corrections\": {\"CODE_INITIAL\": \"CODE_CHOISI\"}}. " +
      "Si aucun code proposé ne convient, indique null."];
    const aCorriger = [];
    for (const e of ensembles) {
      if (e.statut === "codable") continue;
      const sections = candidats(e) || [];
      lignes.push("", "Code proposé : " + e.code + (e.libelleModele ? " (« " + e.libelleModele + " »)" : "") + " — passages " + e.passages.join(", ") +
        " — " + (e.statut === "inconnu" ? "inconnu de l'index" : "non codable") + ".");
      const retenus = [];
      let total = 0;
      for (const sec of sections) {
        const vus = new Set(retenus);
        const liste = (sec.liste || []).filter((c) => !vus.has(c.code));
        total += liste.length;
        const place = Math.max(0, LIMITE_CANDIDATS - retenus.length);
        const prise = liste.slice(0, place);
        if (!prise.length) continue;
        lignes.push("  " + sec.titre + (liste.length > prise.length ? " (les " + prise.length + " premiers sur " + liste.length + ")" : "") + " :");
        for (const c of prise) { lignes.push("  - " + c.code + " — " + c.libelle); retenus.push(c.code); }
      }
      if (!retenus.length) lignes.push("  Aucun code codable proposé : réponds null pour ce code.");
      aCorriger.push({ code: e.code, candidats: retenus, total });
    }
    return { message: lignes.join("\n"), aCorriger };
  }

  // Applique une réponse de correction : { corrections: { "Z992": "Z992+0" } }. Un code choisi hors des candidats
  // proposés est ignoré (signalé). Retourne la liste des codes toujours à corriger.
  function appliquerCorrection(ensembles, texteReponse, aCorriger, index, descendants) {
    let obj;
    try { obj = JSON.parse(String(texteReponse).trim().replace(/^```(?:json)?\s*|\s*```$/gi, "")); } catch (e) { return { ok: false, erreur: "réponse de correction illisible" }; }
    const corr = obj && obj.corrections && typeof obj.corrections === "object" ? obj.corrections : {};
    const ignores = [];
    for (const a of aCorriger) {
      const choisi = normaliserCode(corr[a.code] === null ? "" : (corr[a.code] || ""));
      if (!choisi) continue;
      if (!a.candidats.includes(choisi)) { ignores.push({ code: a.code, choisi }); continue; }
      for (const e of ensembles) if (e.code === a.code && e.statut !== "codable") {
        e.codeInitialNonCodable = e.codeInitialNonCodable || e.code;
        e.code = choisi;
      }
    }
    verifierCodes(ensembles, index, descendants);
    return { ok: true, ignores, restants: ensembles.filter((e) => e.statut !== "codable").map((e) => e.code) };
  }

  // Construction du JSON du codage (SCHEMA.md §3.4). Les preuves sont recopiées des passages envoyés.
  // Un ensemble dont le code n'est pas codable est enregistré avec code null et un commentaire (règle 8 : aucun code
  // non codable n'entre dans un codage) ; les passages manquants vont dans passages_non_codes avec l'auteur « outil ».
  // Les commentaires ne sont plus dans le JSON du codage (24 octobre 2026, table commentaires) : les alertes de l'outil et les
  // explications de l'IA sont rendues dans `codage._commentaires` (liste transitoire : objet, code, auteur, type, texte), que la
  // page enregistre dans la table après la ligne de codage, et retire du JSON (nettoyerPourEnregistrement).
  function commentaireCode(e, auteur, type, texte) {
    const code = e.code || e.code_propose_non_codable || null;
    return code ? { objet: "code", code, auteur, type, texte } : { objet: "sejour", code: null, auteur, type, texte };
  }
  function construireCodage(resultat, passages, etape, precedent) {
    const prec = precedent || {};
    const commentaires = [];
    const ensembles = resultat.ensembles.map((e) => {
      const ens = {
        code: e.statut === "codable" ? e.code : null,
        libelle: e.statut === "codable" ? e.libelle : null,
        categorie: e.categorie,
        preuves: e.passages.map((k) => ({ debut: passages[k - 1].debut, fin: passages[k - 1].fin, texte: passages[k - 1].texte, ...(e.natures && e.natures[k] ? { nature: e.natures[k] } : {}) })),
        confiance: e.confiance,
        ...(e.statut !== "codable" ? { code_propose_non_codable: e.code, libelle_propose: e.libelleModele || null } : {}),
      };
      if (e.explication) commentaires.push(commentaireCode(ens, "ia", "explication", e.explication));
      if (e.statut !== "codable") {
        commentaires.push(commentaireCode(ens, "outil", "alerte", "Code proposé par l'IA non codable (" + e.code + (e.codeInitialNonCodable ? ", initialement " + e.codeInitialNonCodable : "") + ") : code à choisir par le codeur."));
      } else if (e.codeInitialNonCodable) {
        commentaires.push(commentaireCode(ens, "outil", "alerte", "Code corrigé après boucle de correction : " + e.codeInitialNonCodable + " → " + e.code + "."));
      }
      if (e.affinable) commentaires.push(commentaireCode(ens, "outil", "alerte", "Code plus précis possible : " + e.descendants.map((d) => d.code).join(", ") + "."));
      for (const t of resultat.anomalies.passagesTropCites || []) {
        if (e.passages.includes(t.passage)) {
          const autres = resultat.ensembles.filter((x) => x !== e && x.passages.includes(t.passage)).map((x) => x.code || "?");
          commentaires.push(commentaireCode(ens, "outil", "alerte", "Passage n° " + t.passage + " (« " + passages[t.passage - 1].texte.slice(0, 40) + (passages[t.passage - 1].texte.length > 40 ? "…" : "") + " ») cité par " + t.nb + " codes dans la réponse de l'IA : avec " + autres.join(", ") + "."));
        }
      }
      return ens;
    });
    const nonCodes = resultat.nonCodes.map((x) => ({ debut: passages[x.passage - 1].debut, fin: passages[x.passage - 1].fin, texte: passages[x.passage - 1].texte, raison: x.raison || "", auteur: "ia" }));
    for (const k of resultat.anomalies.passagesManquants) {
      nonCodes.push({ debut: passages[k - 1].debut, fin: passages[k - 1].fin, texte: passages[k - 1].texte, raison: "Passage non traité par l'IA (absent de sa réponse).", auteur: "outil" });
    }
    return {
      regle_hierarchisation: prec.regle_hierarchisation ?? null,
      mode_prise_en_charge: prec.mode_prise_en_charge ?? null,
      libelle_mode_prise_en_charge: prec.libelle_mode_prise_en_charge ?? null,
      ensembles,
      passages_non_codes: nonCodes,
      codes_rejetes: [],
      _commentaires: commentaires,
    };
  }
  // Le JSON tel qu'il est enregistré : sans les listes transitoires ni les champs de l'ancien format (commentaires,
  // explications), qui restent lisibles dans les anciennes lignes mais ne sont plus recopiés.
  function nettoyerPourEnregistrement(codage) {
    const c = JSON.parse(JSON.stringify(codage));
    delete c._commentaires; delete c._brouillons; delete c.commentaires;
    for (const e of c.ensembles || []) { delete e.commentaires; delete e.explication; }
    if (c.caracteristiques) delete c.caracteristiques.explication;
    return c;
  }

  // Compteurs (SCHEMA.md §3.7) : appariement des ensembles par chevauchement de leurs preuves.
  function chevauche(a, b) { return a.debut < b.fin && b.debut < a.fin; }
  function memesPreuves(a, b) {
    if (a.length !== b.length) return false;
    const cle = (p) => p.debut + ":" + p.fin;
    const sa = new Set(a.map(cle));
    return b.every((p) => sa.has(cle(p)));
  }
  // SCHEMA.md §3.7 (ordre d'appariement du 22 octobre) : on apparie d'abord les ensembles de MÊME CODE dont les preuves
  // se chevauchent, puis, parmi les restants, ceux dont les preuves se chevauchent ; seuls les cas encore ambigus
  // (plusieurs candidats des deux côtés, ou ensembles sans preuve) sont incertains.
  function compteurs(precedent, nouveau) {
    const c = { conserves: 0, modifies: 0, preuves_modifiees: 0, retires: 0, ajoutes: 0, incertains: 0,
                regle_modifiee: (precedent ? precedent.regle_hierarchisation : null) !== (nouveau.regle_hierarchisation ?? null),
                mode_prise_en_charge_modifie: (precedent ? precedent.mode_prise_en_charge : null) !== (nouveau.mode_prise_en_charge ?? null) };
    const avant = precedent ? precedent.ensembles : [];
    const apres = nouveau.ensembles;
    const lie = (ea, en) => ea.preuves.some((pa) => en.preuves.some((pn) => chevauche(pa, pn)));
    const prisAvant = new Set(), prisApres = new Set();
    const classer = (ea, en) => {
      if (ea.code !== en.code || ea.categorie !== en.categorie) c.modifies += 1;
      else if (!memesPreuves(ea.preuves, en.preuves)) c.preuves_modifiees += 1;
      else c.conserves += 1;
    };
    // 1. même code et preuves qui se chevauchent (appariement sûr)
    avant.forEach((ea, i) => {
      if (!ea.preuves.length || !ea.code) return;
      const cand = apres.map((en, j) => [en, j]).filter(([en, j]) => !prisApres.has(j) && en.code === ea.code && lie(ea, en));
      if (cand.length === 1) { prisAvant.add(i); prisApres.add(cand[0][1]); classer(ea, cand[0][0]); }
    });
    // 2. preuves qui se chevauchent, parmi les restants
    const liens = avant.map((ea, i) => prisAvant.has(i) || !ea.preuves.length ? [] : apres.map((en, j) => [en, j]).filter(([en, j]) => !prisApres.has(j) && lie(ea, en)));
    const liensInverse = apres.map((en, j) => prisApres.has(j) ? [] : avant.map((ea, i) => [ea, i]).filter(([ea, i]) => !prisAvant.has(i) && ea.preuves.length && lie(ea, en)));
    avant.forEach((ea, i) => {
      if (prisAvant.has(i)) return;
      if (!ea.preuves.length) { c.incertains += 1; prisAvant.add(i); return; }
      const cand = liens[i];
      if (cand.length === 0) { c.retires += 1; prisAvant.add(i); return; }
      if (cand.length > 1 || liensInverse[cand[0][1]].length > 1) { c.incertains += 1; prisAvant.add(i); cand.forEach(([, j]) => prisApres.add(j)); return; }
      prisAvant.add(i); prisApres.add(cand[0][1]); classer(ea, cand[0][0]);
    });
    apres.forEach((en, j) => {
      if (prisApres.has(j)) return;
      if (!en.preuves.length) c.incertains += 1; else c.ajoutes += 1;
    });
    return c;
  }

  // Préparation d'un appel répété : parmi les passages surlignés, ceux qui chevauchent une preuve existante complètent
  // ce code (modification du codeur, non envoyée) ; les autres sont envoyés. Retourne { aEnvoyer, completes, modifie }.
  // SCHEMA.md §3.6 (23 octobre) : seuls les passages rattachés à aucun code partent (nouveaux surlignages, passages d'un code
  // supprimé) ; un passage déjà déclaré non codé n'est pas renvoyé. Retourne aussi, pour chaque code rejeté dont des preuves
  // sont renvoyées, les numéros (1 à n) de ces passages, pour la consigne « ne le repropose pas ».
  function preparerAppelRepete(courant, passagesSurlignes, verifier) {
    const aEnvoyer = [], completes = [];
    let modifie = false;
    const nonCodes = courant.passages_non_codes || [];
    for (const p of passagesSurlignes) {
      if (nonCodes.some((x) => x.debut === p.debut && x.fin === p.fin)) continue;
      const i = courant.ensembles.findIndex((e) => e.preuves.some((q) => q.debut < p.fin && p.debut < q.fin));
      if (i < 0) { if (!aEnvoyer.some((q) => q.debut === p.debut && q.fin === p.fin)) aEnvoyer.push(p); continue; }
      if (verifier && !verifier(p)) continue;
      const e = courant.ensembles[i];
      if (!e.preuves.some((q) => q.debut === p.debut && q.fin === p.fin)) {
        e.preuves.push({ debut: p.debut, fin: p.fin, texte: p.texte }); e.preuves.sort((a, b) => a.debut - b.debut); modifie = true;
      }
      completes.push(e.code || "code à choisir");
    }
    aEnvoyer.sort((a, b) => a.debut - b.debut);
    const rejetes = [];
    for (const r of courant.codes_rejetes || []) {
      const nums = [];
      aEnvoyer.forEach((p, k) => { if ((r.preuves || []).some((q) => q.debut < p.fin && p.debut < q.fin)) nums.push(k + 1); });
      if (nums.length) rejetes.push({ code: r.code, libelle: r.libelle || null, passages: nums });
    }
    return { aEnvoyer, completes, modifie, rejetes };
  }

  // Appel répété (SCHEMA.md §3.6) : assemble le nouveau codage = codes déjà retenus inchangés + propositions qui
  // portent sur les nouveaux passages. Une proposition dont tous les passages sont déjà couverts par un code retenu
  // est écartée ; un code proposé identique à un code retenu voit ses nouveaux passages ajoutés aux preuves de celui-ci,
  // de façon visible (commentaire outil, signalement à l'écran).
  function assemblerAppelRepete(codageRetenu, nouveau, etape) {
    const resultat = JSON.parse(JSON.stringify(codageRetenu));
    resultat.passages_non_codes = resultat.passages_non_codes || [];
    resultat.codes_rejetes = resultat.codes_rejetes || [];
    resultat._commentaires = (nouveau._commentaires || []).slice();
    const ecartes = [], completes = [], reproposes = [];
    for (const e of nouveau.ensembles) {
      // un code rejeté par le codeur, reproposé par l'IA pour les mêmes passages : gardé mais signalé, jamais imposé
      const rejet = resultat.codes_rejetes.find((r) => e.code && r.code === e.code && (r.preuves || []).some((q) => e.preuves.some((p) => q.debut < p.fin && p.debut < q.fin)));
      if (rejet) {
        resultat._commentaires.push(commentaireCode(e, "outil", "alerte", "Code déjà rejeté par vous (" + rejet.code + ", retiré à l'étape " + (rejet.etape || "précédente") + ") : reproposé par l'IA pour ces passages."));
        reproposes.push(e.code);
      }
      const existant = resultat.ensembles.find((r) => r.code && e.code && r.code === e.code);
      if (existant) {
        for (const p of e.preuves) if (!existant.preuves.some((q) => q.debut === p.debut && q.fin === p.fin)) existant.preuves.push(p);
        existant.preuves.sort((a, b) => a.debut - b.debut);
        resultat._commentaires.push(commentaireCode(existant, "outil", "alerte", "Passage ajouté aux preuves par l'IA lors d'un appel répété : " + e.preuves.map((p) => "« " + p.texte.slice(0, 40) + (p.texte.length > 40 ? "…" : "") + " »").join(", ") + "."));
        completes.push(existant.code);
        continue;
      }
      if (!e.preuves.length) { ecartes.push(e.code || e.code_propose_non_codable); continue; }
      if (e.categorie === "pathologie_principale" && resultat.ensembles.some((r) => r.categorie === "pathologie_principale")) {
        e.categorie = "diagnostic_associe";
        resultat._commentaires.push(commentaireCode(e, "outil", "alerte", "Proposé en pathologie principale par l'IA, passé en diagnostic associé : une pathologie principale était déjà retenue."));
      }
      resultat.ensembles.push(e);
    }
    for (const x of nouveau.passages_non_codes) resultat.passages_non_codes.push(x);
    return { codage: resultat, ecartes, completes, reproposes };
  }

  // ================================================================================================================
  // Second appel (brief 8) : la règle de hiérarchisation et le mode de prise en charge (SCHEMA.md §3.4, §3.6 ; prompt
  // web/prompts/caracteristiques_v1.md). Logique pure : message, analyse et contrôles de la réponse, correction, application.
  // MODE_PROMPT_CARACTERISTIQUES : « complet » envoie le préambule, les extraits officiels des règles candidates et les passages
  // communs (option a du 24 octobre 2026) ; « table » (à venir, option c) n'enverrait que le tableau des règles.
  const MODE_PROMPT_CARACTERISTIQUES = "complet";
  const SITUATIONS = ["diagnostic", "traitement", "surveillance"];
  const CIRCONSTANCES = { diagnostic: ["diagnostic_decouverte", "diagnostic_bilan_extension", "diagnostic_exploration_programmee", "diagnostic_antecedent_facteur_risque"],
                          traitement: ["traitement_unique", "traitement_repetitif", "traitement_adaptation_diabete", "traitement_assimile"],
                          surveillance: ["surveillance_negative", "surveillance_positive"] };
  // famille (type) d'une ligne du guide -> situation attendue ; les situations assimilées au traitement unique sont « traitement »
  const SITUATION_DE_TYPE = { diagnostic: "diagnostic", traitement: "traitement", surveillance: "surveillance", accouchement: "traitement", nouveau_ne: "traitement", ivg: "traitement", itg: "traitement" };

  function pathologiePrincipale(codage) {
    const e = (codage.ensembles || []).find((x) => x.categorie === "pathologie_principale");
    return e && e.code ? e.code : null;
  }
  function modesDe(regle) {
    const m = (regle.details && regle.details.mode_prise_en_charge) || { dp: false, codes: [] };
    return { dp: !!m.dp, codes: m.codes || [] };
  }
  // Le message utilisateur du second appel. `regles` : les lignes compatibles (regles_compatibles) ; `extraits` : la liste de
  // web/situations/extraits_guide.json ; `commentaire` : le commentaire du codeur pour un recalcul (ou null).
  function construireMessageCaracteristiques(idSource, texte, codage, regles, extraits, commentaire, mode) {
    mode = mode || MODE_PROMPT_CARACTERISTIQUES;
    const L = ["TEXTE DU DOSSIER (" + idSource + ") :", texte, "", "CODAGE PROPOSÉ :"];
    const pp = (codage.ensembles || []).find((e) => e.categorie === "pathologie_principale");
    const cite = (e) => (e.preuves || []).filter((p) => !p.introuvable).map((p) => "« " + p.texte + " »").join(", ") || "(sans passage cité)";
    L.push(pp && pp.code ? "Pathologie principale : " + pp.code + " — " + pp.libelle + " ; passages : " + cite(pp) : "Pathologie principale : aucune (non renseignée)");
    const das = (codage.ensembles || []).filter((e) => e.categorie !== "pathologie_principale" && e.code);
    L.push(das.length ? "Pathologies associées :" : "Pathologies associées : aucune");
    for (const e of das) L.push("- " + e.code + " — " + e.libelle + " ; passages : " + cite(e));
    L.push("", "PRÉAMBULE OFFICIEL (guide méthodologique MCO 2026) :");
    for (const x of extraits.filter((x) => x.type === "preambule")) L.push("[" + x.section + ", p. " + x.page + "]", x.extrait, "");
    const codesRegles = new Set(regles.map((r) => r.regle)), officielles = new Set(regles.map((r) => r.regle_officielle));
    L.push("RÈGLES CANDIDATES (" + regles.length + ", les seules compatibles avec la pathologie principale) :");
    for (const r of regles) {
      const m = modesDe(r);
      const modes = (m.dp ? ["DP"] : []).concat(m.codes.map((c) => c.code + " (" + c.libelle + ")"));
      L.push("", "--- Règle " + r.regle + " — " + r.famille + (r.specificite ? " — " + r.specificite : "") + (r.libelle && r.libelle !== r.specificite ? " — " + r.libelle : ""));
      L.push("Pathologies visées : " + (r.pathologie || "(vide dans le guide)") + " ; compatibilité : " + (r.motif || ""));
      L.push("Modes de prise en charge possibles : " + (modes.join(", ") || "(aucun)"));
      if (mode === "complet") {
        for (const x of extraits.filter((x) => x.type === "regle" && x.regle_officielle === r.regle_officielle && (!x.lignes || x.lignes.split(" ").includes(r.regle)))) {
          L.push("Extrait officiel [" + x.section + ", p. " + x.page + "] :", x.extrait);
        }
      }
    }
    if (mode === "complet") {
      const communs = extraits.filter((x) => x.type === "commun" && (x.lignes ? x.lignes.split(" ").some((l) => codesRegles.has(l)) : x.regle_officielle.split(" ").some((o) => officielles.has(o))));
      if (communs.length) L.push("", "PASSAGES OFFICIELS COMMUNS À PLUSIEURS RÈGLES CANDIDATES :");
      for (const x of communs) L.push("", "[" + x.section + ", p. " + x.page + " ; règles " + (x.lignes || x.regle_officielle).split(" ").filter((k) => codesRegles.has(k) || officielles.has(k)).join(", ") + "]", x.extrait);
    }
    if (commentaire) L.push("", "COMMENTAIRE DU CODEUR :", commentaire);
    return L.join("\n");
  }
  // Analyse et contrôles de la réponse. Retourne { ok, erreur } ou { ok: true, situation, circonstance, regle, mode, dr_conforme,
  // confiance, explication, anomalies: [...], aCorriger: bool } ; rien n'est refusé, tout est signalé.
  function analyserCaracteristiques(texteReponse, regles) {
    let obj;
    try {
      let t = String(texteReponse).trim(); const fence = t.match(/^```(?:json)?\s*([\s\S]*?)\s*```$/i); if (fence) t = fence[1];
      obj = JSON.parse(t);
    } catch (e) { return { ok: false, erreur: "la réponse du modèle n'est pas un JSON lisible" }; }
    if (!obj || typeof obj !== "object") return { ok: false, erreur: "la réponse du modèle n'a pas la forme attendue" };
    const r = { ok: true, situation: SITUATIONS.includes(obj.situation) ? obj.situation : null, circonstance: typeof obj.circonstance === "string" ? obj.circonstance : null,
                regle: typeof obj.regle === "string" ? obj.regle.trim() : null, mode: obj.mode_prise_en_charge === "DP" ? "DP" : (typeof obj.mode_prise_en_charge === "string" ? normaliserCode(obj.mode_prise_en_charge) : null),
                dr_conforme: obj.dr_conforme === null || obj.dr_conforme === undefined ? null : !!obj.dr_conforme,
                libelle_mode: typeof obj.libelle_mode === "string" && obj.libelle_mode.trim() ? obj.libelle_mode.trim() : null,
                confiance: typeof obj.confiance === "number" && obj.confiance >= 0 && obj.confiance <= 1 ? obj.confiance : null,
                explication: typeof obj.explication === "string" ? obj.explication : "", anomalies: [], aCorriger: false };
    const regle = regles.find((x) => x.regle === r.regle);
    if (!regle) { r.anomalies.push("règle hors des candidates (" + (r.regle || "vide") + ")"); r.aCorriger = true; }
    else {
      const m = modesDe(regle);
      if (r.mode === "DP" ? !m.dp : !m.codes.some((c) => c.code === r.mode)) { r.anomalies.push("mode de prise en charge hors de la liste de la règle " + regle.regle + " (" + (r.mode || "vide") + ")"); r.aCorriger = true; }
      const attendue = SITUATION_DE_TYPE[regle.type];
      if (r.situation && attendue && r.situation !== attendue) r.anomalies.push("situation « " + r.situation + " » incohérente avec la famille de la règle " + regle.regle + " (" + attendue + ")");
    }
    if (!r.situation) r.anomalies.push("situation absente ou inconnue (" + (obj.situation || "vide") + ")");
    if (r.circonstance && !(CIRCONSTANCES[r.situation] || []).includes(r.circonstance)) r.anomalies.push("circonstance « " + r.circonstance + "» hors de la situation « " + (r.situation || "?") + " »");
    if (!r.circonstance) r.anomalies.push("circonstance absente");
    if ((r.mode === "DP") !== (r.dr_conforme === null)) r.anomalies.push("dr_conforme doit être null si et seulement si le mode est DP (mode " + (r.mode || "vide") + ", dr_conforme " + r.dr_conforme + ")");
    return r;
  }
  // Tour de correction : la règle et les modes possibles, pour une réponse hors liste.
  function construireMessageCorrectionCaracteristiques(analyse, regles) {
    const L = ["Ta réponse n'est pas recevable : " + analyse.anomalies.filter((a) => /hors/.test(a)).join(" ; ") + ".",
               "Choisis la règle UNIQUEMENT parmi les règles candidates ci-dessous, et le mode de prise en charge UNIQUEMENT dans la liste de la règle choisie.", ""];
    for (const r of regles) { const m = modesDe(r); L.push("- " + r.regle + " (" + r.famille + (r.specificite ? " — " + r.specificite : "") + ") : modes possibles : " + (m.dp ? ["DP"] : []).concat(m.codes.map((c) => c.code)).join(", ")); }
    L.push("", "Réponds uniquement par un objet JSON : {\"regle\": \"…\", \"mode_prise_en_charge\": \"…\"}.");
    return L.join("\n");
  }
  function appliquerCorrectionCaracteristiques(analyse, texteReponse, regles) {
    let obj; try { let t = String(texteReponse).trim(); const f = t.match(/^```(?:json)?\s*([\s\S]*?)\s*```$/i); if (f) t = f[1]; obj = JSON.parse(t); } catch (e) { return { ok: false }; }
    const regle = regles.find((x) => x.regle === (obj && typeof obj.regle === "string" ? obj.regle.trim() : null));
    if (!regle) return { ok: false };
    const mode = obj.mode_prise_en_charge === "DP" ? "DP" : normaliserCode(obj.mode_prise_en_charge || "");
    const m = modesDe(regle);
    if (mode === "DP" ? !m.dp : !m.codes.some((c) => c.code === mode)) return { ok: false };
    analyse.regle = regle.regle; analyse.mode = mode; analyse.aCorriger = false; analyse.anomalies = analyse.anomalies.filter((a) => !/hors/.test(a)); analyse.corrige = true;
    return { ok: true };
  }
  const LIBELLE_DP = "La pathologie principale motive elle-même le séjour";
  // Le libellé du mode de prise en charge : pour un code Z, le libellé officiel (liste de la règle, ou index) ; pour DP, le texte
  // court du modèle (dix mots au plus), sinon le texte fixe.
  function libelleMode(mode, regle, libelleModele, index) {
    if (!mode) return null;
    if (mode === "DP") {
      const t = (libelleModele || "").trim();
      return t && t.split(/\s+/).length <= 10 ? t : LIBELLE_DP;
    }
    const m = regle ? modesDe(regle).codes.find((c) => c.code === mode) : null;
    if (m) return m.libelle;
    const f = index ? index(mode) : null;
    return f ? f.libelle : null;
  }
  // Applique la proposition au codage : règle, mode et libellé du mode retenus (null, « à choisir », si la correction a échoué),
  // et l'objet `caracteristiques` (SCHEMA.md §3.4 : calculee_sur, appel_llm, confiance, règle et mode proposés). L'explication
  // du modèle est rendue à part : la page l'enregistre comme commentaire (objet mode_prise_en_charge, auteur ia).
  function appliquerCaracteristiques(codage, analyse, infos, regles) {
    const aChoisir = !analyse.ok || analyse.aCorriger;
    const regle = aChoisir ? null : (regles || []).find((r) => r.regle === analyse.regle) || null;
    codage.regle_hierarchisation = aChoisir ? null : analyse.regle;
    codage.mode_prise_en_charge = aChoisir ? null : analyse.mode;
    codage.libelle_mode_prise_en_charge = aChoisir ? null : libelleMode(analyse.mode, regle, analyse.libelle_mode, null);
    codage.caracteristiques = { calculee_sur: pathologiePrincipale(codage), appel_llm: infos.appel_llm || null,
                                regle: aChoisir ? null : analyse.regle, mode_prise_en_charge: aChoisir ? null : analyse.mode,
                                confiance: analyse.ok ? analyse.confiance : null };
    return { codage, explication: analyse.ok && analyse.explication ? analyse.explication : null };
  }
  // « Règle à revoir » : la pathologie principale courante diffère de celle sur laquelle la règle a été calculée.
  function regleARevoir(codage) {
    const c = codage && codage.caracteristiques;
    if (!c) return false;
    return pathologiePrincipale(codage) !== (c.calculee_sur || null);
  }

  const api = { preparerAppelRepete, assemblerAppelRepete, normaliserCode, construireMessageUtilisateur, analyserReponse, verifierCodes, construireMessageCorrection,
                appliquerCorrection, construireCodage, compteurs, LIMITE_CANDIDATS,
                MODE_PROMPT_CARACTERISTIQUES, construireMessageCaracteristiques, analyserCaracteristiques, construireMessageCorrectionCaracteristiques,
                appliquerCorrectionCaracteristiques, appliquerCaracteristiques, regleARevoir, pathologiePrincipale, modesDe, CIRCONSTANCES,
                nettoyerPourEnregistrement, commentaireCode, libelleMode, LIBELLE_DP };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else racine.CodeurCodage = api;
})(typeof window !== "undefined" ? window : globalThis);
