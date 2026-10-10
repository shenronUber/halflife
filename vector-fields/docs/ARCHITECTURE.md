# Contrats d’équipement, sauvegardes et modèle opérateur

<!-- generated-contract:start -->

| Contrat courant | Valeur |
| --- | ---: |
| API renderer | 3 |
| Pièces par assemblage | 24 |
| Assemblages actifs | 96 |
| Modèles en cache | 2048 |
| Protocole équipement | 4 |
| VFBuild (octets) | 64 |
| VFState (octets) | 75 |
| Capacité catalogue | 2048 |

<!-- generated-contract:end -->

La version actuelle utilise le protocole réseau 4 : indices d’objet sur 16 bits,
`VFBuild` de 64 octets et `VFState` de 75 octets. Les
indices et les empreintes des catalogues restent les données de transport :
un client dont le catalogue diffère ne peut pas appliquer ses indices au serveur.

## Validation faisant autorité

`vf_apply` valide les budgets, l’emplacement de chaque objet et le sous-ensemble
de gameplay. Seuls épaules, ceinture, bouclier et spécial peuvent rester vides.
Les cinq autres zones opérateur exigent une apparence produite. Les douze
emplacements d’arme exigent les objets R-01 nommés du catalogue actuel.
Chaque objet possède `model` et `weaponStyle`, validés à la lecture puis lors
de l’application. Le modèle de travail doit exister sur le même emplacement,
avec les mêmes coûts et la même famille ; le rendu utilise sa clé de modèle.
Les variantes gardent une clé d’inventaire distincte, par exemple
`r01_receiver_arch_top__dieselpunk`. Une finition falsifiée est refusée.

Le catalogue accepte 2 048 entrées et un fichier ASCII de 1 Mio. Les lignes
historiques gardent 14 colonnes, les objets GIGN 15, les variantes d’arme 17 :
apparence GIGN vide, clé du modèle de travail, clé de finition. Les modèles de
travail R-01 restent sélectionnables uniquement dans l’espace développeur.

`vf_apply_dev` conserve les objets historiques et les emplacements libres du
laboratoire. Il est disponible en solo ou avec `sv_cheats` en multijoueur. Dès
qu’une pièce R-01 est présente, les douze pièces doivent appartenir au R-01,
y compris dans le laboratoire. Un assemblage incomplet ou mixte est refusé
atomiquement ; le rendu ne remplace plus silencieusement une pièce historique
par une pièce R-01. Le mode Apparence libre suit la même autorisation.

Le bouton Retour au jeu restaure le choix de gameplay mémorisé par le client ;
`vf_gameplay` normalise aussi l’équipement côté serveur et quitte les modes
expérimentaux. Les anciens catalogues de laboratoire sans apparences produites
restent compatibles.

## Persistance par identifiants

Les sauvegardes écrivent les identifiants textuels des 21 objets, des 12
finitions et des 5 apparences libres dans des champs `FIELD_STRING`. Ces
identifiants doivent rester stables lorsqu’on ajoute, réordonne ou renomme
l’affichage d’un contenu. Une modification de commentaire change l’empreinte
de synchronisation, mais conserve les objets sauvegardés.

Les anciens identifiants R-01 et leurs finitions séparées sont restaurés avant
la normalisation du mode jeu, puis convertis vers leur objet nommé correspondant.
Cette conversion est idempotente et préserve les finitions mixtes.

Au rechargement d’un catalogue modifié, chaque choix est retrouvé par son
identifiant. Un objet supprimé ou déplacé dans un autre emplacement est remplacé
par le défaut de son seul emplacement ; une finition ou apparence supprimée
revient à l’entrée zéro. Un emplacement optionnel explicitement vide reste vide.
L’ensemble passe ensuite par la validation : si les nouvelles règles ou les
nouveaux budgets rendent l’ensemble invalide, une normalisation peut être
nécessaire.

`game_shared/vf_legacy_save.h` fige les dictionnaires de la version 0.14.0
antérieure à ces champs. Ils permettent d’importer ses anciennes sauvegardes
numériques, même après réordonnancement des catalogues. Ne pas régénérer ces
dictionnaires. Une sauvegarde numérique d’un catalogue plus ancien dont
l’empreinte est inconnue ne contient pas assez d’information pour retrouver
les objets : elle revient aux choix par défaut.

## Squelette et impacts

`vf::OperatorRig` choisit le même modèle porteur côté serveur et côté client.
Les cinq zones ajustées GIGN utilisent `persona_rig.mdl`. Les mélanges avec
un corps historique utilisent encore `vf_operator.mdl`.

Le modèle GIGN conserve les 77 séquences attendues par le code joueur. Ses
21 zones d’impact et leurs groupes anatomiques proviennent du donneur GIGN,
transformés dans les coordonnées de ses os ajustés. Il contient aussi le corps
complet utilisé lorsque le rendu modulaire est absent, notamment pour le corps
au sol. Le moteur masque ce corps porteur pendant le rendu modulaire normal.

## Bras en première personne

Les bras R-01 sont deux pièces fusionnées sur le squelette animé :
`r01_fp_gloves.mdl` et `r01_fp_sleeves.mdl`. `FirstPersonSkin` résout
l’apparence de l’objet porté dans les emplacements gants (2) et torse (3).
Chaque pièce possède les quatorze familles de textures du personnage.
L’état existant de l’équipement suffit ; aucun champ réseau ou sauvegardé
supplémentaire ne duplique ce choix.

Le rig conserve les animations ; ses anciennes mains intégrées sont masquées.
Les douze pièces d’arme et les deux éléments du bras occupent quatorze des
vingt-quatre emplacements moteur. Les trois rigs partagent les noms et poses de
liaison des os. `build_first_person.py` réutilise les pixels des tenues à leur
résolution native dans deux atlas dédiés, avec UV continus sur la main et
centrage progressif sur chaque doigt, partagé avec la paume pour éviter les coutures triangulaires. Les panneaux sous l’avant-bras suivent le torse.
La plaque rigide est supprimée pour exposer le gant fermé existant ; 334 triangles supplémentaires
arrondissent les doigts, uniquement sur des bords dont les sommets suivent
le même os. Les poids aux articulations et le squelette sont conservés.
Les modèles et textures du personnage à la troisième personne restent intacts.
Le chargeur latéral conserve son contact main/chargeur pendant la recharge ;
le solveur choisit un coude bas en réduisant la flexion du poignet.

## Vérifications

- `vector-fields/build.ps1` compile les deux DLL et exécute les validations
  d’équipement, de migration, d’effets et de géométrie/impacts.
- `python vector-fields/tests/architecture_engine_test.py` teste les vraies DLL
  dans `runtime/vector-engine/vf_architecture`, avec un moteur sans affichage.
  Il vérifie les refus côté serveur, les autorisations multijoueurs, les deux
  squelettes et les sauvegardes après réordonnancement des trois catalogues.
  Il importe aussi l’ancienne sauvegarde de contrôle 0.14 si elle est présente.
  Ce test nécessite le moteur construit, les ressources `vf_visual` déployées
  et les outils C++ Visual Studio ; il ne vérifie pas les pixels.
- `gameplay_engine_test.py` et `current_release_test.py` vérifient le parcours
  natif et les sauvegardes avec le rendu graphique après déploiement.

Les rapports sont écrits dans `vector-fields/build/`. La commande serveur
`cmd vf_model_info` affiche le modèle joueur, le mode expérimental et les
catégories d’identifiants persistés.

## Caractéristiques partagées des modèles

`data/model_contract.json` est la source des montages de chargeur des neuf
châssis, de la prise de la poignée avant, des neuf chemins de porteurs et des
sockets première et troisième personne. `model_contract.py` valide ces données
et génère `game_shared/vf_model_contract.h`. Le client et le serveur choisissent
le même porteur. Les variantes nommées héritent des traits de leur `ItemModel` ;
les identifiants de sauvegarde et le protocole ne changent pas.

Les auteurs d’animations gardent leur correspondance de joints établie, vérifiée
par nom contre le squelette source du contrat. Un changement de donneur qui
réordonne les joints produit une erreur explicite, avant compilation, au lieu
de poser silencieusement un bras ou un chargeur sur le mauvais os.

## Génération et livraison

`build_cache.py` empreinte les noms, longueurs et contenus des entrées et vérifie
les empreintes des sorties. Les recettes, donneurs SMD/QC/BMP, auxiliaires de
retargeting, compilateur StudioMDL et ressources de texture pertinentes font
partie des dépendances. Un fichier compilé manquant ou altéré invalide le cache.
Un ancien cache incomplet impose une première reconstruction.

Le R-01 a deux étapes : pièces/textures et rigs animés. Une retouche de recette de prise ou de script de geste dédié
reconstruit uniquement les six rigs. Un changement du bind
pose ou du compilateur reconstruit aussi les pièces concernées. Les caches sont
écrits après succès. Les rigs tiers-personne supportent également `--ensure`.

`release.deployment_files` inventorie les DLL, catalogues, effets et modèles
requis, y compris les trois porteurs tiers-personne. Le lanceur puis le test de
release vérifient leurs empreintes installées. Une liste de fichiers obtenue
par glob vide ne peut plus cacher la disparition d’un modèle requis.

`build.ps1` exécute les tests C++ de gameplay/persistance et les suites Python
`unit` et `assets`. `validate.py --suite native` et `--suite multiplayer`
séparent les vérifications qui lancent le moteur. `validate.py --suite all`
enchaîne les quatre suites après compilation et déploiement. Une réussite
unitaire ne prétend pas valider l’esthétique de toutes les combinaisons.
