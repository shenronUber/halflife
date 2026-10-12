# Contrats d’équipement, sauvegardes et modèle opérateur

<!-- generated-contract:start -->

| Contrat courant | Valeur |
| --- | ---: |
| API renderer | 4 |
| Pièces par assemblage | 24 |
| Assemblages actifs | 96 |
| Modèles en cache | 2048 |
| Protocole équipement | 5 |
| VFBuild (octets) | 66 |
| VFState (octets) | 77 |
| Capacité catalogue | 2048 |

<!-- generated-contract:end -->

La version actuelle utilise le protocole réseau 5 : indices d’objet sur 16 bits,
`VFBuild` de 66 octets et `VFState` de 77 octets. Les
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

Les sauvegardes écrivent les identifiants textuels des 22 objets, des 12
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

- `vector-fields/build.ps1` prépare un candidat privé complet, compile les deux DLL et exécute les validations
  d’équipement, de migration, d’effets et de géométrie/impacts.
- `python vector-fields/tests/architecture_engine_test.py` teste les vraies DLL
  dans une session privée `build/native-sessions/…/vf_architecture`, avec un moteur sans affichage.
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

`build.ps1` délègue à `build_release.py` : les tests C++ de gameplay/persistance et les suites Python
`unit`, `policy`, `assets` et `integration` doivent réussir avant publication. La suite `policy` recompile les tests C++ avant
chaque exécution, pour éviter qu’un ancien exécutable valide de nouvelles sources.
`validate.py --suite native` et `--suite multiplayer`
séparent les vérifications qui lancent le moteur. `validate.py --suite all`
enchaîne les cinq suites après compilation et déploiement. Une réussite
unitaire ne prétend pas valider l’esthétique de toutes les combinaisons.

## Persistance des déplacements

Le mouvement partagé transporte sa phase dans `iuser4`, sa durée restante dans
`fuser1`, son ancrage horizontal dans `vuser3.x/y` et la hauteur du rebord dans
`fuser4`. Ces champs ne figurent pas dans la table historique des entvars.
`CBasePlayer` les sauvegarde explicitement : entier, durée `FIELD_FLOAT` et
ancrage `FIELD_POSITION_VECTOR`, pour suivre les translations de landmark.
La restauration valide la phase, le yaw encodé, les durées et les coordonnées.
Une ancienne sauvegarde ou une réapparition sans landmark repart en état normal.
Le prochain mouvement recontrôle le support et les collisions. `vuser3.z`,
réservé aux munitions, reste indépendant. La prédiction des armes copie phase
et durée depuis le même état client, afin de bloquer le tir pendant le dégainé.

## Runtimes de validation

Les suites qui créaient des copies complètes du moteur passent par
`native_workspace.py`. Les sessions sont distinctes entre processus et supprimées
après archivage des logs/captures. Le cache des ressources est indépendant du
runtime principal : ses fichiers sont identifiés par contenu et partagés par
liens physiques. Une surcharge de ressource détache le lien avant écriture.
Les anciennes versions inutilisées du cache sont retirées après validation.
Les sources des ateliers, même ignorées par Git, ne font jamais partie de ce cycle.

## Assemblages et sessions de validation

La topologie d’un assemblage (porteur, modèles, modes et sockets) reste en cache.
Les transformations, groupes de corps, finitions et phases de casque sont validés
séparément puis appliqués à la pose ; ils ne reconstruisent pas les cartes d’os.
Les effets de mort parcourent des listes compactes d’entités actives, retirées à
expiration et réinitialisées au changement de carte. Les budgets physiques et
le pool de particules restent inchangés.

`runtime_contract.py` lit les emplacements et tailles du contrat C++ pour les
harnesses Python. `validate.py` inclut les gestes, le HUD/audio des casques,
le parcours de franchissement et le combat en glissade. Les anciens essais du
menu et de l’architecture utilisent des sessions privées ; le renderer nul est
compilé dans sa propre session. Les ressources Half-Life originales sont lues
par `-rodir`, avec une zone d’écriture locale pour les caches.

Les preuves sont archivées dans un dossier temporaire puis publiées sous un
verrou propre au scénario. Une archive échouée conserve la preuve précédente.
Les liens de ressources et la mise à jour/pruning de leur index sont protégés
par le même verrou de cache. Les tests unitaires exercent deux processus qui
publient simultanément le même scénario.

`tests/performance_native_test.py --pairs 3` compare les binaires conservés sous
`build/maintenance-perf` en alternant l’ordre A/B. Le profiler `vf_perf` est
inactif par défaut ; ses requêtes GPU sont asynchrones. Les résultats détaillent
le rendu/HUD CPU, le GPU hors présentation et l’intervalle mural entre images.
Le corps subjectif peut être isolé pour cette mesure avec `vf_first_person_body`.

Le renderer de corps version 2 aligne la copie subjective pendant la marche et fournit les jambes de glissade dans le monde. L'API native reste en version 4 ; le marqueur client `VFBody motion: world slide=1` impose cette capacité sans modifier le protocole réseau. Le lanceur refuse un renderer ancien ou un candidat dont la validation du corps n'a pas été effectuée. La livraison remplace seulement le renderer et les DLL SDK effectivement modifiées, avec contrôle des empreintes ; le cœur moteur audité et les banques d'animation restent en place.


## Publication et cartes partagées

`build_release.py` est la publication principale. Il fige les sources, prépare moteur, DLL, cartes et ressources dans `build/releases/<id>`, puis lie les preuves de validation aux empreintes du paquet. Il refuse un candidat non validé, altéré, ou issu de sources dépassées. Le verrou commun couvre construction, publication et lancement. Le mod complet est remplacé par renommage avec sauvegarde et retour arrière ; les sauvegardes du joueur sont conservées.

`game_profiles.py` déclare la recette et le dossier source de chaque carte. Ce registre pilote préparation, livraison et contrôle des cartes. `vf_range` contient le tir et les obstacles de `course_boxes()` dans une aile reliée ; `vf_modular` utilise les mêmes DLL et ressources. L'ancienne carte `vf_traversal` reste une référence de régression.

Les modifications du moteur passent d'abord par `build-engine.ps1`, dont la destination par défaut est le candidat privé `build/engine-candidate`. Son empreinte de sources est contrôlée avant et après compilation. Le paquet n'est publié qu'après les essais d'intégration. Un ancien candidat incompatible ne remplace pas le moteur installé.

Le lancement rapide vérifie le manifeste publié, sans reconstruire. Un ajout de carte exige une entrée du registre, une recette déterministe et une couverture native. Voir [le workflow](BUILD-WORKFLOW.md) pour les branches et la préparation d'un nouveau worktree.
