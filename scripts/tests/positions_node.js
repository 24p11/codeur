// Pont pour le test de la convention de positions : lit des cas JSON sur l'entrée standard, applique
// web/positions.js (le même fichier que la page) et renvoie les résultats en JSON.
"use strict";
const path = require("path");
const P = require(path.join(__dirname, "..", "..", "web", "positions.js"));
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
    }
    return r;
  });
  process.stdout.write(JSON.stringify(sorties));
});
