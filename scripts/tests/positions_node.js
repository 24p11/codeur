// Pont pour le test de la convention de positions : lit des cas JSON sur l'entrée standard, applique
// web/positions.js (le même fichier que la page) et renvoie les résultats en JSON.
"use strict";
const path = require("path");
const P = require(path.join(__dirname, "..", "..", "web", "positions.js"));
const M = require(path.join(__dirname, "..", "..", "web", "markdown.js"));
let entree = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (d) => { entree += d; });
process.stdin.on("end", () => {
  const cas = JSON.parse(entree);
  const sorties = cas.map((c) => {
    const r = { longueur: P.longueur(c.texte) };
    if (c.debut16 !== undefined) {
      const p = P.passageDepuisU16(c.texte, c.debut16, c.fin16);
      r.passage = p;
    }
    if (c.debut !== undefined) {
      r.extrait = P.extraire(c.texte, c.debut, c.fin);
      r.verif = P.verifier(c.texte, { debut: c.debut, fin: c.fin, texte: c.attendu });
      r.verif_faux = P.verifier(c.texte, { debut: c.debut, fin: c.fin, texte: c.attendu + "x" });
      // Mise en forme (web/markdown.js) : le découpage en morceaux, avec les décorations et le passage, doit
      // restituer le texte entier, et les morceaux couverts par le passage doivent restituer exactement l'extrait.
      const d16 = P.pointsVersU16(c.texte, c.debut), f16 = P.pointsVersU16(c.texte, c.fin);
      const decos = M.decorations(c.texte);
      const bornes = M.bornes(c.texte, [...decos, [d16, f16]]);
      let tout = "", dans = "";
      for (let i = 0; i + 1 < bornes.length; i++) {
        const m = c.texte.slice(bornes[i], bornes[i + 1]);
        tout += m;
        if (d16 <= bornes[i] && bornes[i + 1] <= f16) dans += m;
      }
      r.decoupage_ok = tout === c.texte && dans === c.texte.slice(d16, f16) && dans === r.extrait;
      r.nb_decorations = decos.length;
      r.classes = [...new Set(decos.map((x) => x[2]))].sort();
    }
    return r;
  });
  process.stdout.write(JSON.stringify(sorties));
});
