# Extension native Vector Fields, version 3

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

Base : Xash3D FWGS `9137964147d8f749dbeddf1cb5482c3d16f86e4a`.
Source officielle : https://github.com/FWGS/xash3d-fwgs

Le moteur modifié est installé dans `runtime/vector-engine`. La copie officielle
et le prototype précédent restent dans `runtime/xash3d`. Le moteur local est
une dérivation de Xash3D, pas le code propriétaire de GoldSrc.
Le fichier `vector-engine-build.json` du runtime identifie la base, le patch et
les empreintes des exécutables produits.

## Recompiler sous Windows

Préparer le dépôt officiel dans `runtime/engine-source`, avec ses sous-modules
au commit ci-dessus. Installer Python 3.10 et Visual Studio 2022 Build Tools
17.4, outils C++ x86 et Windows SDK 10.0.22000.0 (versions utilisées ici).
Décompresser le SDK Visual C++ SDL2 2.32.10 sous
`devtools/SDL2-sdk/SDL2-2.32.10` :
https://github.com/libsdl-org/SDL/releases/tag/release-2.32.10

```powershell
./vector-fields/build-engine.ps1 -Configure
./vector-fields/build.ps1
python vector-fields/build_sockets.py
python vector-fields/play.py --native-engine --deploy-only
python vector-fields/tests/native_engine_test.py
python vector-fields/tests/native_multiplayer_test.py
```

Fermer les processus du moteur natif avant de remplacer ses DLL. Le script
vérifie le commit et applique `xash3d.patch` seulement si nécessaire ; il refuse
les conflits au lieu d'écraser des modifications. Il copie `gl_vf.inc` et le
contrat `game_shared/vf_engine_api.h`, puis compile client, serveur dédié,
renderer, bibliothèques auxiliaires et tests amont. La configuration MSVC est
volontairement explicite : l'adapter si la machine utilise un autre toolset.
Les atlas de textures créés pour le projet et leurs prompts sont dans Git.
Les modèles compilés, exports dérivés et ressources importées restent locaux.

## Contrat

L'extension ne change ni l'ABI historique GoldSrc ni `REF_API_VERSION`.
Le moteur relie l'export client `HUD_VFEngineInterface` à l'export renderer
`VF_GetRenderAPI`. Version et taille des structures doivent correspondre.
Le client conserve l'ancien aperçu si le renderer ne fournit pas l'extension.
Le mod `vf_engine` nécessite cependant ce renderer pour ses personnages modulaires.

- `SetAssembly` : une entité, un modèle porteur d'animations, jusqu'à 24 pièces.
  La validation et le remplacement sont atomiques. `replace_carried` supprime le modèle porté historique quand les douze pièces R-01 sont incluses. Registre de 96 assemblages ;
  `-1` désigne l'arme en première personne. Les pièces ne créent aucune entité réseau.
- `VF_PART_MERGE` : correspondance des os par nom, calculée lors de l'installation.
  Les pièces copient les matrices d'une pose parent ; elles ne recalculent pas
  chacune l'animation. Un squelette incompatible est refusé.
- `VF_PART_SOCKET` : os nommé, translation, rotation et échelle uniforme locales (0 conserve l’échelle 1). Le silencieux
  indépendant démontre ce chemin sur `M16A2`. `build_sockets.py` convertit sa
  géométrie en coordonnées locales, avec une racine identité. Le contrat généré
  est `generated/sockets/socket-contract.json`. Les futurs adaptateurs d'armes
  peuvent fournir d'autres os, offsets et pièces sans changer le moteur.
- `DrawPreview` : MDL natif, séquence et temps explicites, profondeur matérielle,
  cadrage d'après la géométrie posée. La passe est limitée au rectangle du menu
  et restaure le dessin du HUD. Aucun sprite de prévisualisation n'est nécessaire.
- `SequenceInfo` : noms, nombre et durée des séquences présentes dans le MDL.
- `GetStats` : assemblages, modèles mis en cache, poses, pièces dessinées,
  accessoires, armes portées, textures, octets estimés et durée CPU du dernier
  aperçu. Les octets viennent du suivi de textures du renderer : ce n'est pas
  une mesure de toute la VRAM ni un temps GPU. Cache de 2 048 modèles, remis à
  zéro au changement de carte ; les ressources restent gérées par Xash3D.

`pm_shared` porte la table des matériaux à 1 024 textures pour couvrir les
ressources Half-Life et Counter-Strike importées. Les collisions et hitboxes restent
communes au rig du personnage : changer une chaussure ne change pas la physique.
Le SDK rétablit explicitement les volumes debout/accroupi après `SET_MODEL`,
car cet appel remet les limites d'une entité Studio à zéro dans Xash3D.

## Réseau et données du jeu

`VFState` v4 est un message fiable de 75 octets : version, index, présence et
mode du joueur, trois empreintes de catalogue, cinq choix d’apparence, 21 indices
d’objet sur 16 bits et douze finitions. `VFBuild` utilise 64 octets.
Le serveur valide les choix avant diffusion. Une arrivée, une réapparition,
une demande de synchronisation ou un changement transmet l'état ; aucune
géométrie ni matrice d'animation n'est envoyée à chaque frame. La déconnexion
retire l'état du joueur. Le modèle porteur reste précaché ; les pièces cosmétiques
sont chargées à la demande côté client. Les deux clients doivent avoir le même
contenu installé ; aucun téléchargement automatique de ce catalogue n'est ajouté.

Le mannequin est une seule entité et présente l'apparence du joueur local.
Les véritables joueurs distants utilisent chacun leur état serveur. Les joueurs GIGN équipés du R-01 utilisent l’un des trois porteurs tiers-personne
`r01_tp*.mdl` : ils conservent les 77 séquences opérateur et ajoutent quatre
rechargements. Les douze modules remplacent le `p_9mmAR.mdl` historique ;
les mains suivent les prises de l’arme et du chargeur. Les autres armes
conservent leur modèle porté. Les rigs première personne standard et avec
poignée avant utilisent deux pièces de bras, avec les quatorze apparences
du personnage, résolues depuis les objets gants et torse.

L’inventaire joueur fonctionne à la souris, par sélection d’objets nommés
à finition fixe. Les commandes d’essai et choix groupés appartiennent à
l’atelier développeur. Les effets de combat, voix et retours d’état sont
implémentés ; le renderer annonce séparément sa capacité `status_viewmodel_version=1`
pour limiter le halo aux bras. Le lanceur vérifie cette capacité avant livraison.

Les raccords artistiques demandent toujours un contrôle visuel selon les
combinaisons. Les cadavres gardent le corps porteur complet ; le corps local
visible en première personne n’est pas encore implémenté.

Commandes de diagnostic (console avec `developer 1`) : `vf_engine_stats`,
`vf_engine_audit`, `vf_animation <séquence>`, `vf_animation_pause`,
`vf_animation_time <secondes>`. La commande de placement `cmd vf_peer_pose`
est réservée à la carte de test et nécessite `sv_cheats 1`.
`cmd vf_body_info` affiche le volume de collision et la présence du fusil.
Chaque joueur reçoit un fusil en apparaissant dans le laboratoire multijoueur.

Les tests réels produisent `build/native-engine-verification.json` et
`build/native-multiplayer-verification.json`. Le second lance un serveur lié
à `127.0.0.1:27025` et deux clients isolés ; il n'ouvre pas un serveur Internet.
Les captures sont conservées dans les dossiers `vf_engine/scrshots` des deux
runtimes. Le test exerce déplacement et tir, mais ne remplace pas un test de
latence, une partie prolongée ou l'examen artistique de toutes les combinaisons.

## Historique des ateliers (contrats de l’époque)

La version 0.6 ajoute l'atelier `vf_visual`. L’API courante est en version 3 ; les
composants utilisent les sockets existants. Les aperçus isolent l'état de
miroir de l'arme en main, utilisent une lumière neutre et affichent les deux
faces des géométries anciennes. L'état de culling est restauré après le rendu.
Les enfants d'une arme en main héritent de sa convention de culling/éclairage.
Les ombres de scène sont désactivées uniquement sur l'entité d'aperçu.

Une ligne de catalogue peut désormais référencer une famille de textures :
`id|cle_unique|nom|animations|modele_partage|skin`. Les anciennes lignes à trois
ou quatre champs restent acceptées. Les références et bornes sont validées ;
les choix de famille circulent dans les mêmes cinq identifiants réseau et ne
nécessitent aucun nouveau message. La tête garde la texture d'origine.

Commandes supplémentaires : `vf_skin_tab 0/1/2`, `vf_weapon_part zone variante`
(zones et variantes indexées depuis zéro), `vf_weapon_equip`, `vf_weapon_reset`,
`vf_weapon_audit`, `vf_visual_bench nom`. Le benchmark se termine après 180
aperçus réellement dessinés et 30 images d'échauffement ; il faut laisser le
menu ouvert. Il mesure le temps de soumission CPU et l'intervalle entre images.
L'atelier de mélange d'armes ne modifie pas les états serveur des équipements :
c'est un test cosmétique local, sans réplication des pièces d'arme à ce stade.

Version 2 (atelier 0.9) : capacité portée à 16 pièces et pose neutre des contrôleurs de colonne dans les aperçus. Les vrais contrôleurs de visée des joueurs sont conservés.

## Validation courante

`build.ps1` compile les deux DLL et les tests C++, puis exécute les tests
unitaires Python et tous les contrôles d’assets maintenus, dont les prises
avant et les rigs tiers-personne. `validate.py --suite native` vérifie ensuite
la livraison et le jeu réel ; `--suite multiplayer` vérifie deux clients
sur boucle locale. Les suites s’exécutent dans l’ordre et s’arrêtent au premier
échec. Les tests natifs utilisent les DLL de release actuelles.

`data/model_contract.json` décrit les montages, prises, porteurs et sockets
partagés par les auteurs Python, le client et le serveur. Les données sont
compilées dans `game_shared/vf_model_contract.h`. Les tables ci-dessus sont
produites par `contract_documentation.py` et contrôlées par la suite unitaire.
