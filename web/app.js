// codeur — page web (lot A1). JavaScript simple, sans outil de construction.
// Étape 3 : connexion par lien envoyé par courriel, déconnexion.
// Étape 4 : mention d'information, accord, fiche d'inscription, profil.
"use strict";

(function () {
  const cfg = window.CODEUR_CONFIG;
  const $ = (id) => document.getElementById(id);
  const STATUTS = { medecin_dim: "Médecin DIM", tim: "TIM", autre_medecin: "Autre médecin", interne: "Interne", etudiant: "Étudiant", autre: "Autre" };

  // --- Écrans : un seul visible à la fois --------------------------------------------------------
  const ecrans = ["ecran-chargement", "ecran-connexion", "ecran-mention", "ecran-inscription", "ecran-profil", "ecran-liste", "ecran-dossier", "ecran-erreur"];
  function montrer(id) {
    for (const e of ecrans) $(e).hidden = e !== id;
    window.scrollTo(0, 0);
  }
  function erreur(message) {
    $("message-erreur").textContent = message;
    montrer("ecran-erreur");
  }
  function message(id, texte, alerte) {
    const el = $(id);
    el.hidden = !texte;
    el.className = "message" + (alerte ? " alerte" : "");
    el.textContent = texte || "";
  }

  // --- Client Supabase (clé publique uniquement) ----------------------------------------------------
  if (!window.supabase || !cfg || !cfg.supabaseUrl || !cfg.supabaseKey) {
    erreur("La configuration de la page ou la bibliothèque Supabase n'a pas pu être chargée.");
    return;
  }
  const base = window.supabase.createClient(cfg.supabaseUrl, cfg.supabaseKey, {
    auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true },
  });
  $("version-page").textContent = "codeur " + cfg.versionPage;
  const adresseRetour = window.location.origin + window.location.pathname;

  // --- État de l'application -------------------------------------------------------------------------
  const etat = { utilisateur: null, profil: null };

  // --- Connexion / déconnexion ----------------------------------------------------------------------
  $("formulaire-connexion").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const email = $("champ-email").value.trim();
    $("bouton-lien").disabled = true;
    message("message-connexion", "Envoi en cours…");
    const { error } = await base.auth.signInWithOtp({ email, options: { emailRedirectTo: adresseRetour } });
    if (error) {
      message("message-connexion", "Le lien n'a pas pu être envoyé : " + error.message +
        ". Si le problème persiste, demandez un lien au responsable du projet.", true);
      $("bouton-lien").disabled = false;
      return;
    }
    message("message-connexion", "Un courriel contenant votre lien de connexion a été envoyé à " + email +
      ". Ouvrez-le et cliquez sur le lien ; il est valable une heure et ne sert qu'une fois.");
  });
  $("bouton-deconnexion").addEventListener("click", async () => {
    await base.auth.signOut();
    window.location.replace(adresseRetour);
  });
  $("bouton-recharger").addEventListener("click", () => window.location.replace(adresseRetour));

  // --- Mention d'information et accord ---------------------------------------------------------------
  // La page affiche le fichier docs/mention_information.md (copié dans web/ à la publication) jusqu'au
  // titre « Votre accord » ; les cases à cocher et le bouton sont ceux de la page, et la section
  // « Notes pour la mise en œuvre » n'est jamais affichée.
  async function afficherMention() {
    try {
      const rep = await fetch("mention_information.md", { cache: "no-store" });
      if (!rep.ok) throw new Error("HTTP " + rep.status);
      let md = await rep.text();
      const coupe = md.search(/^## Votre accord/m);
      if (coupe >= 0) md = md.slice(0, coupe);
      $("mention-contenu").innerHTML = window.marked ? window.marked.parse(md) : "<pre>" + md.replace(/</g, "&lt;") + "</pre>";
    } catch (e) {
      $("mention-contenu").innerHTML = "<p class='message alerte'>La mention d'information n'a pas pu être chargée (" + e.message + "). Rechargez la page.</p>";
    }
    $("case-donnees-reelles").checked = false;
    $("case-recherche").checked = false;
    $("bouton-vers-inscription").disabled = true;
    montrer("ecran-mention");
  }
  function verifierCases() {
    $("bouton-vers-inscription").disabled = !($("case-donnees-reelles").checked && $("case-recherche").checked);
  }
  $("case-donnees-reelles").addEventListener("change", verifierCases);
  $("case-recherche").addEventListener("change", verifierCases);
  $("bouton-vers-inscription").addEventListener("click", () => {
    if ($("bouton-vers-inscription").disabled) return;
    etat.accordLe = new Date().toISOString(); // le moment où les deux cases étaient cochées
    montrer("ecran-inscription");
  });

  // --- Fiche d'inscription (crée la ligne de profils) --------------------------------------------------
  $("formulaire-inscription").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (!etat.accordLe) { await afficherMention(); return; }
    $("bouton-inscription").disabled = true;
    message("message-inscription", "");
    const ligne = {
      id: etat.utilisateur.id,
      nom: $("champ-nom").value.trim(),
      prenom: $("champ-prenom").value.trim(),
      statut: $("champ-statut").value,
      etablissement: $("champ-etablissement").value.trim(),
      accord_le: etat.accordLe,
    };
    const { data, error } = await base.from("profils").insert(ligne).select().single();
    if (error) {
      message("message-inscription", "L'enregistrement a échoué : " + error.message, true);
      $("bouton-inscription").disabled = false;
      return;
    }
    etat.profil = data;
    afficherListe();
  });

  // --- Profil : consultation et modification -----------------------------------------------------------
  function afficherProfil() {
    const p = etat.profil;
    $("profil-nom").value = p.nom;
    $("profil-prenom").value = p.prenom;
    $("profil-statut").value = p.statut;
    $("profil-etablissement").value = p.etablissement;
    $("profil-infos").textContent = "Adresse : " + etat.utilisateur.email + " — accord donné le " +
      new Date(p.accord_le).toLocaleString("fr-FR") + " — statut : " + (STATUTS[p.statut] || p.statut);
    message("message-profil", "");
    montrer("ecran-profil");
  }
  $("bouton-profil").addEventListener("click", () => { if (etat.profil) afficherProfil(); });
  $("bouton-profil-retour").addEventListener("click", afficherListe);
  $("formulaire-profil").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const modifs = {
      nom: $("profil-nom").value.trim(), prenom: $("profil-prenom").value.trim(),
      statut: $("profil-statut").value, etablissement: $("profil-etablissement").value.trim(),
    };
    const { data, error } = await base.from("profils").update(modifs).eq("id", etat.utilisateur.id).select().single();
    if (error) { message("message-profil", "La modification a échoué : " + error.message, true); return; }
    etat.profil = data;
    message("message-profil", "Profil enregistré.");
    $("profil-infos").textContent = "Adresse : " + etat.utilisateur.email + " — accord donné le " +
      new Date(data.accord_le).toLocaleString("fr-FR") + " — statut : " + (STATUTS[data.statut] || data.statut);
  });

  // --- Liste des dossiers (étape 5) ------------------------------------------------------------------
  // La liste lit la vue dossiers_disponibles (dernière version, sans les dossiers à corriger, sans texte
  // ni champ nettoyage). Les valeurs brutes de la base sont mises en forme pour l'affichage seulement.
  const PAR_PAGE = 50;
  const liste = { page: 0, total: 0, filtres: { specialite: "", type: "", id: "" }, valeursChargees: false };

  function enClair(valeur) {
    if (!valeur) return "—";
    const bas = valeur.toLowerCase();
    return bas.charAt(0).toUpperCase() + bas.slice(1);
  }
  function nombre(n) { return new Intl.NumberFormat("fr-FR").format(n); }

  async function chargerValeursRecherche() {
    if (liste.valeursChargees) return;
    const { data, error } = await base.from("dossiers_disponibles").select("specialite, type_prise_en_charge").limit(10000);
    if (error) { message("message-liste", "Les valeurs de recherche n'ont pas pu être chargées : " + error.message, true); return; }
    const specialites = new Map(), types = new Map();
    for (const d of data) {
      if (d.specialite) specialites.set(d.specialite, (specialites.get(d.specialite) || 0) + 1);
      if (d.type_prise_en_charge) types.set(d.type_prise_en_charge, (types.get(d.type_prise_en_charge) || 0) + 1);
    }
    const remplir = (select, valeurs) => {
      for (const [brut, n] of [...valeurs.entries()].sort((a, b) => a[0].localeCompare(b[0], "fr"))) {
        const opt = document.createElement("option");
        opt.value = brut; opt.textContent = enClair(brut) + " (" + nombre(n) + ")";
        select.appendChild(opt);
      }
    };
    remplir($("filtre-specialite"), specialites);
    remplir($("filtre-type"), types);
    liste.valeursChargees = true;
  }

  async function chargerPage() {
    message("message-liste", "");
    let req = base.from("dossiers_disponibles")
      .select("id, id_source, specialite, type_prise_en_charge, nb_documents_origine, longueur", { count: "exact" })
      .order("id_source");
    const f = liste.filtres;
    if (f.specialite) req = req.eq("specialite", f.specialite);
    if (f.type) req = req.eq("type_prise_en_charge", f.type);
    if (f.id) req = req.ilike("id_source", "%" + f.id.replace(/[%_]/g, "") + "%");
    const debut = liste.page * PAR_PAGE;
    const { data, error, count } = await req.range(debut, debut + PAR_PAGE - 1);
    if (error) { message("message-liste", "La liste n'a pas pu être chargée : " + error.message, true); return; }
    liste.total = count || 0;
    const corps = $("tableau-dossiers").querySelector("tbody");
    corps.textContent = "";
    for (const d of data) {
      const tr = document.createElement("tr");
      const cellules = [
        ["ident", d.id_source], ["", enClair(d.specialite)], ["", enClair(d.type_prise_en_charge)],
        ["num", nombre(d.nb_documents_origine)], ["num", nombre(d.longueur) + " car."],
      ];
      for (const [classe, texte] of cellules) {
        const td = document.createElement("td"); td.className = classe; td.textContent = texte; tr.appendChild(td);
      }
      const td = document.createElement("td");
      const bouton = document.createElement("button");
      bouton.textContent = "Ouvrir"; bouton.className = "secondaire"; bouton.style.marginTop = "0";
      bouton.addEventListener("click", () => ouvrirDossier(d.id));
      td.appendChild(bouton); tr.appendChild(td);
      corps.appendChild(tr);
    }
    const nbPages = Math.max(1, Math.ceil(liste.total / PAR_PAGE));
    $("liste-resume").textContent = liste.total ? nombre(liste.total) + " dossier(s) disponible(s)" : "Aucun dossier ne correspond à la recherche.";
    $("page-position").textContent = "Page " + (liste.page + 1) + " sur " + nbPages;
    $("page-precedente").disabled = liste.page === 0;
    $("page-suivante").disabled = liste.page + 1 >= nbPages;
  }

  async function afficherListe() {
    montrer("ecran-liste");
    await chargerValeursRecherche();
    await chargerPage();
  }
  $("formulaire-recherche").addEventListener("submit", (ev) => {
    ev.preventDefault();
    liste.filtres = { specialite: $("filtre-specialite").value, type: $("filtre-type").value, id: $("filtre-id").value.trim() };
    liste.page = 0;
    chargerPage();
  });
  $("bouton-effacer-recherche").addEventListener("click", () => {
    $("filtre-specialite").value = ""; $("filtre-type").value = ""; $("filtre-id").value = "";
    liste.filtres = { specialite: "", type: "", id: "" }; liste.page = 0;
    chargerPage();
  });
  $("page-precedente").addEventListener("click", () => { if (liste.page > 0) { liste.page -= 1; chargerPage(); } });
  $("page-suivante").addEventListener("click", () => { liste.page += 1; chargerPage(); });

  // --- Écran du dossier : affichage du texte et surlignage (étape 6) ------------------------------------
  // Le texte affiché est la chaîne de la base, sans transformation (white-space: pre-wrap). Les positions des
  // passages sont des points de code (web/positions.js ; docs/page_web.md). Les surlignages ne sont pas
  // enregistrés dans la base à ce stade : ils restent dans le navigateur (sauvegarde locale, protégée).
  const P = window.CodeurPositions;
  const dossier = { doc: null, ensembles: [], prochainNumero: 1, actif: null, selection: null };

  // Sauvegarde locale : toute lecture ou écriture est protégée ; la page fonctionne sans.
  function cleLocale() { return "codeur.surlignages." + etat.utilisateur.id + "." + dossier.doc.id; }
  function sauvegarderLocal() {
    try {
      const contenu = { version: 1, document: dossier.doc.id, empreinte: dossier.doc.empreinte, prochainNumero: dossier.prochainNumero,
                        ensembles: dossier.ensembles, enregistreLe: new Date().toISOString() };
      window.localStorage.setItem(cleLocale(), JSON.stringify(contenu));
      $("sauvegarde-etat").textContent = "Sauvegardé dans ce navigateur à " + new Date().toLocaleTimeString("fr-FR") + ".";
    } catch (e) {
      $("sauvegarde-etat").textContent = "Sauvegarde locale indisponible dans ce navigateur : vos surlignages seront perdus à la fermeture.";
    }
  }
  function chargerLocal() {
    try {
      const brut = window.localStorage.getItem(cleLocale());
      if (!brut) return null;
      const c = JSON.parse(brut);
      if (c.empreinte !== dossier.doc.empreinte) {
        message("message-dossier", "Des surlignages enregistrés dans ce navigateur correspondent à une autre version de ce texte : ils ont été ignorés.", true);
        return null;
      }
      const ensembles = (c.ensembles || []).map((e) => ({ numero: e.numero, passages: (e.passages || []).filter((p) => P.verifier(dossier.doc.texte, p)) }));
      return { ensembles, prochainNumero: c.prochainNumero || (Math.max(0, ...ensembles.map((e) => e.numero)) + 1) };
    } catch (e) {
      return null;
    }
  }
  function effacerLocal() { try { window.localStorage.removeItem(cleLocale()); } catch (e) { /* indisponible */ } }

  async function ouvrirDossier(id) {
    message("message-liste", "");
    const { data, error } = await base.from("documents")
      .select("id, id_source, version, specialite, type_prise_en_charge, texte, empreinte, nb_documents_origine").eq("id", id).single();
    if (error) { message("message-liste", "Le dossier n'a pas pu être chargé : " + error.message, true); return; }
    dossier.doc = data; dossier.ensembles = []; dossier.prochainNumero = 1; dossier.actif = null; dossier.selection = null;
    $("dossier-titre").textContent = data.id_source;
    $("dossier-infos").textContent = enClair(data.specialite) + " — " + enClair(data.type_prise_en_charge) + " — " +
      nombre(data.nb_documents_origine) + " document(s) d'origine — " + nombre(P.longueur(data.texte)) + " caractères — version " + data.version;
    message("message-dossier", "");
    $("sauvegarde-etat").textContent = "";
    const local = chargerLocal();
    if (local && local.ensembles.length) {
      dossier.ensembles = local.ensembles; dossier.prochainNumero = local.prochainNumero;
      $("sauvegarde-etat").textContent = "Surlignages retrouvés dans ce navigateur.";
    }
    montrer("ecran-dossier");
    rendreTexte(); rendrePanneau(); cacherBarre();
  }

  // Rendu du texte : découpe aux frontières des passages ; chaque morceau est soit un nœud texte, soit un <mark>
  // dont le contenu est exactement le morceau de texte. Aucun caractère n'est ajouté ni retiré.
  function rendreTexte() {
    const texte = dossier.doc.texte;
    const frontieres = new Set([0, texte.length]);
    const couvertures = []; // [debut16, fin16, numero]
    for (const e of dossier.ensembles) for (const p of e.passages) {
      const d = P.pointsVersU16(texte, p.debut), f = P.pointsVersU16(texte, p.fin);
      frontieres.add(d); frontieres.add(f); couvertures.push([d, f, e.numero]);
    }
    const bornes = [...frontieres].sort((a, b) => a - b);
    const bloc = $("texte-dossier");
    bloc.textContent = "";
    for (let i = 0; i + 1 < bornes.length; i++) {
      const d = bornes[i], f = bornes[i + 1];
      const morceau = texte.slice(d, f);
      const nums = couvertures.filter(([cd, cf]) => cd <= d && f <= cf).map((c) => c[2]);
      if (!nums.length) { bloc.appendChild(document.createTextNode(morceau)); continue; }
      const m = document.createElement("mark");
      m.className = "surl c" + (nums[0] % 8) + (nums.length > 1 ? " chevauche" : "") + (nums.includes(dossier.actif) ? " actif" : "");
      m.dataset.ensembles = nums.join(",");
      m.title = "Ensemble" + (nums.length > 1 ? "s " : " ") + nums.join(", ");
      m.textContent = morceau;
      bloc.appendChild(m);
    }
  }
  $("texte-dossier").addEventListener("click", (ev) => {
    const m = ev.target.closest("mark.surl");
    if (!m || window.getSelection().toString()) return;
    const nums = m.dataset.ensembles.split(",").map(Number);
    const i = nums.indexOf(dossier.actif);
    choisirEnsemble(nums[(i + 1) % nums.length], false);
  });

  function rendrePanneau() {
    const ol = $("liste-ensembles");
    ol.textContent = "";
    if (!dossier.ensembles.length) {
      const li = document.createElement("li"); li.className = "discret"; li.textContent = "Aucun ensemble pour l'instant."; ol.appendChild(li);
    }
    for (const e of dossier.ensembles) {
      const li = document.createElement("li");
      li.className = "ensemble c" + (e.numero % 8) + (e.numero === dossier.actif ? " actif" : "");
      li.addEventListener("click", (ev) => { if (!ev.target.closest("button")) choisirEnsemble(e.numero, true); });
      const tete = document.createElement("div"); tete.className = "ensemble-tete";
      const titre = document.createElement("span"); titre.textContent = "Ensemble " + e.numero + " (" + e.passages.length + " passage" + (e.passages.length > 1 ? "s" : "") + ")";
      const suppr = document.createElement("button"); suppr.className = "secondaire"; suppr.textContent = "Supprimer";
      suppr.addEventListener("click", () => supprimerEnsemble(e.numero));
      tete.append(titre, suppr); li.appendChild(tete);
      for (const [k, p] of e.passages.entries()) {
        const div = document.createElement("div"); div.className = "passage";
        const cite = document.createElement("span"); cite.className = "cite";
        const q = document.createElement("q"); q.textContent = p.texte.length > 90 ? p.texte.slice(0, 87) + "…" : p.texte;
        cite.append(q, document.createTextNode(" [" + p.debut + "–" + p.fin + "]"));
        const ret = document.createElement("button"); ret.className = "secondaire"; ret.textContent = "Retirer";
        ret.addEventListener("click", () => retirerPassage(e.numero, k));
        div.append(cite, ret); li.appendChild(div);
      }
      ol.appendChild(li);
    }
    $("bouton-ajouter-ensemble").hidden = dossier.actif === null;
    $("barre-numero").textContent = dossier.actif === null ? "" : dossier.actif;
  }

  function choisirEnsemble(numero, defiler) {
    dossier.actif = numero;
    rendreTexte(); rendrePanneau();
    if (defiler) {
      const m = $("texte-dossier").querySelector("mark.surl.actif");
      if (m) m.scrollIntoView({ block: "center", behavior: "smooth" });
    }
  }

  // Sélection à la souris : position = somme des longueurs des morceaux de texte qui précèdent, dans le bloc.
  function positionDansBloc(noeud, decalage) {
    const bloc = $("texte-dossier");
    if (!bloc.contains(noeud)) return null;
    let total = 0;
    const marcheur = document.createTreeWalker(bloc, NodeFilter.SHOW_TEXT);
    let n;
    while ((n = marcheur.nextNode())) {
      if (n === noeud) return total + decalage;
      if (noeud.nodeType === Node.ELEMENT_NODE && noeud.contains(n) && Array.prototype.indexOf.call(noeud.childNodes, n) >= decalage) return total;
      total += n.nodeValue.length;
    }
    return noeud.nodeType === Node.ELEMENT_NODE ? total : null;
  }
  function lireSelection() {
    const sel = window.getSelection();
    if (!sel || sel.rangeCount === 0 || sel.isCollapsed) return null;
    const r = sel.getRangeAt(0);
    const d = positionDansBloc(r.startContainer, r.startOffset), f = positionDansBloc(r.endContainer, r.endOffset);
    if (d === null || f === null) return null;
    const passage = P.passageDepuisU16(dossier.doc.texte, d, f);
    if (!passage) return null;
    // Contrôle 1 (strict) : le texte cité est exactement l'extrait du texte de référence aux positions indiquées.
    if (!P.verifier(dossier.doc.texte, passage)) return { refus: "positions incohérentes avec le texte de référence" };
    // Contrôle 2 (de bon sens) : l'extrait calculé correspond à ce que le navigateur dit avoir sélectionné,
    // aux blancs près (les navigateurs ne restituent pas tous les sauts de ligne de la même façon).
    const compact = (t) => t.replace(/\s+/g, " ").trim();
    if (compact(passage.texte) !== compact(sel.toString())) {
      return { refus: "le texte sélectionné ne correspond pas à l'extrait calculé aux positions " + passage.debut + "–" + passage.fin };
    }
    return { passage, rect: r.getBoundingClientRect() };
  }
  function montrerBarre(rect) {
    const barre = $("barre-selection");
    barre.hidden = false;
    const x = Math.max(8, Math.min(window.innerWidth - barre.offsetWidth - 8, rect.left + window.scrollX));
    const y = rect.bottom + window.scrollY + 6;
    barre.style.left = x + "px"; barre.style.top = y + "px";
  }
  function cacherBarre() { $("barre-selection").hidden = true; dossier.selection = null; }
  document.addEventListener("selectionchange", () => {
    if ($("ecran-dossier").hidden) return;
    const res = lireSelection();
    if (!res || res.refus) { cacherBarre(); if (res && res.refus) message("message-dossier", "Passage refusé : " + res.refus + ".", true); return; }
    message("message-dossier", "");
    dossier.selection = res.passage;
    montrerBarre(res.rect);
  });

  function ajouterPassage(numero, passage) {
    if (!P.verifier(dossier.doc.texte, passage)) { message("message-dossier", "Passage refusé : contrôle des positions en échec.", true); return; }
    const e = dossier.ensembles.find((x) => x.numero === numero);
    if (!e) return;
    if (e.passages.some((p) => p.debut === passage.debut && p.fin === passage.fin)) { message("message-dossier", "Ce passage est déjà dans l'ensemble " + numero + ".", true); return; }
    e.passages.push(passage); e.passages.sort((a, b) => a.debut - b.debut);
    dossier.actif = numero;
    window.getSelection().removeAllRanges(); cacherBarre();
    rendreTexte(); rendrePanneau(); sauvegarderLocal();
  }
  function nouvelEnsemble() {
    if (!dossier.selection) return;
    const numero = dossier.prochainNumero++; // un numéro attribué ne change jamais
    dossier.ensembles.push({ numero, passages: [] });
    ajouterPassage(numero, dossier.selection);
  }
  function ajouterAuSelectionne() {
    if (!dossier.selection || dossier.actif === null) return;
    ajouterPassage(dossier.actif, dossier.selection);
  }
  function retirerPassage(numero, index) {
    const e = dossier.ensembles.find((x) => x.numero === numero);
    if (!e) return;
    e.passages.splice(index, 1);
    if (!e.passages.length) return supprimerEnsemble(numero);
    rendreTexte(); rendrePanneau(); sauvegarderLocal();
  }
  function supprimerEnsemble(numero) {
    dossier.ensembles = dossier.ensembles.filter((x) => x.numero !== numero);
    if (dossier.actif === numero) dossier.actif = null;
    rendreTexte(); rendrePanneau(); sauvegarderLocal();
  }
  $("bouton-nouvel-ensemble").addEventListener("mousedown", (ev) => ev.preventDefault());
  $("bouton-ajouter-ensemble").addEventListener("mousedown", (ev) => ev.preventDefault());
  $("bouton-nouvel-ensemble").addEventListener("click", nouvelEnsemble);
  $("bouton-ajouter-ensemble").addEventListener("click", ajouterAuSelectionne);
  $("bouton-retour-liste").addEventListener("click", () => { cacherBarre(); afficherListe(); });
  let confirmationEffacement = null;
  $("bouton-tout-effacer").addEventListener("click", () => {
    const b = $("bouton-tout-effacer");
    if (confirmationEffacement) { clearTimeout(confirmationEffacement); confirmationEffacement = null; b.textContent = "Tout effacer";
      dossier.ensembles = []; dossier.actif = null; dossier.prochainNumero = 1; effacerLocal();
      rendreTexte(); rendrePanneau(); $("sauvegarde-etat").textContent = "Surlignages effacés."; return; }
    b.textContent = "Confirmer l'effacement ?";
    confirmationEffacement = setTimeout(() => { confirmationEffacement = null; b.textContent = "Tout effacer"; }, 4000);
  });
  // Raccourcis N et A : seulement sur l'écran du dossier, jamais dans un champ de saisie.
  document.addEventListener("keydown", (ev) => {
    if ($("ecran-dossier").hidden || ev.ctrlKey || ev.metaKey || ev.altKey) return;
    const cible = ev.target;
    if (cible && (cible.tagName === "INPUT" || cible.tagName === "SELECT" || cible.tagName === "TEXTAREA" || cible.isContentEditable)) return;
    if (ev.key === "n" || ev.key === "N") { ev.preventDefault(); nouvelEnsemble(); }
    if (ev.key === "a" || ev.key === "A") { ev.preventDefault(); ajouterAuSelectionne(); }
  });

  // --- Après connexion : profil existant ou parcours d'inscription --------------------------------------
  async function demarrer(session) {
    const connecte = !!(session && session.user);
    $("utilisateur-courant").hidden = !connecte;
    $("bouton-deconnexion").hidden = !connecte;
    $("bouton-profil").hidden = true;
    if (!connecte) {
      etat.utilisateur = null; etat.profil = null;
      $("formulaire-connexion").hidden = false;
      message("message-connexion", "");
      montrer("ecran-connexion");
      return;
    }
    etat.utilisateur = session.user;
    $("utilisateur-courant").textContent = session.user.email;
    const { data, error } = await base.from("profils").select("*").eq("id", session.user.id).maybeSingle();
    if (error) { erreur("Impossible de lire votre profil : " + error.message); return; }
    etat.profil = data;
    if (!data) { await afficherMention(); return; }
    $("bouton-profil").hidden = false;
    afficherListe();
  }

  let sessionCourante = null;
  base.auth.onAuthStateChange((evenement, session) => {
    const avant = sessionCourante && sessionCourante.user ? sessionCourante.user.id : null;
    const apres = session && session.user ? session.user.id : null;
    sessionCourante = session;
    if (evenement === "SIGNED_OUT" || avant !== apres) demarrer(session);
  });
  base.auth.getSession().then(({ data, error }) => {
    if (error) { erreur("Impossible de vérifier la session : " + error.message); return; }
    sessionCourante = data.session;
    demarrer(data.session);
    if (window.location.hash && window.location.hash.includes("access_token")) {
      history.replaceState(null, "", adresseRetour);
    }
  });
})();
