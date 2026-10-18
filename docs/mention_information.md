# Mention d'information et accord des testeurs — premier jet

*Proposition à relire et à compléter. Les passages entre crochets `[À COMPLÉTER]` demandent une information que je n'ai pas. Ce texte n'est pas un avis juridique : dans un cadre AP-HP, il est prudent de le faire relire par le délégué à la protection des données (DPO) avant la diffusion.*

*Le texte est conçu pour s'afficher à la première connexion, avant la fiche d'inscription. Il est volontairement court ; un lien « En savoir plus » peut mener à une version détaillée si nécessaire.*

---

## Bienvenue dans `codeur`

`codeur` est un **prototype de recherche** qui permet de tester l'aide au codage CIM-10 par l'intelligence artificielle. Il s'inscrit dans le projet [À COMPLÉTER : nom du projet et des partenaires], conduit par [À COMPLÉTER : organisme responsable].

### Ce que vous allez faire

Vous allez coder des **comptes rendus d'hospitalisation entièrement fictifs** : aucun ne concerne un patient réel. Un modèle d'IA vous proposera des codes, que vous accepterez, corrigerez ou rejetterez. Vous pourrez aussi noter la qualité des comptes rendus.

### Une règle impérative

**N'introduisez jamais de données concernant un patient réel**, ni dans les textes, ni dans les commentaires. L'outil est conçu pour des documents fictifs uniquement.

### Les données que nous recueillons

- **Votre profil** : nom, prénom, adresse électronique, statut professionnel, établissement.
- **Votre travail dans l'outil** : vos codages, à chaque étape, vos commentaires, vos notes de qualité, les dates de vos actions.
- **Les échanges avec le modèle d'IA** : les demandes envoyées et les réponses reçues, le modèle utilisé, le nombre de tokens consommés.

**Votre clé d'accès au modèle d'IA n'est jamais recueillie** : elle reste enregistrée dans votre navigateur, sur votre ordinateur. Vous pouvez l'effacer à tout moment avec le bouton « Oublier mes réglages ». Les appels au modèle se font avec votre propre clé, sous les conditions de votre fournisseur ([À COMPLÉTER : par défaut, Mistral AI]).

### À quoi servent ces données

- faire fonctionner l'outil et retrouver votre travail d'une session à l'autre ;
- **évaluer l'aide au codage par l'IA** : qualité des propositions, accord entre les codeurs, accord avec le codage de référence ;
- **constituer des jeux de données** pour améliorer les modèles de codage.

Les résultats publiés et les jeux de données diffusés ne contiendront **ni votre nom, ni votre adresse électronique**. [À COMPLÉTER : préciser si le statut et l'établissement peuvent apparaître sous forme agrégée.]

### Où sont-elles conservées, et combien de temps

Les données sont hébergées par Supabase, dans l'Union européenne (Irlande). Elles sont conservées [À COMPLÉTER : durée, par exemple jusqu'à la fin du projet et au plus N ans]. Seule l'équipe du projet y a accès : [À COMPLÉTER : liste ou description].

### Vos droits

Vous pouvez demander à consulter, corriger ou supprimer vos données, ou vous opposer à leur utilisation, en écrivant à [À COMPLÉTER : adresse de contact]. Vous pouvez aussi contacter le délégué à la protection des données de [À COMPLÉTER : organisme] à [À COMPLÉTER], ou adresser une réclamation à la CNIL.

[À COMPLÉTER : préciser ce que devient votre travail si vous demandez la suppression de vos données — par exemple suppression complète, ou conservation sous forme anonymisée.]

---

## Votre accord

Pour utiliser l'outil, cochez les deux cases :

- ☐ J'ai lu cette information et je m'engage à n'introduire **aucune donnée concernant un patient réel**.
- ☐ J'accepte que mon travail dans l'outil (codages, commentaires, notes) soit utilisé **à des fins de recherche**, dans les conditions décrites ci-dessus.

[Bouton : Continuer vers la fiche d'inscription]

*La date de votre accord est enregistrée avec votre profil.*

---

## Notes pour la mise en œuvre (non affichées)

1. **Deux cases distinctes**, toutes deux obligatoires : l'engagement sur les données réelles, et l'accord pour la recherche.
2. **La date d'accord** est enregistrée dans `profils.accord_le`. Si la mention change de façon importante, il faudra pouvoir redemander l'accord : enregistrer aussi la **version de la mention** acceptée serait utile (petite évolution du schéma, à discuter).
3. **La règle sur les données réelles** prend toute son importance avec la page d'édition (lot A6), qui permet de modifier un texte : un rappel y sera affiché.
4. **Le texte de la mention** est un fichier du dépôt (par exemple `docs/mention_information.md`), affiché par la page : on garde ainsi une trace de chaque version.
