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
      lignes.push("", "CODES DÉJÀ RETENUS PAR LE CODEUR (ne pas les modifier, ne pas les reproposer ; rattacher les nouveaux passages à de nouveaux codes, ou les déclarer non codés) :");
      contexte.codesRetenus.forEach((c) => lignes.push("- " + c.code + " — " + c.libelle + (c.categorie === "pathologie_principale" ? " (pathologie principale, déjà désignée)" : "")));
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
    const anomalies = { passagesInconnus: [], passagesManquants: [], ensemblesSansPassage: 0, pathologiesPrincipalesMultiples: [], passagesMultiEnsembles: [], nonCodesRedondants: [] };
    const vus = new Map(); // n° de passage -> nombre d'ensembles
    const ensembles = [];
    for (const e of obj.ensembles) {
      if (!e || typeof e !== "object") continue;
      const nums = [];
      for (const x of (Array.isArray(e.passages) ? e.passages : [])) {
        const k = Number(x);
        if (!Number.isInteger(k) || k < 1 || k > n) { anomalies.passagesInconnus.push(x); continue; }
        if (!nums.includes(k)) nums.push(k);
      }
      if (!nums.length) { anomalies.ensemblesSansPassage += 1; continue; }
      for (const k of nums) vus.set(k, (vus.get(k) || 0) + 1);
      const confiance = typeof e.confiance === "number" && e.confiance >= 0 && e.confiance <= 1 ? e.confiance : null;
      ensembles.push({
        codeBrut: String(e.code || ""), code: normaliserCode(e.code), libelleModele: typeof e.libelle === "string" ? e.libelle : "",
        categorie: e.categorie === "pathologie_principale" ? "pathologie_principale" : "diagnostic_associe",
        passages: nums.sort((a, b) => a - b), confiance, explication: typeof e.explication === "string" ? e.explication : "",
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
    for (const [k, c] of vus) if (c > 1) anomalies.passagesMultiEnsembles.push(k);
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
  function construireCodage(resultat, passages, etape, precedent) {
    const prec = precedent || {};
    const ensembles = resultat.ensembles.map((e) => {
      const commentaires = [];
      if (e.statut !== "codable") {
        commentaires.push({ auteur: "outil", etape, texte: "Code proposé par l'IA non codable (" + e.code + (e.codeInitialNonCodable ? ", initialement " + e.codeInitialNonCodable : "") + ") : code à choisir par le codeur." });
      } else if (e.codeInitialNonCodable) {
        commentaires.push({ auteur: "outil", etape, texte: "Code corrigé après boucle de correction : " + e.codeInitialNonCodable + " → " + e.code + "." });
      }
      if (e.affinable) commentaires.push({ auteur: "outil", etape, texte: "Code plus précis possible : " + e.descendants.map((d) => d.code).join(", ") + "." });
      return {
        code: e.statut === "codable" ? e.code : null,
        libelle: e.statut === "codable" ? e.libelle : null,
        categorie: e.categorie,
        preuves: e.passages.map((k) => ({ debut: passages[k - 1].debut, fin: passages[k - 1].fin, texte: passages[k - 1].texte })),
        confiance: e.confiance, explication: e.explication || null, commentaires,
        ...(e.statut !== "codable" ? { code_propose_non_codable: e.code, libelle_propose: e.libelleModele || null } : {}),
      };
    });
    const nonCodes = resultat.nonCodes.map((x) => ({ debut: passages[x.passage - 1].debut, fin: passages[x.passage - 1].fin, texte: passages[x.passage - 1].texte, raison: x.raison || "", auteur: "ia" }));
    for (const k of resultat.anomalies.passagesManquants) {
      nonCodes.push({ debut: passages[k - 1].debut, fin: passages[k - 1].fin, texte: passages[k - 1].texte, raison: "Passage non traité par l'IA (absent de sa réponse).", auteur: "outil" });
    }
    return {
      regle_hierarchisation: prec.regle_hierarchisation ?? null,
      mode_prise_en_charge: prec.mode_prise_en_charge ?? null,
      commentaires: [],
      ensembles,
      passages_non_codes: nonCodes,
    };
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
  function preparerAppelRepete(courant, passagesSurlignes, verifier) {
    const aEnvoyer = [], completes = [];
    let modifie = false;
    for (const p of passagesSurlignes) {
      const i = courant.ensembles.findIndex((e) => e.preuves.some((q) => q.debut < p.fin && p.debut < q.fin));
      if (i < 0) { aEnvoyer.push(p); continue; }
      if (verifier && !verifier(p)) continue;
      const e = courant.ensembles[i];
      if (!e.preuves.some((q) => q.debut === p.debut && q.fin === p.fin)) {
        e.preuves.push({ debut: p.debut, fin: p.fin, texte: p.texte }); e.preuves.sort((a, b) => a.debut - b.debut); modifie = true;
      }
      completes.push(e.code || "code à choisir");
    }
    return { aEnvoyer, completes, modifie };
  }

  // Appel répété (SCHEMA.md §3.6) : assemble le nouveau codage = codes déjà retenus inchangés + propositions qui
  // portent sur les nouveaux passages. Une proposition dont tous les passages sont déjà couverts par un code retenu
  // est écartée ; un code proposé identique à un code retenu voit ses nouveaux passages ajoutés aux preuves de celui-ci,
  // de façon visible (commentaire outil, signalement à l'écran).
  function assemblerAppelRepete(codageRetenu, nouveau, etape) {
    const resultat = JSON.parse(JSON.stringify(codageRetenu));
    resultat.passages_non_codes = resultat.passages_non_codes || [];
    const ecartes = [], completes = [];
    for (const e of nouveau.ensembles) {
      const existant = resultat.ensembles.find((r) => r.code && e.code && r.code === e.code);
      if (existant) {
        for (const p of e.preuves) if (!existant.preuves.some((q) => q.debut === p.debut && q.fin === p.fin)) existant.preuves.push(p);
        existant.preuves.sort((a, b) => a.debut - b.debut);
        existant.commentaires = existant.commentaires || [];
        existant.commentaires.push({ auteur: "outil", etape, texte: "Passage ajouté aux preuves par l'IA lors d'un appel répété : " + e.preuves.map((p) => "« " + p.texte.slice(0, 40) + (p.texte.length > 40 ? "…" : "") + " »").join(", ") + "." });
        completes.push(existant.code);
        continue;
      }
      if (!e.preuves.length) { ecartes.push(e.code || e.code_propose_non_codable); continue; }
      if (e.categorie === "pathologie_principale" && resultat.ensembles.some((r) => r.categorie === "pathologie_principale")) {
        e.categorie = "diagnostic_associe";
        e.commentaires = (e.commentaires || []).concat([{ auteur: "outil", etape, texte: "Proposé en pathologie principale par l'IA, passé en diagnostic associé : une pathologie principale était déjà retenue." }]);
      }
      resultat.ensembles.push(e);
    }
    for (const x of nouveau.passages_non_codes) resultat.passages_non_codes.push(x);
    return { codage: resultat, ecartes, completes };
  }

  const api = { preparerAppelRepete, assemblerAppelRepete, normaliserCode, construireMessageUtilisateur, analyserReponse, verifierCodes, construireMessageCorrection,
                appliquerCorrection, construireCodage, compteurs, LIMITE_CANDIDATS };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else racine.CodeurCodage = api;
})(typeof window !== "undefined" ? window : globalThis);
