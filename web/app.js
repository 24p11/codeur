// codeur — page web (lot A1). JavaScript simple, sans outil de construction.
// Étape 3 : connexion par lien envoyé par courriel, déconnexion.
// Étape 4 : mention d'information, accord, fiche d'inscription, profil.
"use strict";

(function () {
  const cfg = window.CODEUR_CONFIG;
  const $ = (id) => document.getElementById(id);
  const STATUTS = { medecin_dim: "Médecin DIM", tim: "TIM", autre_medecin: "Autre médecin", interne: "Interne", etudiant: "Étudiant", autre: "Autre" };

  // --- Écrans : un seul visible à la fois --------------------------------------------------------
  const ecrans = ["ecran-chargement", "ecran-connexion", "ecran-mention", "ecran-inscription", "ecran-profil", "ecran-reglages", "ecran-liste", "ecran-dossier", "ecran-erreur"];
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
  const etat = { utilisateur: null, profil: null, reglages: null };

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
  // Lit docs/mention_information.md (copié dans web/) : version (repère <!-- version: x -->) et texte à afficher
  // (jusqu'au repère <!-- fin-de-la-mention -->). Les deux repères sont obligatoires.
  const mention = { version: null, html: null, erreur: null };
  async function lireMention() {
    if (mention.html || mention.erreur) return mention;
    try {
      const rep = await fetch("mention_information.md", { cache: "no-store" });
      if (!rep.ok) throw new Error("HTTP " + rep.status);
      const md = await rep.text();
      const v = md.match(/<!--\s*version:\s*([^\s>]+)\s*-->/);
      if (!v) throw new Error("repère de version absent du fichier de la mention");
      const fin = md.search(/<!--\s*fin-de-la-mention\s*-->/);
      if (fin < 0) throw new Error("repère de fin de la mention absent du fichier");
      mention.version = v[1];
      const corps = md.slice(0, fin).replace(/<!--[\s\S]*?-->/g, "");
      mention.html = window.marked ? window.marked.parse(corps) : "<pre>" + corps.replace(/</g, "&lt;") + "</pre>";
    } catch (e) {
      mention.erreur = e.message;
    }
    return mention;
  }
  async function afficherMention(nouvelleVersion) {
    const m = await lireMention();
    if (m.erreur) { erreur("La mention d'information n'a pas pu être affichée (" + m.erreur + "). Signalez-le au responsable du projet."); return; }
    $("mention-contenu").innerHTML = (nouvelleVersion
      ? "<p class='message'>La mention d'information a été mise à jour (version " + m.version + "). Merci de la relire et de donner de nouveau votre accord.</p>" : "") + m.html;
    $("case-donnees-reelles").checked = false;
    $("case-recherche").checked = false;
    $("bouton-vers-inscription").disabled = true;
    $("bouton-vers-inscription").textContent = nouvelleVersion ? "Confirmer mon accord" : "Continuer vers la fiche d'inscription";
    etat.reacceptation = !!nouvelleVersion;
    montrer("ecran-mention");
  }
  function verifierCases() {
    $("bouton-vers-inscription").disabled = !($("case-donnees-reelles").checked && $("case-recherche").checked);
  }
  $("case-donnees-reelles").addEventListener("change", verifierCases);
  $("case-recherche").addEventListener("change", verifierCases);
  $("bouton-vers-inscription").addEventListener("click", async () => {
    if ($("bouton-vers-inscription").disabled) return;
    etat.accordDonne = true; // les deux cases étaient cochées
    if (etat.reacceptation) {
      // Nouvelle acceptation : seule voie de mise à jour de accord_le et version_mention (fonction de la base).
      $("bouton-vers-inscription").disabled = true; // un seul envoi, même en cas de double clic
      const { error } = await base.rpc("accepter_mention", { version: mention.version });
      if (error) { erreur("Votre accord n'a pas pu être enregistré : " + error.message); $("bouton-vers-inscription").disabled = false; return; }
      const { data } = await base.from("profils").select("*").eq("id", etat.utilisateur.id).single();
      etat.profil = data;
      $("bouton-profil").hidden = false;
      $("bouton-reglages").hidden = false;
      etat.reglages = lireReglages();
      afficherListe();
      return;
    }
    montrer("ecran-inscription");
  });

  // --- Fiche d'inscription (crée la ligne de profils) --------------------------------------------------
  $("formulaire-inscription").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (!etat.accordDonne) { await afficherMention(); return; }
    $("bouton-inscription").disabled = true;
    message("message-inscription", "");
    const ligne = {
      id: etat.utilisateur.id,
      nom: $("champ-nom").value.trim(),
      prenom: $("champ-prenom").value.trim(),
      statut: $("champ-statut").value,
      etablissement: $("champ-etablissement").value.trim(),
      accord_le: new Date().toISOString(), // remplacée par l'heure de la base (déclencheur)
      version_mention: mention.version,
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
      new Date(p.accord_le).toLocaleString("fr-FR") + " (mention version " + (p.version_mention || "non enregistrée") + ") — statut : " + (STATUTS[p.statut] || p.statut);
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
    const b = ev.submitter || $("formulaire-profil").querySelector("button[type=submit], button:not([type])");
    if (b) b.disabled = true;
    const { data, error } = await base.from("profils").update(modifs).eq("id", etat.utilisateur.id).select().single();
    if (b) b.disabled = false;
    if (error) { message("message-profil", "La modification a échoué : " + error.message, true); return; }
    etat.profil = data;
    message("message-profil", "Profil enregistré.");
    $("profil-infos").textContent = "Adresse : " + etat.utilisateur.email + " — accord donné le " +
      new Date(data.accord_le).toLocaleString("fr-FR") + " (mention version " + (data.version_mention || "non enregistrée") + ") — statut : " + (STATUTS[data.statut] || data.statut);
  });

  // --- Réglages de l'IA (lot A2, étape 3) -------------------------------------------------------------
  // Adresse du service, modèle et clé : dans le navigateur uniquement (stockage local, lectures et écritures
  // protégées), jamais envoyés à la base. La clé ne quitte le navigateur que vers le service du LLM.
  const REGLAGES_DEFAUT = { adresse: "https://api.mistral.ai/v1", modele: "mistral-large-latest", cle: "" };
  const CLE_REGLAGES = "codeur.reglages_llm";
  let ecranAvantReglages = "ecran-liste";
  function lireReglages() {
    try {
      const brut = window.localStorage.getItem(CLE_REGLAGES);
      if (!brut) return null;
      const r = JSON.parse(brut);
      return (r && r.adresse && r.modele && r.cle) ? r : null;
    } catch (e) { return null; }
  }
  function ecrireReglages(r) {
    try { window.localStorage.setItem(CLE_REGLAGES, JSON.stringify(r)); return true; } catch (e) { return false; }
  }
  function oublierReglages() {
    try { window.localStorage.removeItem(CLE_REGLAGES); } catch (e) { /* indisponible */ }
    etat.reglages = null;
  }
  // Fournisseur enregistré dans appels_llm : « mistral » pour api.mistral.ai, sinon le nom du serveur.
  function fournisseurDe(adresse) {
    try {
      const h = new URL(adresse).hostname.toLowerCase();
      return h === "api.mistral.ai" ? "mistral" : h;
    } catch (e) { return "inconnu"; }
  }
  // Variante d'affichage du codage (A liste simple, B encadrés de couleur) : lue dans l'ordre « valeur imposée par le
  // responsable » (à venir : table de paramètres ou colonne de profils), « choix du testeur » (navigateur), défaut A.
  const CLE_AFFICHAGE = "codeur.affichage_codage";
  function varianteAffichage() {
    const imposee = null; // réservé : valeur imposée par le responsable (lot ultérieur)
    if (imposee === "A" || imposee === "B") return imposee;
    try { const v = window.localStorage.getItem(CLE_AFFICHAGE); if (v === "A" || v === "B") return v; } catch (e) { /* indisponible */ }
    return "A";
  }
  function enregistrerVariante(v) { try { window.localStorage.setItem(CLE_AFFICHAGE, v); } catch (e) { /* indisponible */ } }
  function reglagesDepuisFormulaire() {
    return { adresse: $("reglage-adresse").value.trim().replace(/\/+$/, ""), modele: $("reglage-modele").value.trim(), cle: $("reglage-cle").value.trim() };
  }
  function afficherReglages(depuis, raison) {
    ecranAvantReglages = depuis || "ecran-liste";
    const r = etat.reglages || lireReglages() || REGLAGES_DEFAUT;
    $("reglage-adresse").value = r.adresse; $("reglage-modele").value = r.modele; $("reglage-cle").value = r.cle || "";
    $("reglage-affichage").value = varianteAffichage();
    message("message-reglages", raison || "", !!raison);
    montrer("ecran-reglages");
  }
  // Appel au format commun /chat/completions. Retourne { contenu, usage, duree_ms, modele, brut } ou lève une erreur
  // dont le message ne contient jamais la clé.
  async function appelerLLM(reglages, messages, options) {
    const corps = { model: reglages.modele, temperature: 0, messages };
    if (options && options.json) corps.response_format = { type: "json_object" };
    const debut = performance.now();
    let rep;
    try {
      rep = await fetch(reglages.adresse + "/chat/completions", {
        method: "POST", headers: { "Content-Type": "application/json", "Authorization": "Bearer " + reglages.cle }, body: JSON.stringify(corps),
      });
    } catch (e) {
      throw new Error("le service n'a pas pu être joint (" + e.message + ") : réseau, adresse du service, ou appel refusé depuis une page web");
    }
    const duree_ms = Math.round(performance.now() - debut);
    const brut = await rep.text();
    if (!rep.ok) throw new Error("le service a répondu HTTP " + rep.status + " : " + brut.replace(reglages.cle, "***").slice(0, 300));
    let donnees;
    try { donnees = JSON.parse(brut); } catch (e) { throw new Error("réponse du service illisible"); }
    const contenu = donnees && donnees.choices && donnees.choices[0] && donnees.choices[0].message ? donnees.choices[0].message.content : null;
    if (typeof contenu !== "string") throw new Error("réponse du service sans contenu");
    return { contenu, usage: donnees.usage || {}, duree_ms, modele: donnees.model || reglages.modele, brut };
  }
  $("formulaire-reglages").addEventListener("submit", (ev) => {
    ev.preventDefault();
    const r = reglagesDepuisFormulaire();
    etat.reglages = r;
    enregistrerVariante($("reglage-affichage").value);
    const ok = ecrireReglages(r);
    message("message-reglages", ok ? "Réglages enregistrés dans ce navigateur." : "Réglages conservés pour cette session seulement : le stockage de ce navigateur est indisponible, la clé sera redemandée à la prochaine ouverture.", !ok);
  });
  $("bouton-tester-llm").addEventListener("click", async () => {
    const r = reglagesDepuisFormulaire();
    if (!r.adresse || !r.modele || !r.cle) { message("message-reglages", "Renseignez l'adresse, le modèle et la clé.", true); return; }
    $("bouton-tester-llm").disabled = true;
    message("message-reglages", "Test en cours…");
    try {
      const res = await appelerLLM(r, [{ role: "user", content: "Réponds uniquement par l'objet JSON {\"ok\": true}." }], { json: true });
      message("message-reglages", "Connexion réussie : " + res.modele + " a répondu en " + res.duree_ms + " ms (" + (res.usage.total_tokens || "?") + " tokens). Fournisseur enregistré : « " + fournisseurDe(r.adresse) + " ».");
    } catch (e) {
      message("message-reglages", "Échec du test : " + e.message, true);
    }
    $("bouton-tester-llm").disabled = false;
  });
  $("bouton-oublier-reglages").addEventListener("click", () => {
    oublierReglages();
    $("reglage-adresse").value = REGLAGES_DEFAUT.adresse; $("reglage-modele").value = REGLAGES_DEFAUT.modele; $("reglage-cle").value = "";
    message("message-reglages", "Réglages oubliés : la clé n'est plus dans ce navigateur.");
  });
  $("bouton-reglages-retour").addEventListener("click", () => montrer(ecranAvantReglages));
  $("bouton-reglages").addEventListener("click", () => afficherReglages($("ecran-dossier").hidden ? "ecran-liste" : "ecran-dossier"));

  // --- Liste des dossiers (étape 5) ------------------------------------------------------------------
  // La liste lit la vue dossiers_disponibles (dernière version, sans les dossiers à corriger, sans texte
  // ni champ nettoyage). Les valeurs brutes de la base sont mises en forme pour l'affichage seulement.
  const PAR_PAGE = 50;
  const liste = { page: 0, total: 0, filtres: { source: "", specialite: "", type: "", id: "" }, valeurs: null, lots: new Map() };
  // Nom court d'une source pour l'affichage, d'après l'identifiant du lot (lots.id).
  function nomSource(lot) {
    if (!lot) return "—";
    if (lot.startsWith("parhaf")) return "PARHAF";
    if (lot.startsWith("synthetiques")) return "Synthétique";
    return lot;
  }
  // Identifiant abrégé à l'écran : les UUID des CRH synthétiques sont réduits à leurs 8 premiers caractères.
  function identCourt(id) { return /^[0-9a-f]{8}-[0-9a-f]{4}-/.test(id) ? id.slice(0, 8) + "…" : id; }

  function enClair(valeur) {
    if (!valeur) return "—";
    const bas = valeur.toLowerCase();
    return bas.charAt(0).toUpperCase() + bas.slice(1);
  }
  function nombre(n) { return new Intl.NumberFormat("fr-FR").format(n); }

  // Les valeurs des listes de filtre viennent de la fonction valeurs_filtres() (migration 19) : par lot, les
  // spécialités et types distincts avec leur effectif, en une requête courte (PostgREST renvoie au plus 1 000
  // lignes par requête ; lire toute la vue ne convenait plus au-delà de 1 000 dossiers).
  async function chargerValeursRecherche() {
    // Une seule promesse partagée : deux appels rapprochés (restauration de session, puis changement d'état de
    // connexion) remplissaient chacun les menus, d'où des sources en double (corrigé en A2-0.14).
    if (!liste.chargement) liste.chargement = chargerValeursRecherche_().catch((e) => { liste.chargement = null; throw e; });
    return liste.chargement;
  }
  async function chargerValeursRecherche_() {
    if (liste.valeurs) return;
    const lots = await base.from("lots").select("id, description").order("id");
    if (lots.error) { message("message-liste", "Les sources n'ont pas pu être chargées : " + lots.error.message, true); return; }
    const { data, error } = await base.rpc("valeurs_filtres");
    if (error) { message("message-liste", "Les valeurs de recherche n'ont pas pu être chargées : " + error.message, true); return; }
    liste.valeurs = data;
    const lotsPresents = new Set(data.map((v) => v.lot));
    for (const l of lots.data) if (lotsPresents.has(l.id)) liste.lots.set(l.id, l.description);
    const sel = $("filtre-source");
    while (sel.options.length > 1) sel.remove(1);
    for (const [id] of liste.lots) {
      const opt = document.createElement("option");
      opt.value = id; opt.textContent = nomSource(id) + " (" + nombre(data.filter((v) => v.lot === id).reduce((t, v) => t + v.nb, 0)) + ")";
      sel.appendChild(opt);
    }
    remplirValeurs();
  }
  // Les listes de spécialité et de type ne montrent que les valeurs de la source choisie (toutes si aucune).
  function remplirValeurs() {
    const source = $("filtre-source").value;
    const specialites = new Map(), types = new Map();
    for (const v of liste.valeurs) {
      if (source && v.lot !== source) continue;
      if (v.specialite) specialites.set(v.specialite, (specialites.get(v.specialite) || 0) + v.nb);
      if (v.type_prise_en_charge) types.set(v.type_prise_en_charge, (types.get(v.type_prise_en_charge) || 0) + v.nb);
    }
    const remplir = (select, valeurs) => {
      const courant = select.value;
      select.textContent = "";
      const vide = document.createElement("option"); vide.value = ""; vide.textContent = select.id === "filtre-type" ? "Tous" : "Toutes";
      select.appendChild(vide);
      for (const [brut, n] of [...valeurs.entries()].sort((a, b) => a[0].localeCompare(b[0], "fr"))) {
        const opt = document.createElement("option");
        opt.value = brut; opt.textContent = enClair(brut) + " (" + nombre(n) + ")";
        select.appendChild(opt);
      }
      select.value = valeurs.has(courant) ? courant : "";
    };
    remplir($("filtre-specialite"), specialites);
    remplir($("filtre-type"), types);
  }
  $("filtre-source").addEventListener("change", remplirValeurs);

  async function chargerPage() {
    message("message-liste", "");
    let req = base.from("dossiers_disponibles")
      .select("id, lot, id_source, specialite, type_prise_en_charge, nb_documents_origine, longueur", { count: "exact" })
      .order("lot").order("id_source");
    const f = liste.filtres;
    if (f.source) req = req.eq("lot", f.source);
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
        ["", nomSource(d.lot)], ["ident", identCourt(d.id_source)], ["", enClair(d.specialite)], ["", enClair(d.type_prise_en_charge)],
        ["num", nombre(d.nb_documents_origine)], ["num", nombre(d.longueur) + " car."],
      ];
      for (const [classe, texte] of cellules) {
        const td = document.createElement("td"); td.className = classe; td.textContent = texte;
        if (classe === "ident") td.title = d.id_source;
        tr.appendChild(td);
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
    liste.filtres = { source: $("filtre-source").value, specialite: $("filtre-specialite").value, type: $("filtre-type").value, id: $("filtre-id").value.trim() };
    liste.page = 0;
    chargerPage();
  });
  $("bouton-effacer-recherche").addEventListener("click", () => {
    $("filtre-source").value = ""; remplirValeurs(); $("filtre-id").value = "";
    liste.filtres = { source: "", specialite: "", type: "", id: "" }; liste.page = 0;
    chargerPage();
  });
  $("page-precedente").addEventListener("click", () => { if (liste.page > 0) { liste.page -= 1; chargerPage(); } });
  $("page-suivante").addEventListener("click", () => { liste.page += 1; chargerPage(); });

  // --- Écran du dossier : affichage du texte et surlignage (étape 6) ------------------------------------
  // Le texte affiché est la chaîne de la base, sans transformation (white-space: pre-wrap). Les positions des
  // passages sont des points de code (web/positions.js ; docs/page_web.md). Les surlignages ne sont pas
  // enregistrés dans la base à ce stade : ils restent dans le navigateur (sauvegarde locale, protégée).
  //
  // DEUX MODES (docs/page_web.md §9) :
  //  - MODE_ENSEMBLES = false (lot A1, CADRAGE.md §2.1 étape 7, SCHEMA.md §3.5) : l'utilisateur surligne des
  //    passages sans les regrouper ; c'est le LLM qui formera les ensembles (lot A2).
  //  - MODE_ENSEMBLES = true : regroupement manuel en ensembles numérotés (nouvel ensemble, ajout, retrait,
  //    suppression). Code conservé, désactivé, pour la revue des ensembles après l'appel (lot A3).
  //  - MODE_PANNEAU = false (lot A1, en service) : pas de panneau latéral ni de barre de sélection. Le passage est
  //    surligné dès que la souris est relâchée ; un clic sur un passage surligné le retire ; une sélection qui
  //    chevauche un passage existant est fusionnée avec lui. MODE_PANNEAU = true réactive le panneau (passages ou
  //    ensembles selon MODE_ENSEMBLES) et la barre « Surligner / Nouvel ensemble / Ajouter ».
  const MODE_ENSEMBLES = false;
  const MODE_PANNEAU = false;
  const P = window.CodeurPositions;
  const dossier = { doc: null, passages: [], ensembles: [], prochainNumero: 1, actif: null, selection: null };

  // Sauvegarde locale : toute lecture ou écriture est protégée ; la page fonctionne sans.
  function cleLocale() { return "codeur.surlignages." + etat.utilisateur.id + "." + dossier.doc.id; }
  function sauvegarderLocal() {
    try {
      const contenu = { version: 2, document: dossier.doc.id, empreinte: dossier.doc.empreinte, enregistreLe: new Date().toISOString(),
                        passages: dossier.passages, ensembles: dossier.ensembles, prochainNumero: dossier.prochainNumero };
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
      const valide = (p) => P.verifier(dossier.doc.texte, p);
      const ensembles = (c.ensembles || []).map((e) => ({ numero: e.numero, passages: (e.passages || []).filter(valide) }));
      let passages = (c.passages || []).filter(valide);
      // Compatibilité : surlignages de l'ancien format (version 1, ensembles seulement) relus comme passages.
      if (!passages.length && !MODE_ENSEMBLES) passages = ensembles.flatMap((e) => e.passages);
      return { passages: trierPassages(passages), ensembles, prochainNumero: c.prochainNumero || (Math.max(0, ...ensembles.map((e) => e.numero)) + 1) };
    } catch (e) {
      return null;
    }
  }
  function effacerLocal() { try { window.localStorage.removeItem(cleLocale()); } catch (e) { /* indisponible */ } }
  function trierPassages(liste) { return liste.slice().sort((a, b) => a.debut - b.debut || a.fin - b.fin); }

  async function ouvrirDossier(id) {
    message("message-liste", "");
    const { data, error } = await base.from("documents")
      .select("id, id_source, version, specialite, type_prise_en_charge, texte, empreinte, nb_documents_origine").eq("id", id).single();
    if (error) { message("message-liste", "Le dossier n'a pas pu être chargé : " + error.message, true); return; }
    dossier.doc = data; dossier.passages = []; dossier.ensembles = []; dossier.prochainNumero = 1; dossier.actif = null; dossier.selection = null; dossier.codage = null;
    $("bloc-codage").hidden = true; $("codage-contenu").textContent = ""; $("codage-etat").textContent = ""; $("codage-reprise").hidden = true;
    $("codage-non-codes").textContent = ""; $("codage-non-codes").hidden = true; $("codage-sauvegarde").textContent = "";
    travail.base = null; travail.courant = null; travail.modifie = false; travail.localEnAttente = null;
    $("dossier-titre").textContent = data.id_source;
    $("dossier-infos").textContent = enClair(data.specialite) + "\n" + enClair(data.type_prise_en_charge) + "\n" +
      nombre(data.nb_documents_origine) + " document" + (data.nb_documents_origine > 1 ? "s" : "") + " d'origine — " + nombre(P.longueur(data.texte)) + " caractères — version " + data.version;
    message("message-dossier", "");
    $("sauvegarde-etat").textContent = "";
    const local = chargerLocal();
    if (local && (local.passages.length || local.ensembles.length)) {
      dossier.passages = local.passages; dossier.ensembles = local.ensembles; dossier.prochainNumero = local.prochainNumero;
      $("sauvegarde-etat").textContent = "Surlignages retrouvés dans ce navigateur.";
    }
    $("panneau-titre").textContent = MODE_ENSEMBLES ? "Ensembles" : "Passages surlignés";
    $("panneau-aide").textContent = MODE_ENSEMBLES
      ? "Sélectionnez un passage dans le texte, puis « Nouvel ensemble » (touche N) ou « Ajouter à l'ensemble sélectionné » (touche A)."
      : "Sélectionnez un passage dans le texte, puis « Surligner » (touche N). Les passages seront regroupés par le LLM.";
    $("liste-passages").hidden = MODE_ENSEMBLES; $("liste-ensembles").hidden = !MODE_ENSEMBLES;
    $("bouton-surligner").hidden = MODE_ENSEMBLES; $("bouton-nouvel-ensemble").hidden = !MODE_ENSEMBLES;
    $("panneau-ensembles").hidden = !MODE_PANNEAU;
    document.querySelector(".dossier-corps").classList.toggle("sans-panneau", !MODE_PANNEAU);
    $("texte-dossier").classList.toggle("mode-simple", !MODE_PANNEAU);
    montrer("ecran-dossier");
    codageUI.commentairesOuverts = new Set();
    montrerVue("codage");
    rendre(); cacherBarre();
    await chargerCodageExistant();
    majBoutons();
    chargerEvaluationExistante();
  }

  // Les « unités » surlignées : en mode passages, chaque passage ; en mode ensembles, chaque ensemble.
  function unites() {
    if (MODE_ENSEMBLES) return dossier.ensembles.map((e) => ({ cle: e.numero, couleur: e.numero % 8, passages: e.passages }));
    return passagesLibres().map((p) => ({ cle: "p" + p.debut + ":" + p.fin, couleur: 0, passages: [p] }));
  }
  // Passages surlignés qui ne sont rattachés à aucun code (SCHEMA.md §3.6) : seuls ceux-là sont envoyés au LLM.
  function passagesLibres() {
    const preuves = travail.courant ? travail.courant.ensembles.flatMap((e) => e.preuves) : [];
    return dossier.passages.filter((p) => !preuves.some((q) => q.debut < p.fin && p.debut < q.fin));
  }

  // Rendu du texte : découpe aux frontières des passages ; chaque morceau est soit un nœud texte, soit un <mark>
  // dont le contenu est exactement le morceau de texte. Aucun caractère n'est ajouté ni retiré.
  function rendreTexte() {
    const texte = dossier.doc.texte;
    const frontieres = new Set([0, texte.length]);
    const couvertures = []; // [debut16, fin16, cle, couleur]
    for (const u of unites()) for (const p of u.passages) {
      const d = P.pointsVersU16(texte, p.debut), f = P.pointsVersU16(texte, p.fin);
      frontieres.add(d); frontieres.add(f); couvertures.push([d, f, u.cle, u.couleur]);
    }
    // Preuves des codes du codage courant : une unité par code (couleur = rang du code, variante B).
    const preuvesCodes = []; // [debut16, fin16, indexCode]
    if (travail.courant) travail.courant.ensembles.forEach((e, i) => { for (const p of e.preuves) {
      const d = P.pointsVersU16(texte, p.debut), f = P.pointsVersU16(texte, p.fin);
      frontieres.add(d); frontieres.add(f); preuvesCodes.push([d, f, i]);
    } });
    // Mise en forme markdown sans retirer un caractère (web/markdown.js) : des intervalles à décorer, qui
    // ajoutent leurs bornes ; chaque morceau est enveloppé dans un <span> portant les classes qui le couvrent.
    const decos = Markdown.decorations(texte);
    const bornes = Markdown.bornes(texte, [...couvertures, ...preuvesCodes, ...decos].concat([...frontieres].map((x) => [x, x])));
    const bloc = $("texte-dossier");
    bloc.textContent = "";
    bloc.classList.add("mise-en-forme");
    const poser = (d, f, noeud) => {
      const classes = decos.filter(([cd, cf]) => cd <= d && f <= cf).map((x) => x[2]);
      if (!classes.length) { bloc.appendChild(noeud); return; }
      const span = document.createElement("span"); span.className = [...new Set(classes)].join(" "); span.appendChild(noeud); bloc.appendChild(span);
    };
    for (let i = 0; i + 1 < bornes.length; i++) {
      const d = bornes[i], f = bornes[i + 1];
      const morceau = texte.slice(d, f);
      const couv = couvertures.filter(([cd, cf]) => cd <= d && f <= cf);
      const couvCodes = preuvesCodes.filter(([cd, cf]) => cd <= d && f <= cf);
      if (!couv.length && !couvCodes.length) { poser(d, f, document.createTextNode(morceau)); continue; }
      const m = document.createElement("mark");
      if (couvCodes.length) {
        const idx = couvCodes.map((c) => c[2]);
        m.className = "preuve " + couleurCode(idx[0]) + (couvCodes.length > 1 ? " chevauche" : "") + (idx.includes(codageUI.ressort) ? " ressort" : "");
        m.dataset.codes = idx.join(",");
        m.title = (couvCodes.length > 1 ? "Passage partagé par " : "") + idx.map((k) => (travail.courant.ensembles[k].code || "code à choisir")).join(", ") + " — cliquer pour voir le code";
      } else {
        const cles = couv.map((c) => c[2]);
        m.className = "surl c" + couv[0][3] + (couv.length > 1 ? " chevauche" : "") + (cles.includes(dossier.actif) ? " actif" : "");
        m.dataset.cles = cles.join(",");
        m.title = !MODE_PANNEAU ? "Passage surligné, pas encore codé — cliquer pour retirer ce surlignage"
          : MODE_ENSEMBLES ? "Ensemble" + (cles.length > 1 ? "s " : " ") + cles.join(", ") : "Passage" + (cles.length > 1 ? "s " : " ") + cles.map((k) => k + 1).join(", ");
      }
      m.textContent = morceau;
      poser(d, f, m);
    }
  }
  // La mise en forme markdown (titres, gras, traits) est toujours active depuis le style « Neutre » ; le texte de la
  // page reste le texte de référence, seul le style change (web/markdown.js).
  function couleurCode(i) {
    const e = travail.courant && travail.courant.ensembles[i];
    return (!e || !e.code) ? "cCX" : "cC" + (i % 8);
  }
  let dernierSurlignage = 0; // en mode simple, le clic qui suit un surlignage ne doit pas le retirer
  $("texte-dossier").addEventListener("click", (ev) => {
    const mp = ev.target.closest("mark.preuve");
    if (mp && !window.getSelection().toString()) { // clic sur une preuve : fait ressortir son code
      const idx = mp.dataset.codes.split(",").map(Number);
      const i = idx.indexOf(codageUI.ressort);
      ressortirCode(idx[(i + 1) % idx.length], true);
      return;
    }
    const m = ev.target.closest("mark.surl");
    if (!m || window.getSelection().toString()) return;
    const cles = m.dataset.cles.split(",").map((x) => (x.startsWith("p") ? x : Number(x)));
    if (!MODE_PANNEAU) {
      if (Date.now() - dernierSurlignage < 400) return;
      retirerPassageSimple(cles[0]);
      return;
    }
    const i = cles.indexOf(dossier.actif);
    choisir(cles[(i + 1) % cles.length], false);
  });

  // ---- Mode simple (lot A1, en service) : surlignage au relâchement de la souris, fusion des chevauchements ----
  function surlignerSimple(passage) {
    if (!P.verifier(dossier.doc.texte, passage)) { message("message-dossier", "Passage refusé : contrôle des positions en échec.", true); return; }
    let debut = passage.debut, fin = passage.fin;
    const restants = [];
    for (const p of dossier.passages) {
      if (p.debut < fin && debut < p.fin) { debut = Math.min(debut, p.debut); fin = Math.max(fin, p.fin); } // chevauchement : fusion
      else restants.push(p);
    }
    const fusionne = { debut, fin, texte: P.extraire(dossier.doc.texte, debut, fin) };
    if (!P.verifier(dossier.doc.texte, fusionne)) { message("message-dossier", "Passage refusé : contrôle des positions en échec après fusion.", true); return; }
    dossier.passages = trierPassages(restants.concat([fusionne]));
    dossier.actif = null;
    dernierSurlignage = Date.now();
    window.getSelection().removeAllRanges();
    rendre(); sauvegarderLocal();
  }
  $("texte-dossier").addEventListener("mouseup", () => {
    if (MODE_PANNEAU) return;
    setTimeout(() => { // laisse au navigateur le temps de finaliser la sélection
      const res = lireSelection();
      if (!res) return;
      if (res.refus) { message("message-dossier", "Passage refusé : " + res.refus + ".", true); window.getSelection().removeAllRanges(); return; }
      message("message-dossier", "");
      if (travail.courant) { menuSelection(res.passage, res.rect); return; } // avec un codage : « Ajouter à… », « Nouveau code… »
      surlignerSimple(res.passage);
    }, 0);
  });
  function rendreCompte() {
    const n = dossier.passages.length;
    $("compte-passages").textContent = n === 0 ? "Aucun passage surligné : sélectionnez un passage avec la souris pour pouvoir faire le codage ; cliquez sur un passage surligné pour le retirer."
      : nombre(n) + " passage" + (n > 1 ? "s" : "") + " surligné" + (n > 1 ? "s" : "") + " — cliquez sur un passage pour le retirer.";
    majBoutons();
  }
  // « Codage » est actif dès qu'il y a un surlignage ou un codage ; « Coder les nouveaux passages » n'apparaît
  // qu'avec un codage et des passages surlignés non rattachés à un code (appel répété, SCHEMA.md §3.6).
  function majBoutons() {
    if (codageUI.appelEnCours) return;
    $("bouton-codage").disabled = !dossier.passages.length && !travail.courant;
    $("bouton-coder-nouveaux").hidden = !(travail.courant && passagesLibres().length);
  }
  // Sous le texte, le codage ou l'évaluation : l'un ou l'autre, jamais les deux ; le bouton actif est coloré.
  function montrerVue(vue) {
    codageUI.vue = vue;
    document.querySelector(".colonne-texte").classList.toggle("vue-evaluation", vue === "evaluation");
    $("bloc-evaluation").hidden = vue !== "evaluation";
    $("bouton-codage").classList.toggle("actif", vue === "codage");
    $("bouton-evaluation").classList.toggle("actif", vue === "evaluation");
  }
  $("bouton-codage").addEventListener("click", () => { montrerVue("codage"); if (!travail.courant) faireCodage(); });
  $("bouton-evaluation").addEventListener("click", () => montrerVue("evaluation"));
  $("bouton-coder-nouveaux").addEventListener("click", faireCodage);

  // ---- Mode passages (lot A1) ----
  function rendrePanneauPassages() {
    const ol = $("liste-passages");
    ol.textContent = "";
    if (!dossier.passages.length) {
      const li = document.createElement("li"); li.className = "discret"; li.textContent = "Aucun passage surligné pour l'instant."; ol.appendChild(li);
    }
    dossier.passages.forEach((p, i) => {
      const li = document.createElement("li");
      li.className = "passage-item" + (i === dossier.actif ? " actif" : "");
      li.addEventListener("click", (ev) => { if (!ev.target.closest("button")) choisir(i, true); });
      const cite = document.createElement("span"); cite.className = "cite";
      const q = document.createElement("q"); q.textContent = p.texte.length > 120 ? p.texte.slice(0, 117) + "…" : p.texte;
      const pos = document.createElement("span"); pos.className = "pos"; pos.textContent = (i + 1) + " — positions " + p.debut + "–" + p.fin;
      cite.append(q, pos);
      const ret = document.createElement("button"); ret.className = "secondaire"; ret.textContent = "Retirer";
      ret.addEventListener("click", () => retirerPassageSimple(i));
      li.append(cite, ret); ol.appendChild(li);
    });
  }
  function surligner() {
    if (!dossier.selection) return;
    const passage = dossier.selection;
    if (!P.verifier(dossier.doc.texte, passage)) { message("message-dossier", "Passage refusé : contrôle des positions en échec.", true); return; }
    if (dossier.passages.some((p) => p.debut === passage.debut && p.fin === passage.fin)) { message("message-dossier", "Ce passage est déjà surligné.", true); return; }
    dossier.passages = trierPassages(dossier.passages.concat([passage]));
    dossier.actif = dossier.passages.findIndex((p) => p.debut === passage.debut && p.fin === passage.fin);
    window.getSelection().removeAllRanges(); cacherBarre();
    rendre(); sauvegarderLocal();
  }
  function retirerPassageSimple(cle) {
    // `cle` : un rang (mode panneau) ou une clé « p<debut>:<fin> » (marques du texte)
    let i = cle;
    if (typeof cle === "string") { const [d, f] = cle.slice(1).split(":").map(Number); i = dossier.passages.findIndex((p) => p.debut === d && p.fin === f); }
    if (typeof i !== "number" || i < 0 || i >= dossier.passages.length) return;
    dossier.passages.splice(i, 1);
    dossier.actif = null;
    rendre(); sauvegarderLocal();
    if (travail.courant) rendreCodage();
  }

  // ---- Mode ensembles (désactivé au lot A1, conservé pour la revue, lot A3) ----
  function rendrePanneauEnsembles() {
    const ol = $("liste-ensembles");
    ol.textContent = "";
    if (!dossier.ensembles.length) {
      const li = document.createElement("li"); li.className = "discret"; li.textContent = "Aucun ensemble pour l'instant."; ol.appendChild(li);
    }
    for (const e of dossier.ensembles) {
      const li = document.createElement("li");
      li.className = "ensemble c" + (e.numero % 8) + (e.numero === dossier.actif ? " actif" : "");
      li.addEventListener("click", (ev) => { if (!ev.target.closest("button")) choisir(e.numero, true); });
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
    $("bouton-ajouter-ensemble").hidden = !MODE_ENSEMBLES || dossier.actif === null;
    $("barre-numero").textContent = dossier.actif === null ? "" : dossier.actif;
  }
  function ajouterPassage(numero, passage) {
    if (!P.verifier(dossier.doc.texte, passage)) { message("message-dossier", "Passage refusé : contrôle des positions en échec.", true); return; }
    const e = dossier.ensembles.find((x) => x.numero === numero);
    if (!e) return;
    if (e.passages.some((p) => p.debut === passage.debut && p.fin === passage.fin)) { message("message-dossier", "Ce passage est déjà dans l'ensemble " + numero + ".", true); return; }
    e.passages.push(passage); e.passages.sort((a, b) => a.debut - b.debut);
    dossier.actif = numero;
    window.getSelection().removeAllRanges(); cacherBarre();
    rendre(); sauvegarderLocal();
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
    rendre(); sauvegarderLocal();
  }
  function supprimerEnsemble(numero) {
    dossier.ensembles = dossier.ensembles.filter((x) => x.numero !== numero);
    if (dossier.actif === numero) dossier.actif = null;
    rendre(); sauvegarderLocal();
  }

  // ---- Commun aux deux modes ----
  function rendre() {
    rendreTexte();
    rendreCompte();
    if (!MODE_PANNEAU) return;
    if (MODE_ENSEMBLES) rendrePanneauEnsembles(); else rendrePanneauPassages();
  }
  function choisir(cle, defiler) {
    dossier.actif = cle;
    rendre();
    if (defiler) {
      const m = $("texte-dossier").querySelector("mark.surl.actif");
      if (m) m.scrollIntoView({ block: "center", behavior: "smooth" });
    } else {
      const el = MODE_ENSEMBLES ? $("liste-ensembles").querySelector(".ensemble.actif") : $("liste-passages").querySelector(".passage-item.actif");
      if (el) el.scrollIntoView({ block: "nearest", behavior: "smooth" });
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
    if ($("ecran-dossier").hidden || !MODE_PANNEAU) return;
    const res = lireSelection();
    if (!res || res.refus) { cacherBarre(); if (res && res.refus) message("message-dossier", "Passage refusé : " + res.refus + ".", true); return; }
    message("message-dossier", "");
    dossier.selection = res.passage;
    montrerBarre(res.rect);
  });

  for (const id of ["bouton-surligner", "bouton-nouvel-ensemble", "bouton-ajouter-ensemble"]) $(id).addEventListener("mousedown", (ev) => ev.preventDefault());
  $("bouton-surligner").addEventListener("click", surligner);
  $("bouton-nouvel-ensemble").addEventListener("click", nouvelEnsemble);
  $("bouton-ajouter-ensemble").addEventListener("click", ajouterAuSelectionne);
  $("bouton-retour-liste").addEventListener("click", () => { cacherBarre(); afficherListe(); });
  $("bouton-retour-liste-bas").addEventListener("click", () => { cacherBarre(); afficherListe(); window.scrollTo(0, 0); });
  // --- « Faire le codage » : appel au LLM, contrôles, boucle de correction, enregistrement (étape 5) ---------------
  // SCHEMA.md §3.5, §3.6, §3.10, §5.2. La logique pure est dans web/codage.js (CodeurCodage) ; ici : les prompts,
  // les lectures de l'index, les écritures dans appels_llm et codages, et l'enchaînement.
  const K = window.CodeurCodage;
  const prompts = {};
  // --- Notation de la qualité du compte rendu (brief 7, étape 4) ---------------------------------------
  // La grille est le fichier versionné web/grille_qualite.md : un titre « ## » par dimension, une ligne par niveau
  // « n — repère ». Les clés des notes (SCHEMA.md §5.3) suivent l'ordre des dimensions.
  const CLES_DIMENSIONS = ["organisation", "langage", "coherence_medicale", "synthese", "qualite_generale"];
  let grille = null;
  async function lireGrille() {
    if (grille) return grille;
    const rep = await fetch("grille_qualite.md", { cache: "no-store" });
    if (!rep.ok) throw new Error("grille de qualité introuvable (HTTP " + rep.status + ")");
    const md = await rep.text();
    const v = md.match(/<!--\s*version:\s*([^\s>]+)\s*-->/);
    if (!v) throw new Error("grille de qualité sans repère de version");
    const dimensions = [];
    for (const ligne of md.split("\n")) {
      const t = ligne.match(/^##\s+(.+?)\s*$/);
      if (t) { const [nom, sous] = t[1].split(/\s*:\s*/); dimensions.push({ nom, sous: sous || null, reperes: {} }); continue; }
      const r = ligne.match(/^([1-5])\s*[—–-]\s*(.+?)\s*$/);
      if (r && dimensions.length) dimensions[dimensions.length - 1].reperes[r[1]] = r[2];
    }
    if (dimensions.length !== 5 || dimensions.some((d) => Object.keys(d.reperes).length !== 5)) throw new Error("grille de qualité incomplète (cinq dimensions, cinq niveaux chacune)");
    dimensions.forEach((d, i) => { d.cle = CLES_DIMENSIONS[i]; });
    grille = { version: v[1], dimensions };
    return grille;
  }
  const evaluation = { notes: {}, derniere: null };
  async function chargerEvaluationExistante() {
    evaluation.notes = {}; evaluation.derniere = null;
    $("evaluation-commentaire").value = ""; $("evaluation-sauvegarde").textContent = ""; $("evaluation-etat").textContent = "";
    message("evaluation-message", "");
    try { await lireGrille(); } catch (e) { message("evaluation-message", "La grille de notation n'a pas pu être lue (" + e.message + ").", true); return; }
    const r = await base.from("evaluations").select("id, cree_le, notes, commentaire, version_grille").eq("document", dossier.doc.id)
      .eq("utilisateur", etat.utilisateur.id).eq("auteur", "humain").order("cree_le", { ascending: false }).limit(1);
    if (r.error) { message("evaluation-message", "Votre note n'a pas pu être relue : " + r.error.message, true); }
    else if (r.data.length) {
      evaluation.derniere = r.data[0];
      evaluation.notes = { ...(r.data[0].notes || {}) };
      $("evaluation-commentaire").value = r.data[0].commentaire || "";
      $("evaluation-etat").textContent = "Dernière note enregistrée le " + new Date(r.data[0].cree_le).toLocaleString("fr-FR") +
        (r.data[0].version_grille && r.data[0].version_grille !== grille.version ? " (grille " + r.data[0].version_grille + ")" : "") + ".";
    }
    rendreEvaluation();
  }
  function rendreEvaluation() {
    const zone = $("evaluation-contenu"); zone.textContent = "";
    if (!grille) return;
    for (const d of grille.dimensions) {
      const dim = document.createElement("div"); dim.className = "dim";
      const nom = document.createElement("span"); nom.className = "nom"; nom.textContent = d.nom;
      if (d.sous) { const small = document.createElement("small"); small.textContent = d.sous; nom.appendChild(small); }
      const choix = document.createElement("span"); choix.className = "choix";
      const valeur = evaluation.notes[d.cle];
      for (let n = 1; n <= 5; n++) {
        const b = document.createElement("button"); b.type = "button"; b.textContent = n; b.title = n + " — " + d.reperes[n];
        b.className = valeur === n ? "actif" : "";
        b.addEventListener("click", () => { evaluation.notes[d.cle] = valeur === n ? null : n; rendreEvaluation(); });
        choix.appendChild(b);
      }
      const repere = document.createElement("span"); repere.className = "repere";
      repere.textContent = valeur ? valeur + " — " + d.reperes[valeur] : "Non notée.";
      dim.append(nom, choix, repere); zone.appendChild(dim);
    }
    const nb = CLES_DIMENSIONS.filter((k) => evaluation.notes[k]).length;
    $("evaluation-sauvegarde").textContent = nb === 5 ? "" : (nb === 0 ? "Aucune dimension notée pour l'instant." : nb + " dimension" + (nb > 1 ? "s" : "") + " notée" + (nb > 1 ? "s" : "") + " sur 5 : une note incomplète peut être enregistrée.");
  }
  $("evaluation-commentaire").addEventListener("input", () => { $("evaluation-compte").textContent = nombre($("evaluation-commentaire").value.length) + " / 1 000"; });
  $("bouton-enregistrer-note").addEventListener("click", async () => {
    if (!dossier.doc || !grille) return;
    const notes = {}; for (const k of CLES_DIMENSIONS) notes[k] = evaluation.notes[k] || null;
    const commentaire = $("evaluation-commentaire").value.trim() || null;
    if (!Object.values(notes).some(Boolean) && !commentaire) { message("evaluation-message", "Notez au moins une dimension, ou écrivez un commentaire, avant d'enregistrer.", true); return; }
    const b = $("bouton-enregistrer-note"); b.disabled = true; message("evaluation-message", "");
    const ins = await base.from("evaluations").insert({ utilisateur: etat.utilisateur.id, document: dossier.doc.id, auteur: "humain",
      notes, commentaire, version_grille: grille.version }).select("id, cree_le").single();
    b.disabled = false;
    if (ins.error) { message("evaluation-message", "La note n'a pas pu être enregistrée : " + ins.error.message, true); return; }
    evaluation.derniere = { id: ins.data.id, cree_le: ins.data.cree_le, notes, commentaire, version_grille: grille.version };
    $("evaluation-etat").textContent = "Dernière note enregistrée le " + new Date(ins.data.cree_le).toLocaleString("fr-FR") + ".";
    const nb = Object.values(notes).filter(Boolean).length;
    message("evaluation-message", "Votre note est enregistrée (" + nb + " dimension" + (nb > 1 ? "s" : "") + " sur 5" + (commentaire ? ", avec un commentaire" : "") + ").");
  });

  async function lirePrompt(nom) {
    if (prompts[nom]) return prompts[nom];
    const rep = await fetch("prompts/" + nom + ".md", { cache: "no-store" });
    if (!rep.ok) throw new Error("prompt " + nom + " introuvable (HTTP " + rep.status + ")");
    const md = await rep.text();
    const v = md.match(/<!--\s*version:\s*([^\s>]+)\s*-->/);
    if (!v) throw new Error("prompt " + nom + " sans repère de version");
    prompts[nom] = { version: v[1], texte: md.replace(/<!--[\s\S]*?-->/g, "").trim() };
    return prompts[nom];
  }
  function uuid() {
    if (window.crypto && window.crypto.randomUUID) return window.crypto.randomUUID();
    const b = new Uint8Array(16); window.crypto.getRandomValues(b); b[6] = (b[6] & 0x0f) | 0x40; b[8] = (b[8] & 0x3f) | 0x80;
    const h = [...b].map((x) => x.toString(16).padStart(2, "0")).join("");
    return h.slice(0, 8) + "-" + h.slice(8, 12) + "-" + h.slice(12, 16) + "-" + h.slice(16, 20) + "-" + h.slice(20);
  }
  // Enregistre un appel dans appels_llm (sans la clé ; sans retour, la table n'étant pas relisible).
  async function enregistrerAppel(ligne) {
    const { error } = await base.from("appels_llm").insert(ligne, { returning: "minimal" });
    if (error) throw new Error("l'appel n'a pas pu être enregistré dans la base : " + error.message);
  }
  // Index : lit les codes et leurs descendants ; candidats de catégorie pour les codes sans descendant.
  async function lireIndex(codes) {
    const uniques = [...new Set(codes.filter(Boolean))];
    const index = new Map(), descendants = new Map();
    if (uniques.length) {
      const f = await base.from("fiches").select("code, libelle, codable, statut_mco").in("code", uniques);
      if (f.error) throw new Error("lecture de l'index impossible : " + f.error.message);
      for (const x of f.data) index.set(x.code, { codable: x.codable, libelle: x.libelle, statut: x.statut_mco });
      // Une requête par code, limitée au nombre de candidats que la correction présente : un nœud peut avoir
      // plus de cent descendants et PostgREST ne renvoie jamais plus de 1 000 lignes par requête.
      const reponses = await Promise.all(uniques.map((c) => base.from("descendants_codables").select("code, libelle")
        .eq("noeud", c).order("ordre_kit").limit(K.LIMITE_CANDIDATS)));
      reponses.forEach((d, i) => {
        if (d.error) throw new Error("lecture des descendants impossible : " + d.error.message);
        if (d.data.length) descendants.set(uniques[i], d.data.map((x) => ({ code: x.code, libelle: x.libelle })));
      });
    }
    return { index, descendants };
  }
  async function candidatsDeCategorie(code, limite) {
    const cat = (code || "").slice(0, 3);
    if (cat.length < 3) return [];
    const r = await base.from("fiches").select("code, libelle").like("code", cat + "%").eq("codable", true).order("code").limit(limite || K.LIMITE_CANDIDATS);
    return r.error ? [] : r.data;
  }
  async function dernierCodage(documentId) {
    const r = await base.from("codages").select("id, etape, codage, cree_le").eq("document", documentId).eq("utilisateur", etat.utilisateur.id)
      .order("cree_le", { ascending: false }).limit(1);
    return r.error || !r.data.length ? null : r.data[0];
  }

  async function faireCodage() {
    etat.reglages = etat.reglages || lireReglages();
    if (!etat.reglages) { afficherReglages("ecran-dossier", "Indiquez d'abord l'adresse du service, le modèle et votre clé pour pouvoir faire le codage."); return; }
    if (!dossier.passages.length) { message("message-dossier", "Surlignez au moins un passage avant de faire le codage.", true); return; }
    const bouton = $("bouton-codage");
    codageUI.appelEnCours = true;
    bouton.disabled = true; $("bouton-coder-nouveaux").disabled = true;
    montrerVue("codage");
    $("bloc-codage").hidden = false;
    $("codage-contenu").textContent = "";
    const etatCodage = (t) => { $("codage-etat").innerHTML = "<span class='attente'></span>" + t; };
    message("message-dossier", "");
    const reglages = etat.reglages;
    const fournisseur = fournisseurDe(reglages.adresse);
    // Appel répété (SCHEMA.md §3.6) : seuls les passages surlignés non rattachés à un code sont envoyés ; un passage qui
    // chevauche une preuve existante complète ce code sans être envoyé ; les codes retenus sont transmis en lecture seule.
    const repete = !!(travail.courant && travail.courant.ensembles.length);
    let passages = dossier.passages.slice();
    const avertissements = [];
    if (repete) {
      const prep = K.preparerAppelRepete(travail.courant, dossier.passages, (p) => P.verifier(dossier.doc.texte, p));
      passages = prep.aEnvoyer;
      if (prep.modifie) { travail.modifie = true; avertissements.push("Passage(s) ajouté(s) aux preuves d'un code existant (chevauchement) : " + prep.completes.join(", ") + "."); }
      if (!passages.length) {
        rendreCodage(); if (prep.modifie) sauvegarderLocalCodage();
        message("message-dossier", "Aucun nouveau passage à envoyer au modèle : tous vos surlignages sont déjà rattachés à un code." + (prep.modifie ? " " + avertissements[0] : ""), !prep.modifie);
        finAppel(); return;
      }
      // Vos modifications non enregistrées sont d'abord enregistrées (ligne revue_humain), pour ne pas être attribuées à l'IA.
      if (travail.modifie) {
        etatCodage("Enregistrement de vos modifications (revue) avant l'appel…");
        try { await enregistrerRevue(); avertissements.push("Vos modifications ont d'abord été enregistrées comme revue (ligne revue_humain)."); }
        catch (e) { afficherEchec("Vos modifications n'ont pas pu être enregistrées avant l'appel : " + e.message + ". Appel annulé."); finAppel(); return; }
      }
    }
    try {
      const pc = await lirePrompt("codage_v1");
      const contexte = repete ? { codesRetenus: travail.courant.ensembles.filter((e) => e.code).map((e) => ({ code: e.code, libelle: e.libelle, categorie: e.categorie })) } : null;
      const utilisateur = K.construireMessageUtilisateur(dossier.doc.id_source, dossier.doc.texte, passages, contexte);
      const messages = [{ role: "system", content: pc.texte }, { role: "user", content: utilisateur }];
      const appelInitial = uuid();
      let appelCourant = appelInitial;
      // ---- Tour 1 : le codage
      etatCodage("Appel au modèle " + reglages.modele + " (" + passages.length + " passage" + (passages.length > 1 ? "s" : "") + ")…");
      let res = await appelerEtEnregistrer(reglages, fournisseur, messages, { id: appelInitial, appel_initial: null, version_prompt: pc.version, tache: "codage", passages });
      let analyse = K.analyserReponse(res.contenu, passages);
      if (!analyse.ok) { afficherEchec("La réponse du modèle n'est pas exploitable : " + analyse.erreur + ". Aucun codage n'a été enregistré ; vous pouvez réessayer."); return; }
      let idx = await lireIndex(analyse.ensembles.map((e) => e.code));
      K.verifierCodes(analyse.ensembles, (c) => idx.index.get(c) || null, (c) => idx.descendants.get(c) || []);
      // ---- Tours de correction (au plus 2)
      const pcorr = await lirePrompt("correction_v1");
      for (let tour = 1; tour <= 2; tour++) {
        const aCorriger = analyse.ensembles.filter((e) => e.statut !== "codable");
        if (!aCorriger.length) break;
        // Candidats : descendants codables (seule liste pour un code tronqué ou père interdit) ; pour un code inconnu
        // ou sans descendant : codes codables de la catégorie, puis codes dont une formulation ressemble au libellé du modèle.
        const cands = new Map();
        for (const e of aCorriger) {
          const d = idx.descendants.get(e.code) || [];
          if (d.length) { cands.set(e.code, [{ titre: "Codes codables possibles (descendants)", liste: d }]); continue; }
          const sections = [];
          const inconnu = e.statut === "inconnu";
          const cat = await candidatsDeCategorie(e.code, inconnu ? 20 : K.LIMITE_CANDIDATS); // catégorie limitée à 20 pour un code inconnu
          let ress = null;
          if (e.libelleModele) {
            const r = await base.rpc("rechercher_codes", { recherche: e.libelleModele, limite: K.LIMITE_CANDIDATS, seuil: 0.15 });
            if (!r.error && r.data.length) ress = { titre: "Codes dont une formulation ressemble à votre libellé", liste: r.data.map((x) => ({ code: x.code, libelle: x.libelle })) };
          }
          const secCat = cat.length ? { titre: "Codes codables de la catégorie " + e.code.slice(0, 3), liste: cat } : null;
          // Code inconnu : la ressemblance d'abord ; code connu sans descendant : la catégorie d'abord.
          for (const sec of (inconnu ? [ress, secCat] : [secCat, ress])) if (sec) sections.push(sec);
          cands.set(e.code, sections);
        }
        const mc = K.construireMessageCorrection(analyse.ensembles, (e) => cands.get(e.code) || []);
        etatCodage("Correction (tour " + tour + ") : " + aCorriger.map((e) => e.code).join(", ") + " non codable" + (aCorriger.length > 1 ? "s" : "") + "…");
        messages.push({ role: "assistant", content: res.contenu }, { role: "user", content: pcorr.texte + "\n\n" + mc.message });
        appelCourant = uuid();
        res = await appelerEtEnregistrer(reglages, fournisseur, messages, { id: appelCourant, appel_initial: appelInitial, version_prompt: pcorr.version, tache: "codage", passages, tour });
        // les candidats sont déjà vérifiés codables ; on recharge l'index pour les codes choisis
        const choisis = []; try { const o = JSON.parse(res.contenu.replace(/^```(?:json)?\s*|\s*```$/gi, "")); for (const v of Object.values(o.corrections || {})) if (v) choisis.push(K.normaliserCode(v)); } catch (e) { /* géré par appliquerCorrection */ }
        const idx2 = await lireIndex(choisis);
        for (const [k, v] of idx2.index) idx.index.set(k, v);
        for (const [k, v] of idx2.descendants) idx.descendants.set(k, v);
        const corr = K.appliquerCorrection(analyse.ensembles, res.contenu, mc.aCorriger, (c) => idx.index.get(c) || null, (c) => idx.descendants.get(c) || []);
        if (!corr.ok) { avertissements.push("Réponse de correction illisible au tour " + tour + "."); break; }
        if (corr.ignores.length) avertissements.push("Choix hors liste ignoré : " + corr.ignores.map((x) => x.code + " → " + x.choisi).join(", ") + ".");
      }
      // ---- Construction et enregistrement
      const precedent = await dernierCodage(dossier.doc.id);
      let codage = K.construireCodage(analyse, passages, "ia_humain", precedent ? precedent.codage : null);
      if (repete) {
        // la page assemble : codes retenus (y compris vos modifications non enregistrées) + propositions sur les nouveaux passages
        const ass = K.assemblerAppelRepete(travail.courant, codage, "ia_humain");
        codage = ass.codage;
        if (ass.ecartes.length) avertissements.push("Proposition(s) sans nouveau passage écartée(s) : " + ass.ecartes.join(", ") + ".");
        if (ass.completes.length) avertissements.push("L'IA a ajouté des passages aux preuves de codes déjà retenus : " + ass.completes.join(", ") + " (vous pouvez les retirer).");
      }
      codage.affichage = varianteAffichage();
      const compteurs = K.compteurs(precedent ? precedent.codage : null, codage);
      etatCodage("Enregistrement du codage…");
      const ins = await base.from("codages").insert({
        document: dossier.doc.id, etape: "ia_humain", utilisateur: etat.utilisateur.id, codage_precedent: precedent ? precedent.id : null,
        appel_llm: appelCourant, valide: false, compteurs, codage,
      }).select("id, cree_le").single();
      if (ins.error) throw new Error("le codage n'a pas pu être enregistré : " + ins.error.message);
      effacerLocalCodage();
      installerCodage({ id: ins.data.id, etape: "ia_humain", codage, cree_le: ins.data.cree_le }, null);
      const an = analyse.anomalies;
      if (an.passagesManquants.length) avertissements.push("Passage(s) non traité(s) par l'IA : " + an.passagesManquants.map((k) => "n° " + k).join(", ") + ".");
      if (an.passagesInconnus.length) avertissements.push("Numéro(s) de passage inconnu(s) dans la réponse, ignoré(s) : " + an.passagesInconnus.join(", ") + ".");
      if (an.ensemblesSansPassage) avertissements.push(an.ensemblesSansPassage + " ensemble(s) sans passage valide écarté(s).");
      if (an.pathologiesPrincipalesMultiples.length) avertissements.push("Plusieurs pathologies principales proposées : " + an.pathologiesPrincipalesMultiples[0] + " gardée, les autres passées en diagnostic associé.");
      if (an.passagesMultiEnsembles.length) avertissements.push("Passage(s) rattaché(s) à plusieurs codes : " + an.passagesMultiEnsembles.map((k) => "n° " + k).join(", ") + ".");
      if (an.nonCodesRedondants.length) avertissements.push("Passage(s) déclaré(s) non codé(s) alors qu'ils appuient un code : déclaration écartée (" + an.nonCodesRedondants.map((k) => "n° " + k).join(", ") + ").");
      $("codage-etat").textContent = "Codage proposé par l'IA enregistré (" + new Date().toLocaleTimeString("fr-FR") + ")." + (avertissements.length ? " À noter : " + avertissements.join(" ") : "");
      rendreCodage();
    } catch (e) {
      afficherEchec(e.message);
    } finally {
      finAppel();
    }
  }
  // Un appel : envoi, enregistrement dans appels_llm (réussi ou échoué), retour du résultat.
  async function appelerEtEnregistrer(reglages, fournisseur, messages, infos) {
    const requete = { modele: reglages.modele, adresse: reglages.adresse, temperature: 0, response_format: "json_object", tour: infos.tour || 0,
                      passages: infos.passages.map((p, i) => ({ numero: i + 1, debut: p.debut, fin: p.fin, texte: p.texte })), messages };
    let res = null, erreur = null;
    try { res = await appelerLLM(reglages, messages, { json: true }); } catch (e) { erreur = e.message; }
    await enregistrerAppel({
      id: infos.id, utilisateur: etat.utilisateur.id, document: dossier.doc.id, tache: infos.tache, fournisseur, modele: res ? res.modele : reglages.modele,
      version_prompt: infos.version_prompt, requete, reponse: res ? res.brut : null,
      tokens_entree: res ? (res.usage.prompt_tokens ?? null) : null, tokens_sortie: res ? (res.usage.completion_tokens ?? null) : null,
      tokens_total: res ? (res.usage.total_tokens ?? null) : null, duree_ms: res ? res.duree_ms : null, erreur, appel_initial: infos.appel_initial,
    });
    if (erreur) throw new Error("appel au modèle en échec : " + erreur);
    return res;
  }
  function finAppel() { codageUI.appelEnCours = false; $("bouton-coder-nouveaux").disabled = false; majBoutons(); }
  function afficherEchec(texte) {
    $("codage-etat").textContent = "";
    message("message-dossier", texte, true);
    $("bloc-codage").hidden = !travail.base && !travail.courant;
  }
  // « Tout effacer » : un panneau de confirmation dit précisément ce qui sera effacé (surlignages non codés ;
  // codage de travail non enregistré) et rappelle que les lignes enregistrées dans la base ne changent pas.
  $("bouton-tout-effacer").addEventListener("click", (ev) => {
    ev.stopPropagation();
    const libres = passagesLibres().length;
    const codes = travail.courant ? travail.courant.ensembles.length : 0;
    if (!libres && !codes) { message("message-dossier", "Rien à effacer.", false); return; }
    const menu = $("menu-flottant"); menu.textContent = "";
    const t = document.createElement("div"); t.className = "titre"; t.style.whiteSpace = "normal"; t.style.maxWidth = "24rem";
    const lignes = [];
    if (libres) lignes.push(libres + " surlignage" + (libres > 1 ? "s" : "") + " non codé" + (libres > 1 ? "s" : ""));
    if (codes) lignes.push("le codage de travail (" + codes + " code" + (codes > 1 ? "s" : "") + ")" + (travail.modifie ? ", avec des modifications NON ENREGISTRÉES" : ""));
    t.textContent = "Effacer : " + lignes.join(" ; ") + ". Les codages déjà enregistrés dans la base ne changent pas" + (codes ? " ; rouvrir le dossier ramènera le dernier codage enregistré" : "") + ".";
    menu.appendChild(t);
    bouton(menu, "Effacer", () => {
      dossier.passages = []; dossier.ensembles = []; dossier.actif = null; dossier.prochainNumero = 1; effacerLocal();
      if (travail.courant) {
        travail.courant.ensembles = []; travail.courant.passages_non_codes = [];
        travail.modifie = true; codageUI.ressort = null;
        rendreCodage(); sauvegarderLocalCodage();
        $("codage-sauvegarde").textContent = "Surlignages et codage en cours effacés (non enregistré : « Enregistrer mon codage » pour enregistrer ce retrait, ou rouvrir le dossier pour revenir au dernier codage enregistré).";
      } else { rendre(); }
      $("sauvegarde-etat").textContent = "Surlignages effacés.";
    });
    bouton(menu, "Annuler", () => {});
    placerMenu(menu, ev.target.getBoundingClientRect());
  });
  // Raccourcis N et A : seulement sur l'écran du dossier, jamais dans un champ de saisie.
  document.addEventListener("keydown", (ev) => {
    if ($("ecran-dossier").hidden || !MODE_PANNEAU || ev.ctrlKey || ev.metaKey || ev.altKey) return;
    const cible = ev.target;
    if (cible && (cible.tagName === "INPUT" || cible.tagName === "SELECT" || cible.tagName === "TEXTAREA" || cible.isContentEditable)) return;
    if (ev.key === "n" || ev.key === "N") { ev.preventDefault(); if (MODE_ENSEMBLES) nouvelEnsemble(); else surligner(); }
    if ((ev.key === "a" || ev.key === "A") && MODE_ENSEMBLES) { ev.preventDefault(); ajouterAuSelectionne(); }
  });

  // --- Écran de codage (étape 6) ------------------------------------------------------------------------
  // travail.base : la dernière ligne de codage enregistrée du testeur sur ce document (référence des compteurs) ;
  // travail.courant : la copie de travail, modifiable ; sauvegardée dans le navigateur jusqu'à « Enregistrer mon codage ».
  const travail = { base: null, courant: null, modifie: false, localEnAttente: null };
  const codageUI = { ressort: null, recherche: null, commentairesOuverts: new Set(), vue: "codage", appelEnCours: false };
  const CLE_CODAGE = () => "codeur.codage." + etat.utilisateur.id + "." + dossier.doc.id;
  function copier(o) { return JSON.parse(JSON.stringify(o)); }

  function sauvegarderLocalCodage() {
    try {
      window.localStorage.setItem(CLE_CODAGE(), JSON.stringify({ version: 1, empreinte: dossier.doc.empreinte, ligne_base: travail.base ? travail.base.id : null,
        courant: travail.courant, enregistreLe: new Date().toISOString() }));
      $("codage-sauvegarde").textContent = "Modifications sauvegardées dans ce navigateur à " + new Date().toLocaleTimeString("fr-FR") + " (non enregistrées dans la base).";
    } catch (e) {
      $("codage-sauvegarde").textContent = "Sauvegarde locale indisponible : enregistrez votre codage avant de fermer la page.";
    }
  }
  function lireLocalCodage() {
    try {
      const b = window.localStorage.getItem(CLE_CODAGE());
      if (!b) return null;
      const c = JSON.parse(b);
      if (c.empreinte !== dossier.doc.empreinte || !c.courant) return null;
      return c;
    } catch (e) { return null; }
  }
  function effacerLocalCodage() { try { window.localStorage.removeItem(CLE_CODAGE()); } catch (e) { /* indisponible */ } }

  // Règle de réouverture (point interprété) : la dernière ligne de la base est la référence ; les modifications locales
  // sont appliquées d'office si elles ont été faites à partir de cette ligne, sinon proposées par un bouton.
  async function chargerCodageExistant() {
    const docId = dossier.doc.id;
    const dernier = await dernierCodage(docId);
    if (!dossier.doc || dossier.doc.id !== docId) return; // un autre dossier a été ouvert entre-temps
    const local = lireLocalCodage();
    if (dernier) installerCodage({ id: dernier.id, etape: dernier.etape, codage: dernier.codage, cree_le: dernier.cree_le }, null);
    if (local) {
      const concorde = (local.ligne_base || null) === (dernier ? dernier.id : null);
      if (concorde) { installerCodage(travail.base, local.courant); $("codage-sauvegarde").textContent = "Modifications non enregistrées retrouvées dans ce navigateur (" + new Date(local.enregistreLe).toLocaleString("fr-FR") + ")."; }
      else {
        travail.localEnAttente = local;
        $("codage-reprise-texte").textContent = "Des modifications non enregistrées du " + new Date(local.enregistreLe).toLocaleString("fr-FR") + " existent dans ce navigateur, faites à partir d'une version antérieure de votre codage.";
        $("codage-reprise").hidden = false; $("bloc-codage").hidden = false;
      }
    }
    if (travail.courant) rendreCodage();
  }
  $("bouton-reprendre-local").addEventListener("click", () => {
    const l = travail.localEnAttente; if (!l) return;
    installerCodage(travail.base, l.courant); travail.modifie = true; $("codage-reprise").hidden = true; travail.localEnAttente = null; rendreCodage(); sauvegarderLocalCodage();
  });
  $("bouton-oublier-local").addEventListener("click", () => { effacerLocalCodage(); travail.localEnAttente = null; $("codage-reprise").hidden = true; });

  // Installe une ligne de base et, le cas échéant, une copie de travail déjà modifiée.
  function installerCodage(ligneBase, courantLocal) {
    travail.base = ligneBase ? { id: ligneBase.id, etape: ligneBase.etape, codage: copier(ligneBase.codage), cree_le: ligneBase.cree_le } : null;
    travail.courant = courantLocal ? copier(courantLocal) : (ligneBase ? copier(ligneBase.codage) : null);
    travail.modifie = !!courantLocal;
    if (travail.courant) {
      travail.courant.passages_non_codes = travail.courant.passages_non_codes || [];
      for (const e of travail.courant.ensembles) { e.preuves = e.preuves || []; e.commentaires = e.commentaires || []; }
    }
    $("bloc-codage").hidden = !travail.courant;
    majBoutons();
    if (travail.base) $("codage-etat").textContent = "Dernier codage enregistré : " + etiquetteEtape(travail.base.etape) + ", le " + new Date(travail.base.cree_le).toLocaleString("fr-FR") + ".";
  }
  function etiquetteEtape(e) { return { ia_humain: "proposition de l'IA", revue_humain: "votre revue", revue_ia: "revue de l'IA", revue_humain_ia: "votre codage final", humain: "codage humain", ia: "pré-codification" }[e] || e; }

  // ---- Rendu
  function rendreCodage() {
    const c = travail.courant;
    if (!c) { $("bloc-codage").hidden = true; return; }
    const variante = varianteAffichage();
    $("bloc-codage").hidden = false;
    $("bloc-codage").className = "bloc-codage " + variante;
    $("texte-dossier").classList.toggle("B", variante === "B");
    // pathologie principale en tête
    c.ensembles.sort((a, b) => (b.categorie === "pathologie_principale") - (a.categorie === "pathologie_principale"));
    const zone = $("codage-contenu"); zone.textContent = "";
    if (!c.ensembles.length) { const p = document.createElement("p"); p.className = "discret"; p.textContent = "Aucun code. Sélectionnez un passage dans le texte pour en créer un."; zone.appendChild(p); }
    c.ensembles.forEach((e, i) => zone.appendChild(rendreCode(e, i)));
    rendreNonCodes();
    $("bouton-enregistrer-codage").disabled = !travail.courant;
    if (!travail.modifie && !$("codage-sauvegarde").textContent.startsWith("Modifications") && !$("codage-sauvegarde").textContent.startsWith("Codage ")) {
      $("codage-sauvegarde").textContent = "Aucune modification depuis le dernier enregistrement. « Enregistrer mon codage » enregistre votre acceptation du codage tel quel.";
    }
    rendreTexte(); rendreCompte();
  }
  function rendreCode(e, i) {
    const div = document.createElement("div");
    div.className = "code " + couleurCode(i) + (codageUI.ressort === i ? " ressort" : "");
    div.dataset.index = i;
    div.addEventListener("mouseenter", () => ressortirCode(i, false));
    div.addEventListener("mouseleave", () => ressortirCode(null, false));
    // glisser-déposer : cible
    div.addEventListener("dragover", (ev) => { ev.preventDefault(); div.classList.add("cible-depot"); });
    div.addEventListener("dragleave", () => div.classList.remove("cible-depot"));
    div.addEventListener("drop", (ev) => { ev.preventDefault(); div.classList.remove("cible-depot");
      try { const d = JSON.parse(ev.dataTransfer.getData("text/plain")); deplacerPreuve(d.de, d.k, i); } catch (x) { /* rien */ } });
    // Style « Neutre » : le texte du code sur sa ligne, puis la ligne des fonctions.
    const tete = document.createElement("div"); tete.className = "tete";
    const titre = document.createElement("strong");
    if (e.code) titre.textContent = e.code + " – " + e.libelle;
    else { titre.textContent = "Code à choisir"; titre.className = "a-choisir"; }
    tete.appendChild(titre); div.appendChild(tete);
    const fonctions = document.createElement("div"); fonctions.className = "fonctions";
    const ico = (texte, titreIco, action, classe) => {
      const b = document.createElement("button"); b.type = "button"; b.className = "ico" + (classe ? " " + classe : "");
      b.textContent = texte; b.title = titreIco; if (action) b.addEventListener("click", action); fonctions.appendChild(b); return b;
    };
    const cat = document.createElement("span");
    cat.className = "etiquette cat" + (e.categorie === "pathologie_principale" ? "" : " associe");
    cat.textContent = (e.categorie === "pathologie_principale" ? "Principal" : "Associé") + " ▾";
    cat.title = "Cliquer pour changer : Principal / Associé";
    cat.addEventListener("click", (ev) => { ev.stopPropagation(); menuCategorie(i, cat); });
    fonctions.appendChild(cat);
    ico("Supprimer", "Supprimer ce code (ses passages redeviennent de simples surlignages)", () => supprimerCode(i));
    ico("🔍", "Changer le code (recherche)", () => ouvrirRecherche(div, i));
    const commentaires = e.commentaires || [];
    const bulle = ico("💬", commentaires.length ? "Commentaires (" + commentaires.length + ")" : "Commentaires", () => basculerCommentaires(i),
      "bulle" + (codageUI.commentairesOuverts.has(i) ? " ouvert" : ""));
    if (commentaires.length) { const n = document.createElement("span"); n.className = "n"; n.textContent = commentaires.length; bulle.appendChild(n); }
    // Les avertissements sont des icônes, leur explication au survol.
    if (!e.code && e.code_propose_non_codable) ico("⚠", "Code proposé par l'IA : " + e.code_propose_non_codable + ", non codable ; choisissez un code avec 🔍.", null, "alerte");
    const plusPrecis = commentaires.find((k) => k.auteur === "outil" && /plus précis possible/.test(k.texte));
    if (e.code && plusPrecis) ico("◎", "Code plus précis possible — " + plusPrecis.texte, null, "info");
    if (!e.preuves.length) ico("◌", "Sans preuve : aucun passage du texte n'appuie ce code. Gardez-le ou supprimez-le.", null, "alerte");
    const ajoutIA = commentaires.find((k) => k.auteur === "outil" && /ajouté aux preuves par l'IA/.test(k.texte));
    if (ajoutIA) ico("⚑", "Preuve ajoutée par l'IA — " + ajoutIA.texte + " Retirez-la avec ✕ si elle ne convient pas.", null, "info");
    if (e.explication || e.confiance != null) ico("ⓘ", "Explication de l'IA : " + (e.explication || "") + (e.confiance != null ? " (confiance " + e.confiance + ")" : ""), null, "info");
    div.appendChild(fonctions);
    const ul = document.createElement("ul"); ul.className = "preuves";
    e.preuves.forEach((p, k) => {
      const li = document.createElement("li"); li.className = "preuve"; li.draggable = true;
      li.textContent = p.texte.length > 140 ? p.texte.slice(0, 137) + "…" : p.texte;
      li.title = "Positions " + p.debut + "–" + p.fin + " — glisser vers un autre code pour déplacer";
      li.addEventListener("dragstart", (ev) => { ev.dataTransfer.setData("text/plain", JSON.stringify({ de: i, k })); ev.dataTransfer.effectAllowed = "move"; });
      li.addEventListener("mouseenter", () => ressortirCode(i, false));
      const outils = document.createElement("span"); outils.className = "outils";
      const croix = document.createElement("button"); croix.className = "croix"; croix.textContent = "✕"; croix.title = "Retirer cette preuve";
      croix.addEventListener("click", () => retirerPreuve(i, k));
      const dep = document.createElement("button"); dep.textContent = "⋯"; dep.title = "Déplacer vers…";
      dep.addEventListener("click", (ev) => { ev.stopPropagation(); menuDeplacer(i, k, ev.target); });
      outils.append(croix, dep); li.appendChild(outils); ul.appendChild(li);
    });
    if (!e.preuves.length) { const li = document.createElement("li"); li.className = "vide"; li.textContent = "aucun passage cité"; ul.appendChild(li); }
    div.appendChild(ul);
    // Les commentaires du code, dans la marge à droite du pavé, masqués par défaut (la saisie arrive à l'étape 3 du brief 7).
    const marge = document.createElement("div"); marge.className = "marge"; marge.hidden = !codageUI.commentairesOuverts.has(i);
    const titreMarge = document.createElement("div"); titreMarge.className = "titre";
    const tt = document.createElement("span"); tt.textContent = "Commentaires · " + (e.code || "code à choisir");
    const fermer = document.createElement("button"); fermer.type = "button"; fermer.className = "secondaire"; fermer.textContent = "fermer";
    fermer.addEventListener("click", () => basculerCommentaires(i));
    titreMarge.append(tt, fermer); marge.appendChild(titreMarge);
    for (const c of commentaires) {
      const l = document.createElement("div"); l.className = "ligne";
      const a = document.createElement("span"); a.className = "auteur"; a.textContent = { humain: "vous", ia: "IA", outil: "outil", generateur: "source" }[c.auteur] || c.auteur;
      const t = document.createElement("span"); t.className = c.auteur === "outil" ? "outil" : ""; t.textContent = c.texte;
      l.append(a, t); marge.appendChild(l);
    }
    if (!commentaires.length) { const pv = document.createElement("p"); pv.className = "discret"; pv.textContent = "Aucun commentaire."; marge.appendChild(pv); }
    div.appendChild(marge);
    return div;
  }
  function basculerCommentaires(i) {
    if (codageUI.commentairesOuverts.has(i)) codageUI.commentairesOuverts.delete(i); else codageUI.commentairesOuverts.add(i);
    rendreCodage();
  }
  function rendreNonCodes() {
    const c = travail.courant; const zone = $("codage-non-codes"); zone.textContent = "";
    const ia = c.passages_non_codes.filter((x) => x.auteur !== "outil"), outil = c.passages_non_codes.filter((x) => x.auteur === "outil");
    const libres = passagesLibres();
    if (!ia.length && !outil.length && !libres.length) { zone.hidden = true; return; }
    zone.hidden = false;
    const bloc = (titre, liste, vide) => {
      const h = document.createElement("strong"); h.textContent = titre; zone.appendChild(h);
      const ul = document.createElement("ul");
      if (!liste.length) { const li = document.createElement("li"); li.className = "discret"; li.textContent = vide; ul.appendChild(li); }
      for (const x of liste) {
        const li = document.createElement("li"); li.textContent = "« " + (x.texte.length > 100 ? x.texte.slice(0, 97) + "…" : x.texte) + " »" + (x.raison ? " — " + x.raison : "");
        const a = document.createElement("a"); a.textContent = "Coder ce passage";
        a.addEventListener("click", (ev) => { ev.stopPropagation(); menuSelection({ debut: x.debut, fin: x.fin, texte: x.texte }, ev.target.getBoundingClientRect(), true); });
        li.appendChild(a); ul.appendChild(li);
      }
      zone.appendChild(ul);
    };
    if (ia.length) bloc("Passages non codés (selon l'IA)", ia, "");
    if (outil.length) bloc("Passages non traités par l'IA", outil, "");
    if (libres.length) bloc("Passages surlignés, pas encore codés", libres.map((p) => ({ ...p, raison: "" })), "");
  }
  function ressortirCode(i, defiler) {
    codageUI.ressort = i;
    document.querySelectorAll("#codage-contenu .code").forEach((d) => d.classList.toggle("ressort", Number(d.dataset.index) === i));
    document.querySelectorAll("#texte-dossier mark.preuve").forEach((m) => m.classList.toggle("ressort", i !== null && m.dataset.codes.split(",").map(Number).includes(i)));
    if (defiler && i !== null) { const d = document.querySelector('#codage-contenu .code[data-index="' + i + '"]'); if (d) d.scrollIntoView({ block: "nearest", behavior: "smooth" }); }
  }

  // ---- Modifications
  function marquerModifie() { travail.modifie = true; rendreCodage(); sauvegarderLocalCodage(); }
  function nettoyerCommentairesChoix(e) { // les remarques de l'outil sur le choix du code disparaissent quand le code change
    e.commentaires = (e.commentaires || []).filter((k) => !(k.auteur === "outil" && /(à choisir|plus précis possible)/.test(k.texte)));
  }
  function changerCode(i, fiche) {
    const e = travail.courant.ensembles[i];
    e.code = fiche.code; e.libelle = fiche.libelle; delete e.code_propose_non_codable; delete e.libelle_propose;
    nettoyerCommentairesChoix(e);
    marquerModifie();
  }
  function retirerPreuve(i, k) { travail.courant.ensembles[i].preuves.splice(k, 1); marquerModifie(); }
  function deplacerPreuve(de, k, vers) {
    if (de === vers) return;
    const p = travail.courant.ensembles[de].preuves.splice(k, 1)[0];
    ajouterPreuveA(vers, p, false); marquerModifie();
  }
  function ajouterPreuveA(i, p, marquer) {
    if (!P.verifier(dossier.doc.texte, p)) { message("message-dossier", "Passage refusé : contrôle des positions en échec.", true); return; }
    const e = travail.courant.ensembles[i];
    if (!e.preuves.some((q) => q.debut === p.debut && q.fin === p.fin)) { e.preuves.push({ debut: p.debut, fin: p.fin, texte: p.texte }); e.preuves.sort((a, b) => a.debut - b.debut); }
    retirerDesNonCodes(p);
    if (marquer !== false) marquerModifie();
  }
  function retirerDesNonCodes(p) {
    travail.courant.passages_non_codes = travail.courant.passages_non_codes.filter((x) => !(x.debut === p.debut && x.fin === p.fin));
    dossier.passages = dossier.passages.filter((x) => !(x.debut === p.debut && x.fin === p.fin));
  }
  function supprimerCode(i) {
    const e = travail.courant.ensembles.splice(i, 1)[0];
    for (const p of e.preuves) if (!dossier.passages.some((x) => x.debut === p.debut && x.fin === p.fin)) dossier.passages.push({ debut: p.debut, fin: p.fin, texte: p.texte });
    dossier.passages = trierPassages(dossier.passages); sauvegarderLocal();
    marquerModifie();
  }
  function designerPrincipal(i) {
    travail.courant.ensembles.forEach((e, k) => { e.categorie = k === i ? "pathologie_principale" : (e.categorie === "pathologie_principale" ? "diagnostic_associe" : e.categorie); });
    marquerModifie();
  }
  function nouveauCode(fiche, p) {
    travail.courant.ensembles.push({ code: fiche.code, libelle: fiche.libelle, categorie: "diagnostic_associe", preuves: [], confiance: null, explication: null, commentaires: [] });
    const i = travail.courant.ensembles.length - 1;
    if (p) ajouterPreuveA(i, p, false);
    marquerModifie();
  }

  // ---- Menus
  function fermerMenus() { $("menu-selection").hidden = true; $("menu-flottant").hidden = true; }
  document.addEventListener("click", (ev) => { if (!ev.target.closest(".menu-selection, .etiquette.cat, .outils")) fermerMenus(); });
  function placerMenu(menu, rect) {
    menu.hidden = false;
    const x = Math.max(8, Math.min(window.innerWidth - menu.offsetWidth - 8, rect.left + window.scrollX));
    menu.style.left = x + "px"; menu.style.top = (rect.bottom + window.scrollY + 6) + "px";
  }
  function bouton(menu, texte, action) { const b = document.createElement("button"); b.textContent = texte; b.addEventListener("click", () => { fermerMenus(); action(); }); menu.appendChild(b); }
  function menuSelection(passage, rect, depuisNonCode) {
    const menu = $("menu-selection"); menu.textContent = "";
    const t = document.createElement("div"); t.className = "titre"; t.textContent = "« " + (passage.texte.length > 40 ? passage.texte.slice(0, 37) + "…" : passage.texte) + " »"; menu.appendChild(t);
    travail.courant.ensembles.forEach((e, i) => bouton(menu, "Ajouter à " + (e.code || "code à choisir") + (e.libelle ? " – " + e.libelle.slice(0, 40) : ""), () => { ajouterPreuveA(i, passage); window.getSelection().removeAllRanges(); }));
    bouton(menu, "Nouveau code…", () => { window.getSelection().removeAllRanges(); ouvrirRecherche(null, null, passage); });
    if (!depuisNonCode) bouton(menu, "Surligner seulement (pour un prochain codage)", () => { surlignerSimple(passage); rendreCodage(); });
    placerMenu(menu, rect);
  }
  function menuCategorie(i, ancre) {
    const menu = $("menu-flottant"); menu.textContent = "";
    bouton(menu, "Principal", () => designerPrincipal(i));
    bouton(menu, "Associé", () => { travail.courant.ensembles[i].categorie = "diagnostic_associe"; marquerModifie(); });
    placerMenu(menu, ancre.getBoundingClientRect());
  }
  function menuDeplacer(de, k, ancre) {
    const menu = $("menu-flottant"); menu.textContent = "";
    const t = document.createElement("div"); t.className = "titre"; t.textContent = "Déplacer vers…"; menu.appendChild(t);
    travail.courant.ensembles.forEach((e, i) => { if (i !== de) bouton(menu, (e.code || "code à choisir") + (e.libelle ? " – " + e.libelle.slice(0, 40) : ""), () => deplacerPreuve(de, k, i)); });
    bouton(menu, "Nouveau code…", () => { const p = travail.courant.ensembles[de].preuves.splice(k, 1)[0]; ouvrirRecherche(null, null, p); });
    placerMenu(menu, ancre.getBoundingClientRect());
  }

  // ---- Recherche 🔍 : codes codables seulement ; début de code en tête, puis ressemblance (seuil 0,3), puis début de mot
  function ouvrirRecherche(conteneur, i, passagePourNouveau) {
    document.querySelectorAll(".recherche-code").forEach((x) => x.remove());
    const e = i !== null && i !== undefined ? travail.courant.ensembles[i] : null;
    const boite = document.createElement("div"); boite.className = "recherche-code";
    const champ = document.createElement("input"); champ.placeholder = "Code (I10, K40…) ou mots (hypertension, HTA…)";
    champ.value = "";
    const info = document.createElement("div"); info.className = "rc-titre";
    info.textContent = e ? (e.code ? "Choisissez le nouveau code : les preuves restent attachées." : "Code à choisir : suggestions issues de la boucle de correction, ou tapez une recherche.") : "Choisissez le code du nouveau passage.";
    const liste = document.createElement("ol");
    const fermer = document.createElement("button"); fermer.className = "secondaire"; fermer.textContent = "Fermer"; fermer.style.marginTop = ".4rem";
    fermer.addEventListener("click", () => boite.remove());
    boite.append(champ, info, liste, fermer);
    if (conteneur) conteneur.appendChild(boite); else $("codage-contenu").prepend(boite);
    let minuteur = null, serie = 0, afficherAvecChoix = null;
    const choisir = (fiche) => { boite.remove(); if (e) changerCode(i, fiche); else nouveauCode(fiche, passagePourNouveau); };
    const afficher = (sections) => {
      liste.textContent = "";
      for (const sec of sections) {
        if (!sec.liste.length) continue;
        const t = document.createElement("li"); t.className = "rc-titre"; t.textContent = sec.titre; t.style.cursor = "default"; liste.appendChild(t);
        for (const f of sec.liste) {
          const li = document.createElement("li");
          const c = document.createElement("span"); c.className = "rc-code"; c.textContent = f.code;
          const l = document.createElement("span"); l.textContent = f.libelle;
          li.append(c, l);
          if (f.formulation && f.formulation !== f.libelle) {
            const fo = document.createElement("span"); fo.className = "rc-form"; fo.textContent = "← " + f.formulation;
            if (f.source || f.origine) fo.title = "Formulation : « " + f.formulation + " » — source : " + (f.source || "?") + " — origine : " + ({ libelle: "libellé officiel", inclusion: "inclusion", index: "index de la CIM-10", synonyme: "synonyme" }[f.origine] || f.origine || "?");
            li.appendChild(fo);
          }
          li.addEventListener("click", () => (afficherAvecChoix || choisir)(f));
          liste.appendChild(li);
        }
      }
      if (!liste.children.length) { const li = document.createElement("li"); li.className = "discret"; li.textContent = "Aucun code codable trouvé."; liste.appendChild(li); }
    };
    let derniereRecherche = null; // pour le journal des recherches
    const contexte = e ? (e.code ? "changement_code" : "code_a_choisir") : "nouveau_code"; // valeurs de SCHEMA.md §5.4
    // Suggestions avant toute frappe : pour un code à choisir, les candidats de la boucle de correction (descendants du
    // code proposé, codables de sa catégorie, ressemblance avec le libellé du modèle) ; pour un code plus précis possible,
    // ses descendants codables. Dès la frappe, la recherche normale les remplace.
    const suggestions = async () => {
      const sections = [];
      if (!e) return sections;
      if (e.code) {
        const d = await base.from("descendants_codables").select("code, libelle").eq("noeud", e.code).order("ordre_kit");
        if (!d.error && d.data.length) sections.push({ titre: "Codes plus précis que " + e.code, liste: d.data });
        return sections;
      }
      const propose = e.code_propose_non_codable ? K.normaliserCode(e.code_propose_non_codable) : "";
      if (propose) {
        const d = await base.from("descendants_codables").select("code, libelle").eq("noeud", propose).order("ordre_kit");
        if (!d.error && d.data.length) sections.push({ titre: "Codes codables possibles (descendants de " + propose + ")", liste: d.data });
        else {
          const cat = await candidatsDeCategorie(propose, 20);
          if (cat.length) sections.push({ titre: "Codes codables de la catégorie " + propose.slice(0, 3), liste: cat });
        }
      }
      if (e.libelle_propose) {
        const r = await base.rpc("rechercher_codes", { recherche: e.libelle_propose, limite: 20, seuil: 0.15 });
        if (!r.error && r.data.length) sections.unshift({ titre: "Codes dont une formulation ressemble au libellé proposé par l'IA (« " + e.libelle_propose.slice(0, 50) + (e.libelle_propose.length > 50 ? "…" : "") + " »)", liste: r.data });
      }
      return sections;
    };
    const lancer = async () => {
      const q = champ.value.trim(); const n = ++serie;
      let sections = [];
      let mode = null, nb = 0;
      if (!q.length) { sections = await suggestions(); if (n === serie) { afficher(sections); derniereRecherche = null; } return; }
      if (q.length) {
        // 1. un code tapé (M84, C50) est toujours cherché par début de code, en tête
        if (/^[a-z][0-9]/i.test(q) && !/\s/.test(q)) {
          const r = await base.from("fiches").select("code, libelle").ilike("code", K.normaliserCode(q) + "%").eq("codable", true).order("code").limit(40);
          if (!r.error && r.data.length) { sections.push({ titre: "Codes commençant par " + K.normaliserCode(q), liste: r.data }); mode = "code"; nb += r.data.length; }
        }
        // 2. par morceaux de mots (à partir de trois caractères) : les formulations qui contiennent tous les morceaux
        const r = q.length >= 3 ? await base.rpc("rechercher_codes_morceaux", { recherche: q, limite: 40 }) : { error: null, data: [] };
        if (!r.error && r.data.length) {
          sections.push({ titre: "Codes contenant « " + q + " »", liste: r.data.map((x) => ({ code: x.code, libelle: x.libelle, formulation: x.dans_libelle ? null : x.formulation })) });
          if (q.length < 3) { /* jamais atteint : en dessous de trois caractères, seule la recherche par début de code est faite */ }
          mode = mode || "morceaux"; nb += r.data.length;
        } else if (q.length >= 3) {
          // 3. secours : ressemblance (orthographe approchée), signalée comme telle
          const s2 = await base.rpc("rechercher_codes", { recherche: q, limite: 20, seuil: 0.3 });
          if (!s2.error && s2.data.length) { sections.push({ titre: "Aucune formulation ne contient « " + q + " » ; orthographe approchée (ressemblance) :", liste: s2.data }); mode = mode || "ressemblance"; nb += s2.data.length; }
        }
      }
      if (n === serie) {
        if (q.length && q.length < 3 && !sections.length) { const li = document.createElement("li"); liste.textContent = ""; li.className = "discret"; li.textContent = "Tapez au moins trois caractères (ou un début de code, par exemple I1)."; liste.appendChild(li); }
        else afficher(sections);
        derniereRecherche = q.length ? { texte: q, mode: mode || "morceaux", nb } : null;
      }
    };
    const journaliser = (codeChoisi) => {
      if (!derniereRecherche) return;
      base.from("recherches").insert({ utilisateur: etat.utilisateur.id, document: dossier.doc.id, texte: derniereRecherche.texte, mode: derniereRecherche.mode,
        nb_resultats: derniereRecherche.nb, code_choisi: codeChoisi || null, contexte }, { returning: "minimal" }).then(() => {}, () => {});
      derniereRecherche = null;
    };
    const choisirEtJournaliser = (fiche) => { journaliser(fiche.code); choisir(fiche); };
    afficherAvecChoix = choisirEtJournaliser;
    fermer.addEventListener("click", () => journaliser(null));
    champ.addEventListener("input", () => { clearTimeout(minuteur); minuteur = setTimeout(lancer, 300); });
    champ.focus(); lancer();
  }

  // ---- Enregistrer mon codage : ligne revue_humain (bouton, et enregistrement automatique avant un appel répété)
  async function enregistrerRevue() {
    const codage = copier(travail.courant);
    codage.affichage = varianteAffichage();
    const compteurs = K.compteurs(travail.base ? travail.base.codage : null, codage);
    const ins = await base.from("codages").insert({ document: dossier.doc.id, etape: "revue_humain", utilisateur: etat.utilisateur.id,
      codage_precedent: travail.base ? travail.base.id : null, appel_llm: null, valide: false, compteurs, codage }).select("id, cree_le").single();
    if (ins.error) throw new Error(ins.error.message);
    effacerLocalCodage();
    installerCodage({ id: ins.data.id, etape: "revue_humain", codage, cree_le: ins.data.cree_le }, null);
    return { id: ins.data.id, compteurs };
  }
  $("bouton-enregistrer-codage").addEventListener("click", async () => {
    if (!travail.courant) return;
    const b = $("bouton-enregistrer-codage"); b.disabled = true;
    const sansModification = !travail.modifie;
    try {
      const { compteurs } = await enregistrerRevue();
      const heure = new Date().toLocaleTimeString("fr-FR");
      $("codage-sauvegarde").textContent = sansModification
        ? "Codage accepté tel quel, enregistré dans la base à " + heure + " (votre revue, tout conservé : " + compteurs.conserves + " code(s))."
        : "Codage enregistré dans la base à " + heure + " (votre revue). Compteurs : " + compteurs.conserves + " conservé(s), " + compteurs.modifies + " modifié(s), " + compteurs.preuves_modifiees + " preuves modifiées, " + compteurs.retires + " retiré(s), " + compteurs.ajoutes + " ajouté(s).";
      message("message-dossier", sansModification ? "Votre acceptation du codage tel quel est enregistrée." : "Votre codage est enregistré.");
      rendreCodage();
    } catch (e) {
      message("message-dossier", "L'enregistrement a échoué : " + e.message, true);
      b.disabled = false;
    }
  });

  // --- Après connexion : profil existant ou parcours d'inscription --------------------------------------
  let demarreePour; // identifiant de l'utilisateur (ou "deconnecte") pour lequel le démarrage a déjà eu lieu
  async function demarrer(session) {
    // La page reçoit la session deux fois à l'ouverture (lecture de la session, puis événement de changement
    // d'état) : le démarrage ne se fait qu'une fois par utilisateur connecté, pour ne lancer qu'une fois les
    // lectures et affichages qui suivent (profil, mention, liste).
    const cle = session && session.user ? session.user.id : "deconnecte";
    if (demarreePour === cle) return;
    demarreePour = cle;
    const connecte = !!(session && session.user);
    $("utilisateur-courant").hidden = !connecte;
    $("bouton-deconnexion").hidden = !connecte;
    $("bouton-profil").hidden = true;
    $("bouton-reglages").hidden = true;
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
    if (!data) { await afficherMention(false); return; }
    const m = await lireMention();
    if (m.erreur) { erreur("La mention d'information n'a pas pu être lue (" + m.erreur + "). Signalez-le au responsable du projet."); return; }
    if (data.version_mention !== m.version) { await afficherMention(true); return; }
    $("bouton-profil").hidden = false;
    $("bouton-reglages").hidden = false;
    etat.reglages = lireReglages();
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
