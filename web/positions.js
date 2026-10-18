// codeur — convention de positions des passages (docs/page_web.md, « Convention de positions »).
//
// Une position est un nombre de POINTS DE CODE Unicode depuis le début du texte de référence :
// `debut` inclus, `fin` exclu, de sorte que texte[debut:fin] en Python, substr() en PostgreSQL et
// extraire() ici donnent exactement le même texte cité. JavaScript compte nativement en unités UTF-16
// (un caractère hors du plan de base, comme un émoji, en occupe deux) : ce fichier fait la conversion.
//
// Fichier partagé : utilisé par la page (variable globale CodeurPositions) et par le test
// scripts/tests/tester_positions.py (via Node, module.exports).
(function (racine) {
  "use strict";

  // Tables de correspondance pour un texte : u16VersCp[i] = nombre de points de code avant l'unité UTF-16 i ;
  // cpVersU16[k] = index de l'unité UTF-16 où commence le point de code k. Calculées une fois par texte.
  function tables(texte) {
    const n = texte.length;
    const u16VersCp = new Int32Array(n + 1);
    const cpVersU16 = [];
    let cp = 0;
    for (let i = 0; i < n; i++) {
      u16VersCp[i] = cp;
      const c = texte.charCodeAt(i);
      const debutPaire = c >= 0xd800 && c <= 0xdbff && i + 1 < n &&
        texte.charCodeAt(i + 1) >= 0xdc00 && texte.charCodeAt(i + 1) <= 0xdfff;
      if (!(c >= 0xdc00 && c <= 0xdfff && i > 0 && texte.charCodeAt(i - 1) >= 0xd800 && texte.charCodeAt(i - 1) <= 0xdbff)) {
        cpVersU16.push(i); // début d'un point de code
        cp += 1;
      }
      if (debutPaire) { /* la seconde unité de la paire est traitée au tour suivant */ }
    }
    u16VersCp[n] = cp;
    cpVersU16.push(n);
    return { u16VersCp, cpVersU16, longueurCp: cp };
  }

  const cache = new WeakMap();
  function tablesDe(texte) {
    // Les chaînes ne sont pas des objets : on garde un petit cache par valeur via un objet enveloppe.
    if (cache.has(tablesDe) && cache.get(tablesDe).texte === texte) return cache.get(tablesDe).t;
    const t = tables(texte);
    cache.set(tablesDe, { texte, t });
    return t;
  }

  function longueur(texte) { return tablesDe(texte).longueurCp; }
  function u16VersPoints(texte, index16) {
    const t = tablesDe(texte);
    if (index16 < 0 || index16 > texte.length) throw new RangeError("index UTF-16 hors du texte");
    return t.u16VersCp[index16];
  }
  function pointsVersU16(texte, indexCp) {
    const t = tablesDe(texte);
    if (indexCp < 0 || indexCp > t.longueurCp) throw new RangeError("position hors du texte");
    return t.cpVersU16[indexCp];
  }
  // Le texte cité entre deux positions (points de code).
  function extraire(texte, debut, fin) {
    return texte.slice(pointsVersU16(texte, debut), pointsVersU16(texte, fin));
  }
  // Construit un passage à partir d'indices UTF-16 (ce que donne une sélection dans le navigateur).
  // Retourne null si la sélection est vide ou ne contient que des blancs.
  function passageDepuisU16(texte, debut16, fin16) {
    if (debut16 > fin16) [debut16, fin16] = [fin16, debut16];
    const debut = u16VersPoints(texte, debut16), fin = u16VersPoints(texte, fin16);
    if (fin <= debut) return null;
    const cite = extraire(texte, debut, fin);
    if (!cite.trim()) return null;
    return { debut, fin, texte: cite };
  }
  // Contrôle : le texte cité est-il exactement l'extrait du texte de référence aux positions indiquées ?
  function verifier(texte, passage) {
    if (!passage || typeof passage.debut !== "number" || typeof passage.fin !== "number" || typeof passage.texte !== "string") return false;
    if (!Number.isInteger(passage.debut) || !Number.isInteger(passage.fin) || passage.debut < 0 || passage.fin > longueur(texte) || passage.debut >= passage.fin) return false;
    return extraire(texte, passage.debut, passage.fin) === passage.texte;
  }

  const api = { longueur, u16VersPoints, pointsVersU16, extraire, passageDepuisU16, verifier };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else racine.CodeurPositions = api;
})(typeof window !== "undefined" ? window : globalThis);
