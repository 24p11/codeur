// codeur — mise en forme « sans retirer un caractère » du texte des dossiers (CRH synthétiques en markdown).
// Le texte affiché reste exactement le texte de référence : on ne fait que repérer des intervalles à décorer
// (titres, gras, marques, traits), que la page enveloppe dans des <span> stylés. Les positions (docs/page_web.md)
// restent celles du texte. Fichier partagé avec Node pour le test de positions (scripts/tests/tester_positions.py).
(function (racine) {
  "use strict";
  // Intervalles en index UTF-16 (ceux des chaînes JavaScript) : [debut, fin, classe].
  function decorations(texte) {
    const res = [];
    let debut = 0;
    while (debut <= texte.length) {
      let fin = texte.indexOf("\n", debut);
      if (fin < 0) fin = texte.length;
      const ligne = texte.slice(debut, fin);
      const titre = /^(#{1,6})[ \t]+\S/.exec(ligne);
      if (titre) {
        res.push([debut, fin, "md-titre"]);
        res.push([debut, debut + titre[1].length, "md-marque"]);
      } else if (/^[ \t]*-{3,}[ \t]*$/.test(ligne)) {
        res.push([debut, fin, "md-trait"]);
      }
      const gras = /\*\*(?=\S)([^*\n]+?)(?<=\S)\*\*/g;
      let m;
      while ((m = gras.exec(ligne))) {
        const a = debut + m.index, b = a + m[0].length;
        res.push([a, a + 2, "md-marque"]);
        res.push([a + 2, b - 2, "md-gras"]);
        res.push([b - 2, b, "md-marque"]);
      }
      debut = fin + 1;
    }
    return res;
  }
  // Les bornes de découpe du texte : 0, sa longueur, et chaque début ou fin des intervalles donnés
  // (tableaux dont les deux premiers éléments sont debut et fin, en UTF-16).
  function bornes(texte, intervalles) {
    const s = new Set([0, texte.length]);
    for (const it of intervalles) { s.add(it[0]); s.add(it[1]); }
    return [...s].sort((a, b) => a - b);
  }
  const api = { decorations, bornes };
  racine.Markdown = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
