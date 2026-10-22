// Pont pour les tests du codage : lit un cas JSON sur l'entrée standard, applique web/codage.js et renvoie le résultat.
"use strict";
const path = require("path");
const C = require(path.join(__dirname, "..", "..", "web", "codage.js"));
let entree = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (d) => { entree += d; });
process.stdin.on("end", () => {
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
  if (cas.repete) sortie.repete = C.assemblerAppelRepete(cas.repete.retenu, cas.repete.nouveau, "ia_humain");
  if (cas.preparer) { const courant = JSON.parse(JSON.stringify(cas.preparer.courant)); const r = C.preparerAppelRepete(courant, cas.preparer.passages, null); sortie.preparer = { ...r, courant }; }
  if (cas.compteursSeuls) sortie.compteurs = C.compteurs(cas.compteursSeuls.avant, cas.compteursSeuls.apres);
  if (cas.message) sortie.message = C.construireMessageUtilisateur("DOC", cas.message.texte, cas.passages, cas.message.contexte);
  process.stdout.write(JSON.stringify(sortie));
});
