// Pont pour les tests du codage : lit un cas JSON sur l'entrée standard, applique web/codage.js et renvoie le résultat.
"use strict";
const path = require("path");
const C = require(path.join(__dirname, "..", "..", "web", "codage.js"));
let entree = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (d) => { entree += d; });
process.stdin.on("end", async () => {
  const cas = JSON.parse(entree);
  const index = (code) => cas.index[code] || null;
  const descendants = (code) => cas.descendants[code] || [];
  const sortie = {};
  if (cas.reponse !== undefined) {
    const r = C.analyserReponse(cas.reponse, cas.passages);
    sortie.analyse = r;
    if (r.ok) {
      C.verifierCodes(r.ensembles, index, descendants);
      sortie.statuts = r.ensembles.map((e) => [e.code, e.statut, e.affinable]);
      if (cas.reponseCorrection !== undefined) {
        const m = C.construireMessageCorrection(r.ensembles, (e) => {
          const d = descendants(e.code);
          if (d.length) return [{ titre: "Codes codables possibles (descendants)", liste: d }];
          const sections = [];
          const cat = (cas.categorie && cas.categorie[e.code.slice(0, 3)]) || [];
          if (cat.length) sections.push({ titre: "Codes codables de la catégorie " + e.code.slice(0, 3), liste: cat });
          const sim = (cas.ressemblance && cas.ressemblance[e.code]) || [];
          if (sim.length) sections.push({ titre: "Codes dont une formulation ressemble à votre libellé", liste: sim });
          return sections;
        });
        sortie.messageCorrection = m.message;
        sortie.correction = C.appliquerCorrection(r.ensembles, cas.reponseCorrection, m.aCorriger, index, descendants);
      }
      sortie.codage = C.construireCodage(r, cas.passages, "ia_humain", cas.precedent || null);
      if (cas.precedent !== undefined) sortie.compteurs = C.compteurs(cas.precedent, sortie.codage);
    }
  }
  if (cas.reessais) {
    // réponses simulées du service, dans l'ordre : { statut, retryAfter } pour un refus, { ok: true } pour un succès ; aucune attente réelle
    const attentes = []; let appels = 0;
    try {
      const resultat = await C.avecReessais(async (tentative) => {
        const x = cas.reessais.reponses[appels++];
        if (x.statut) { const e = new Error("le service a répondu HTTP " + x.statut); e.statut = x.statut; e.retryAfter = x.retryAfter === undefined ? null : x.retryAfter; throw e; }
        return { tentative };
      }, async (secondes, i) => { attentes.push(secondes); sortie.derniereAnnonce = C.messageAttente(secondes, i.statut, i.prochaine, i.essais); }, cas.reessais.maintenant);
      sortie.reessais = { ok: true, tentative: resultat.tentative, appels, attentes };
    } catch (e) {
      sortie.reessais = { ok: false, appels, attentes, statut: e.statut === undefined ? null : e.statut, essaisEpuises: !!e.essaisEpuises, message: C.messageEchecReessais(e.statut, "mistral") };
    }
  }
  if (cas.requete) {
    const q = cas.requete;
    sortie.requete = { corps: C.corpsRequete(q.modele, q.messages, q.json), enregistree: C.requeteEnregistree(q.modele, q.adresse, q.messages, q.tour, q.passages, q.tentative, q.appel_vise) };
  }
  if (cas.repete) sortie.repete = C.assemblerAppelRepete(cas.repete.retenu, cas.repete.nouveau, "ia_humain");
  if (cas.preparer) {
    const courant = JSON.parse(JSON.stringify(cas.preparer.courant));
    const r = C.preparerAppelRepete(courant, cas.preparer.passages, null);
    sortie.preparer = { ...r, courant };
    // enchaînement complet d'un appel répété : message, analyse de la réponse, construction, assemblage
    if (cas.preparer.reponse !== undefined) {
      const contexte = { codesRetenus: courant.ensembles.filter((e) => e.code).map((e) => ({ code: e.code, libelle: e.libelle, categorie: e.categorie, preuves: e.preuves.map((p) => p.texte) })), rejetes: r.rejetes };
      sortie.preparer.message = C.construireMessageUtilisateur("DOC", "texte", r.aEnvoyer, contexte);
      const an = C.analyserReponse(cas.preparer.reponse, r.aEnvoyer);
      sortie.preparer.analyse = an;
      if (an.ok) {
        C.verifierCodes(an.ensembles, index, descendants);
        const nouveau = C.construireCodage(an, r.aEnvoyer, "ia_humain", courant);
        sortie.preparer.assemblage = C.assemblerAppelRepete(courant, nouveau, "ia_humain");
      }
    }
  }
  if (cas.compteursSeuls) sortie.compteurs = C.compteurs(cas.compteursSeuls.avant, cas.compteursSeuls.apres);
  if (cas.caracteristiques) {
    const k = cas.caracteristiques; const codage = JSON.parse(JSON.stringify(k.codage));
    const r = {};
    r.message = C.construireMessageCaracteristiques("DOC", k.texte || "texte", codage, k.regles, k.extraits || [], k.commentaire || null, k.mode);
    const an = C.analyserCaracteristiques(k.reponse, k.regles);
    r.analyse = an;
    if (an.ok && an.aCorriger && k.reponseCorrection !== undefined) {
      r.messageCorrection = C.construireMessageCorrectionCaracteristiques(an, k.regles);
      r.correction = C.appliquerCorrectionCaracteristiques(an, k.reponseCorrection, k.regles);
    }
    const app = C.appliquerCaracteristiques(codage, an, { appel_llm: "appel-test" }, k.regles);
    r.codage = codage; r.explication = app.explication; r.aRevoir = C.regleARevoir(codage);
    r.enregistre = C.nettoyerPourEnregistrement(codage);
    if (k.nouvellePP !== undefined) { codage.ensembles.find((e) => e.categorie === "pathologie_principale").code = k.nouvellePP; r.aRevoirApres = C.regleARevoir(codage); }
    sortie.caracteristiques = r;
  }
  if (cas.message) sortie.message = C.construireMessageUtilisateur("DOC", cas.message.texte, cas.passages, cas.message.contexte);
  process.stdout.write(JSON.stringify(sortie));
});
