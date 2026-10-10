# Vector Fields — version 0.20.7

La 0.20.7 consolide les équipements, animations, effets, voix et morts ajoutés depuis la dernière publication GitHub. Les fragments gardent les finitions indépendantes des gants et bottes ; la salle et les deux lanceurs utilisent des ressources vérifiées. [Notes de version](docs/RELEASE-0.20.7.md) · [Rapport de validation](docs/validation/maintenance-0.20.7.json).

Morts : 16 signatures elementaires et 17 arrachements sonores, superposes au cri. Sang disperse en gouttes rouges avec gravite. Essai : **F4 puis F8** ; ecoute : `Atelier - Sons de mort.cmd`. Voir [les details](docs/DEATH-SOUNDS.md).

Correction 0.20.1 : retrait complet du boîtier et du bracelet des gants, index aligné sur la prise des autres doigts, rechargement supérieur avec bascule de l’arme vers la gauche.

Les états reçus du serveur affichent désormais une signature sur les bords de
l’écran, un nom anglais avec durée restante et un halo sur les vrais gants et
manches du R1. Les réactions montrent leurs deux composantes. Essai dans
**F3 > Test joueur / voix** ; voir [les détails](docs/STATUS-FEEDBACK.md).

Les huit éléments et huit réactions ont chacun une texture HUD originale,
animée sur quatre images avec fondu entre les frames. Matières et couleurs
restent distinctes ; le centre de visée est dégagé.
Voir [la planche des decals](assets/status-feedback/decals/contact-sheet.png).

La salle **vf_range** dispose de quatre cibles GIGN avec tenue et voix aléatoires.
Six impacts du même élément en **3 secondes** activent un état visible pendant
**6 secondes**. Choisir le vecteur dans **F3 > Weapon FX / R1**, puis tirer ;
**J** les provoque. Voir [la salle et ses règles](docs/TEST-ROOM.md).

Les morts et démembrements se testent dans **F8** après **F4**. L'**Atlas** relie
les huit éléments et huit réactions à des gestuelles distinctes. Dix mouvements
Quaternius/KayKit/Mixamo sont importés sur le GIGN. Les membres projetés produisent
du sang et les particules de leur effet ; voir [l'atlas et l'inventaire](docs/DEATH-ATLAS.md).
Les cinq coupes utilisent des [textures de plaie mesurées](docs/WOUND-TEXTURES.md).

## Version actuelle et lancement

**Jouer - Vector Fields.cmd** lance la version courante dans
`runtime/vector-engine/vf_visual`. **F1/F2** ouvre l’opérateur ; **F11**, l’arme.
Choisir un emplacement, puis un objet de la liste, puis **Équiper**.
**Annuler** rétablit la configuration précédente.

Les collections servent uniquement à filtrer la liste. Il n’y a plus de boutons
d’ensemble ni de changement global de texture dans le menu de jeu. Chaque
objet possède sa finition, son nom et son identifiant ; changer de châssis
conserve les onze autres objets de l’arme. Tous les objets sont accessibles.

Le catalogue de jeu comporte **948 objets** : 854 pièces R1 (61 géométries dans
14 finitions), 70 pièces de tenue et 24 accessoires provisoires. Les cinq zones
GIGN ont quatorze collections, dont les nouvelles tenues **Rome / Inventeur**
et **Dieselpunk**. Épaules, ceinture, bouclier et spécial restent optionnels.

Les mains en première personne suivent les **gants équipés**, et les manches
la **veste équipée**. Les quatorze collections peuvent être mélangées ; le
changement prend effet en validant l’objet, sans modifier la finition de l’arme.
Le dépliage anatomique conserve les détails disponibles dans les textures
actuelles ; la plaque carrée est supprimée et les doigts arrondis sans changer le
squelette. La prise du chargeur latéral est inclinée vers l’avant, avec un
poignet assoupli.

Pour contrôler les modèles compilés et leurs UV hors du jeu :
`python vector-fields/inspect_first_person.py`, puis ouvrir
`vector-fields/build/first-person-inspector.html` (rotation, zoom, paume/dos,
maillage et choix des quatorze tenues).

**Atelier - Animations.cmd** prépare et ouvre l’atelier animé hors du jeu.
La vue initiale présente notre personnage GIGN tenant les douze pièces réelles
R-01. Trois alimentations, quatre chargeurs, finitions, maintien, tir personnalisé,
recharges MP5/fusil adaptées et poses accroupies sont disponibles. Marche,
course et déplacement accroupi superposent les animations existantes des jambes.
Les animations de déplacement de base sont conservées.

En première personne, **Appui avant** permet de vérifier la poignée inclinée,
le tube auxiliaire, le stabilisateur replié et le garde-main. Équiper une poignée
inclinée sélectionne automatiquement une prise dédiée dans le jeu, pour ses
quatorze finitions et les trois alimentations. La main quitte la poignée pour
saisir le chargeur, puis revient dessus. Le geste visuel termine maintenant en
**1,5 s**, comme la recharge gameplay existante. Le trajet du chargeur, la main
droite, les événements sonores et les neuf indices de séquences sont conservés.
La torsion de l’avant-bras supérieur est stabilisée. La troisième personne
conserve ses prises actuelles ; aucune variante de poignée avant n’y est ajoutée.

Les réglages déplacent l’arme, son appui gauche et les coudes, avec vérification
de la portée des bras. **Exporter la recette** sauvegarde un JSON ; déposer ce
fichier sur **Atelier - Animations.cmd** recompile l’essai et ouvre le résultat.
La recette de référence est `assets/animations/r01-third-person.json`.
Les anciennes vues FP et Counter-Strike restent accessibles pour comparaison.

Les trois porteurs R-01 compilés ont 31 os (les 28 existants et trois points
pour l’arme, le chargeur et la culasse), 77 séquences à leurs indices historiques
et quatre recharges ajoutées. Les recharges ont un chargeur mobile, une arme légèrement abaissée et basculée,
et des prises adaptées à chaque alimentation.
L’affichage des adversaires réutilise leur équipement et leurs finitions réseau,
avec une extension native v3 (24 pièces, échelle des sockets, suppression de
l’arme historique remplacée). Cette intégration est vérifiée dans un runtime
d’essai séparé sous `build/animation-native`. Le moteur installé dispose aussi
de cette extension v3. Recompiler le moteur et le client ensemble lors
d’un changement d’interface. Le lanceur refuse un mélange v2/v3 avant de copier des
fichiers, pour éviter un affichage de secours Half-Life inattendu.

Le serveur déclenche la recharge MP5 uniquement lorsqu’elle est acceptée,
utilise le porteur à 81 séquences, conserve le geste pendant les déplacements et
son avancement lors d’un changement debout/accroupi. La fin ou le rangement de
l’arme rend la pose de maintien. Les chargeurs pleins ne déclenchent aucun geste.
Le remplacement systématique du modèle joueur dans `CheckPowerups` est corrigé :
il rétablissait l’index Gordon à chaque image, malgré le nom du modèle équipé.
Pour les porteurs R-01, la rotation du torse suit désormais la verticale plutôt
que les axes inclinés de la colonne accroupie ; les appuis natifs sont conservés.
`tests/third_person_native_test.py` vérifie ces états sur deux clients et prend
des captures du geste reçu. `--verify` relit une session existante sans relancer
le jeu. L’intégration reste dans `build/animation-native`.
Les dimensions anatomiques des zones de dégâts sont héritées du porteur GIGN ;
leurs positions suivent maintenant le porteur serveur. Le combat et ces zones
restent à valider. Le donneur
comporte notamment une ancienne zone de bouclier (groupe 8), à adapter à notre équipement.
Le geste FP est synchronisé sur les 1,5 s de recharge gameplay.
Les contrôles de prise et le test natif ciblé sont décrits dans
[la note sur les poignées avant](docs/ANIMATIONS-FOREGRIP.md).

Les équipements sans apparence explicite utilisent désormais GIGN lorsque ce
corps est disponible, y compris les anciennes catégories qui choisissaient HEV.
Une apparence explicitement sélectionnée dans l’ancien laboratoire reste respectée.
Le moteur utilise aussi le corps GIGN complet envoyé par le serveur pendant
l’attente de l’assemblage réseau, au lieu du modèle Half-Life Gordon par défaut.

**F6/F7** ouvre l’espace développeur avec les anciens skins, préréglages,
prototypes et outils de finition. **Retour au jeu** restaure l’équipement de jeu.
Le lancement ouvre l’inventaire sans appliquer un ensemble préfabriqué.

[Notes de version et vérifications](docs/RELEASE-0.20.1.md) ·
[Historique](CHANGELOG.md) ·
[Validation et sauvegardes](docs/ARCHITECTURE.md) ·
[Hitboxes et propriétés physiques des matériaux](docs/COMBAT-MATERIALS.md)

## Châssis et modules

**Arche supérieure** est une nouvelle variante du corps central, courbe et
ajourée, alimentée par le haut et dotée d’un support d’optique déporté. Elle
complète Zénith. Le châssis définit la position du chargeur :

| Position | Châssis |
| --- | --- |
| Dessous | Atelier, Circuit, Nomade, Bastion, Arche, Gyre |
| Latérale | Traverse |
| Dessus | Zénith, Arche supérieure |

Les quatre modèles de chargeur et tous les autres modules restent
interchangeables. Les neuf châssis existent dans les quatorze finitions.
Dans **F11 → Châssis**, filtrer une collection permet de comparer leurs formes.

Les pièces Inventeur et Dieselpunk font partie du même inventaire :

| Emplacement | Inventeur | Dieselpunk |
| --- | --- | --- |
| Culasse | Manivelle et roue dentée | Arbre à cames et ressort |
| Optique | Dioptre astrolabe | Viseur périscopique |
| Batterie | Accumulateur à ressort | Réservoir à huile |
| Refroidissement | Éventails à lamelles | Radiateur à faisceau |

Chacune possède quatorze objets nommés, un par finition. Les préréglages Atelier,
Circuit, Nomade, Bastion, Inventeur et Dieselpunk sont réservés au développeur.
Les matières Rome / Inventeur emploient bois, toile dessinée, cordages et
mécanismes anciens ; Dieselpunk emploie fonte huileuse, carrosserie nervurée,
bakélite et instruments analogiques. Les mêmes atlas couvrent les 61 géométries.

## Technique et limites actuelles

Les indices d’objets réseau sont sur 16 bits (protocole 4). Les sauvegardes
reposent sur des clés stables et retrouvent les anciennes pièces avec leurs
finitions indépendantes. Les finitions liées aux objets sont validées côté serveur.

Le tir, la capacité et la durée effective de recharge restent ceux du MP5.
Les formes s’assemblent dans l’inventaire et à la première personne ; l’arme
portée en troisième personne garde encore son modèle historique. Les nouvelles
tenues utilisent la silhouette et les animations GIGN communes. Les quatre
emplacements d’accessoires opérateur utilisent toujours des modèles provisoires.

[Banques de matières et ajout d’un atlas](assets/r01/variants/README.md)

## Jouer

Double-cliquer sur `Jouer - Vector Fields.cmd`, à la racine du projet.
Le lancement par défaut est en **1920×1080, plein écran fenêtré sans bordure** (`-borderless`). Le laboratoire équipe le fusil et ouvre le menu. Cette version utilise
`runtime/vector-engine/vf_visual`, avec notre compilation de Xash3D.
Le mod `vf_engine` conserve les données du prototype 0.5.
Le raccourci archivé `legacy-launchers/Jouer - Vector Fields precedent.cmd` lance la version précédente conservée
dans `runtime/xash3d/vf_skins`.
Fermer la version en cours avant de la relancer : ses DLL sont verrouillées
pendant son exécution.

`Explorer - TFC.cmd` propose les 15 cartes installées. F5 permet aussi de
rejoindre 2fort depuis le laboratoire ; F4 revient au laboratoire. Il s'agit
pour le moment de visites avec déplacement et tir, sans les règles de match TFC.

En jeu : **ZQSD** pour se déplacer sur un clavier AZERTY, **souris** pour
regarder dans toutes les directions, **Espace** pour sauter, **Ctrl** pour
s'accroupir, **Maj** pour marcher, **R** pour recharger et **E** pour utiliser.
Fermer l'atelier avec F2 pour reprendre le contrôle du personnage.
La visée libre est réactivée à chaque lancement ; les mouvements de souris
ne font plus avancer, reculer ou glisser le joueur.
Xash3D nomme les touches par leur position QWERTY : les entrées internes
`w` et `a` dans `lab_controls.cfg` correspondent à **Z** et **Q** en AZERTY.
Les raccourcis clavier historiques restent disponibles, mais la souris pilote
maintenant toutes les vues. F1 et F2 ouvrent l’opérateur ; F6 ouvre les outils développeur.

| Action | Commande |
| --- | --- |
| Choisir une vue, un emplacement ou une pièce | Clic gauche |
| Tourner l'aperçu 3D | Glisser dans l'aperçu avec le clic gauche |
| Zoomer dans l'aperçu | Molette au-dessus du modèle |
| Parcourir la bibliothèque | Molette au-dessus des cartes ou boutons de page |
| Lire la définition d'une famille ou d'une jauge | Survoler son emblème / sa jauge |
| Parcourir les animations | Boutons Animation et Pause |
| Soumettre les choix | Appliquer (systèmes/skins) ou Équiper (style d'arme) |
| Annuler les choix techniques ou les skins non validés | Annuler |
| Fermer et retrouver la visée souris | Croix en haut à droite, F1/F2 ou Échap |

## Archives techniques du laboratoire

Les parcours et boutons de ces anciennes versions concernent les outils développeur.
Pour le menu de jeu actuel, utiliser le parcours d’inventaire décrit en tête de page.

## Relais R-01 — arme de référence 0.11

**`Jouer - Vector Fields.cmd`** ouvre le laboratoire avec le R-01 équipé, en
1920×1080 sans bordure. **F11** ouvre son atelier depuis le jeu. Les boutons
**R-01 / Atelier** et **R-01 / Circuit**, dans **Arme / Relais R-01**, chargent deux
ensembles complets. Choisir un emplacement à gauche, une variante à droite,
puis **Appliquer**. La croix ou Échap rend le contrôle au joueur.

Les quatre ensembles partagent les mêmes interfaces ; les 12 choix sont
indépendants, soit **169 869 312 assemblages possibles** avec les huit châssis. Le bouton **Isoler cette pièce
en 3D** permet d'examiner un composant avec rotation à la souris et zoom à la
molette. Une seconde pression revient à l'arme complète. F11 conserve les choix
appliqués quand on rouvre l'atelier. Les collections historiques restent
accessibles par leurs six boutons en bas à gauche.

Le gameplay lie le personnage et l'arme aux objets équipés. Dans les options
développeur, le mode **Apparence libre**
permet de conserver simultanément un skin GIGN indépendant. Ouvrir F11 ne
remplace plus le skin du personnage.
Une page **Relais R-01** a également été ajoutée au guide dans le jeu.

| Emplacement | Variante Atelier | Variante Circuit |
|---|---|---|
| Châssis | R-01 / Chassis Atelier | R-01 / Chassis Circuit |
| Canon | Canon chemise | Canon a induction |
| Bouche | Frein ajoure | Moderateur court |
| Chargeur | Chargeur nervure | Chargeur double pile |
| Culasse | Culasse a levier | Culasse a glissiere |
| Charge | Cassette balistique | Cassette energetique |
| Projectile | Porte-flechettes | Porte-ampoules |
| Optique | Viseur cadre | Lunette compacte |
| Sous-canon | Poignee inclinee | Tube auxiliaire |
| Poignée / crosse | Crosse squelette | Crosse amortie |
| Batterie | Cellule ambre 24V | Condensateur teal 48V |
| Refroidissement | Radiateur a ailettes | Circuit cuivre |

### Fabrication et animations

Les 60 pièces sont des géométries créées dans
`build_reference_weapon.py`, `build_reference_extensions.py` et `build_reference_chassis.py`, avec des plans de raccord communs. Les détails
comprennent des bouches creuses, colliers, ailettes, conduites, bornes, rails,
verrous, vis, protections et des panneaux portant des marquages techniques.
Le viseur cadre utilise une ouverture rectangulaire chanfreinée et **la texture
de lentille générée**, appliquée au verre, sans croix jaune superposée. Les UV
cadrent la zone de verre de cette image ; le matériau additif garde ses reflets
bleus en laissant voir la scène. Le contour métallique est construit en 3D.
La planche de textures industrielle a été créée avec l'outil **imagegen intégré**,
puis découpée en 16 matériaux de 256×256 pixels, avec une palette de 256 couleurs
compatible MDL GoldSrc. Les UV appliquent ces matériaux aux maillages réels.

L'original est conservé dans `assets/r01/texture-atlas.png`, le prompt exact dans
`assets/r01/texture-prompt.txt` et la provenance dans `assets/r01/provenance.json`.
Les sources SMD/QC, textures BMP et MDL compilés sont dans `generated/r01`.
Le manifeste contient les identifiants, empreintes et nombres de triangles.

Les mains et les neuf séquences de base viennent du MP40 déjà présent dans le
projet. Le montage inférieur conserve ces animations ; les deux nouveaux
montages remplacent les pistes du chargeur et du bras gauche.
Le chargeur est monté sur son os de rechargement dédié. Une piste de translation
supplémentaire anime la nouvelle culasse au tir et en fin de rechargement.
Les deux chargeurs partagent leur point d'insertion et leur prise de main.

**Limites actuelles :** les dégâts, la cadence, les munitions et les règles de
rechargement restent ceux du MP5. Les coûts TED/IP/HS/OI sont provisoires (48/100
pour chaque jauge avec les 12 pièces) ; les descriptions des pièces concernent
leur fabrication visuelle. Les gants de l'opérateur ne remplacent pas encore les
mains en première personne. Les vues externes de l'arme restent les modèles
historiques. La batterie et les pièces internes exposées sont une direction
artistique de prototype, à affiner avec les futures mécaniques.

### Reconstruction et validation

```powershell
python vector-fields/build_reference_weapon.py
powershell -ExecutionPolicy Bypass -File vector-fields/build.ps1
python vector-fields/play.py --visual-lab --deploy-only
python vector-fields/tests/reference_engine_test.py
python vector-fields/tests/reference_lens_test.py
python vector-fields/tests/reference_platform_test.py
python vector-fields/tests/reference_extensions_test.py --mode native
python vector-fields/tests/reference_chassis_test.py --mode all
python vector-fields/tests/reference_themes_test.py --mode all
```

Le test natif vérifie 1 700 assemblages couvrant chaque pièce et chaque paire
d’emplacements, ainsi que les 60 maillages. Il contrôle les choix à la souris,
le guide, les ensembles en main, les rechargements et la sauvegarde/reprise.
`reference_extensions_test.py --mode native` ajoute les 24 aperçus Nomade/Bastion
et les deux nouveaux chargeurs sur les trois montages. Leurs captures et
rapports sont produits dans `runtime/vector-engine/vf_visual/scrshots/` et
`vector-fields/build/`. Cette couverture par paires ne constitue pas une
inspection de toutes les configurations complètes. Les mesures de
prévisualisation portent sur les temps CPU.

`reference_platform_test.py` contrôle en plus les poses des mains relues depuis
les SMD, les longueurs de bras, l'orientation de la paume et la prise centrée,
les deux chargeurs dans les trois montages, les sélecteurs à la souris,
le rechargement en première personne, les finitions et la sauvegarde/reprise.
Son rapport est `build/reference-platform-verification.json`.
La génération des pistes utilise Python, NumPy, SciPy et Pillow.

## Outils développeur — Arsenal et contenus 0.10

Les sections historiques suivantes décrivent les outils désormais accessibles
depuis **Options développeur**. Les anciens raccourcis F2 vers les skins et F7
vers l’arsenal sont remplacés par les onglets de cet espace ; F2 revient à
l’opérateur de gameplay et F6/F7 ouvrent les options dev.

**Options développeur → Arsenal** ouvre la bibliothèque intégrée au jeu. Choisir une collection,
utiliser la recherche par nom, puis sélectionner un modèle. La souris fait
pivoter et zoomer l’aperçu ; Animation et Pause permettent d’inspecter les mouvements.

- **En main** : choisir **Essayer / mode libre**, puis fermer avec F2. Le modèle
  remplace visuellement le MP5 et utilise des séquences adaptées de repos, sortie,
  tir et rechargement. Le bouton active explicitement le mode Apparence libre.
- **Pièces** : choisir **Monter / mode libre**. L’atelier Arme / style montre
  immédiatement l’assemblage. Revenir dans Arsenal pour ajouter une autre pièce.
  Un choix remplace la pièce du même emplacement ; **Retirer la pièce** l’enlève.
- **Tout** : inclut les vues externes, projectiles, objets et personnages à
  inspecter. Ces références ne sont pas toutes équipables en première personne.
- **Cartes CS** : **Visiter la carte** lance une copie adaptée à l’exploration.
  F4 revient au laboratoire. `Explorer - Counter-Strike.cmd` propose aussi les 25 cartes.
- **Skins / sources → CS** : 22 nouvelles apparences Counter-Strike, originales et HD,
  segmentées en tête, torse, gants, jambes et chaussures. Le catalogue total
  contient 176 apparences, avec les identifiants existants conservés.

### Contenu installé

| Collection | Entrées dans Arsenal |
|---|---:|
| GameBanana, modèles et variantes | 551 |
| Seconde Guerre mondiale : MP40, Thompson, PPSh-41, M1 Garand et variantes | 22 |
| Counter-Strike 1.6 | 165 |
| Counter-Strike HD, modèles supplémentaires après dédoublonnage | 11 |
| TFC | 63 |
| M4 RIS converti depuis Source | 1 |
| Accessoires isolés et montables | 12 |
| Cartes Counter-Strike | 25 |
| **Total** | **850** |

Cela représente **825 modèles consultables**, dont **309 variantes proposées en
main**, et 25 cartes. Ce ne sont pas 850 armes différentes : les vues au sol,
les personnages, les variantes de mains et les accessoires sont comptés séparément.
Les packs « CS 1.6 Weapons / CS:GO Animations » et « Default Weapons on MW
Animations Mini Pack » rejoignent la collection GameBanana.

L’import copie 1 128 ressources de l’installation Counter-Strike locale : modèles,
sons, sprites, textures WAD, cartes, décors et fichiers de référence. Les originaux
Steam restent intacts. Les ressources TFC nécessaires sont conservées dans la même
bibliothèque montée ; les dictionnaires de décalcomanies sont réunis sans réencodage
de leurs textures. Les menus et binaires propres à CS ne sont pas chargés.

**Limite de cette étape :** les cartes sont visitables sans règles de match CS
(achat, bombe, sauvetage, équipes). La pluie spécifique de CS sur Aztec
reste à porter ; ses décors et textures sont présents. Les nouvelles armes gardent les dégâts,
munitions et règles du MP5 ; les grenades et armes blanches sans séquences
compatibles restent des références 3D. Les modèles d’arme au sol et à la troisième
personne ne changent pas encore avec l’essai local. Les animations peuvent avoir
un timing inhabituel, notamment pour les fusils à pompe et armes à verrou.

### Les douze accessoires

Six optiques (ACOG, Aimpoint, trois variantes holographiques et un holographique
compact), deux silencieux, deux crosses, une poignée verticale et un chargeur.
Leurs maillages et textures proviennent des pièces isolées du catalogue. Les axes,
échelles et supports sont adaptés au prototype MP40 / Thompson / Nailgun.

Cinq emplacements peuvent être utilisés simultanément : optique, bouche, crosse,
poignée et chargeur. Le chargeur suit son os de rechargement ; l’ancien chargeur
est masqué. Les optiques, silencieux et chargeurs des équipements liés utilisent
également ces nouvelles pièces, avec les six indices de famille conservés.
Il ne s’agit pas encore d’un montage universel sur les 309 armes complètes.
Les prises de main et certains raccords restent à retoucher.

### Conversion Source validée sur un premier modèle

Le M4 RIS de [GameBanana 210349](https://gamebanana.com/mods/210349) est passé du
MDL Source v44 au MDL GoldSrc v10 avec Crowbar, conversion des textures VTF et
recompilation : **13 332 triangles, 45 os, 14 animations originales**, auxquelles
s’ajoute la table de correspondance du MP5. Le changement d’axes a été corrigé
et le modèle a été contrôlé dans l’aperçu, en main et pendant le rechargement.

Ce parcours conserve la géométrie, le squelette et les animations échantillonnées.
Il réduit les textures à 512 pixels maximum et 256 couleurs. Les normal maps,
reflets, matériaux et événements spécifiques à Source ne sont pas conservés.
La texture des mains absente du pack a été prise dans le pack Old School CSS
archivé, avec sa provenance enregistrée. Les autres modèles Source restent des
sources de travail : leur conversion demande le même contrôle individuel.

Les crédits, archives et empreintes restent dans `weapon-lab/catalog`,
`weapon-lab/generated/source-goldsrc/conversion.json` et
`generated/library/manifest.json`. Cette intégration est une étude locale ; elle
ne constitue pas un paquet autonome autorisé à la redistribution.

### Reconstruction et vérifications

```powershell
python vector-fields/tests/bsp_import_test.py
python vector-fields/build_cs_skins.py
python weapon-lab/convert_source.py
python vector-fields/build_library.py
python vector-fields/build_library_accessories.py
./vector-fields/build-engine.ps1
./vector-fields/build.ps1
python vector-fields/play.py --visual-lab --deploy-only
python vector-fields/tests/library_engine_test.py --mode audit
python vector-fields/tests/library_engine_test.py --mode visuals
python vector-fields/tests/library_engine_test.py --mode parts
python vector-fields/tests/library_engine_test.py --mode maps
```

Les sources téléchargées, l’installation Steam et la décompilation Crowbar sous
`weapon-lab/generated/source-test` sont nécessaires à la reconstruction complète.
L’import des cartes CS doit avoir eu lieu une première fois avant la génération
complète de la bibliothèque. Après une reconstruction du catalogue des personnages
de base, relancer `build_cs_skins.py` pour réinsérer les entrées CS aux mêmes indices.

Les modèles se chargent à la sélection ; le cache du renderer accepte désormais
2 048 références. L’audit est réalisé par lots dans des processus neufs : il
vérifie le chargement des 825 modèles, pas leur présence simultanée en mémoire.
Les rapports `build/library-*-verification.json` et `build/cs-maps-verification.json`
décrivent la couverture réelle. Tous les nouveaux essais utilisent **1920×1080
sans bordure**. Le parcours représentatif couvre le M4 CS, le PPSh, le Garand,
le M4 Source, les accessoires et les skins CS ; il ne certifie pas chaque animation
de chaque variante.

Validation finale : 825 modèles chargés sans échec dans l’audit, 25 cartes CS
ouvertes et capturées, 12 accessoires montés, parcours souris de l’arsenal validé,
et régression de l’atelier existant réussie (32 captures). Les cartes CS ne
produisent plus d’erreur de chargement ; un avis facultatif du menu sur
`colors.lst` subsiste. Les visites TFC de 2fort et Warpath restent fonctionnelles,
avec les règles TFC toujours absentes.

Sur 180 images par aperçu, le M4 Source a demandé environ **0,93 ms CPU**
(P95 1,01 ms), et l’assemblage à cinq accessoires **0,84 ms** (P95 0,97 ms),
sans chargement supplémentaire pendant la mesure, à une cadence proche de 60 Hz.
Ces mesures concernent l’aperçu sur cette machine, pas une garantie de performance
pour une partie multijoueur complète.

## Intégration des équipements 0.9

Dans les options développeur, le menu déroulant **Apparence**, en haut de l’atelier, choisit entre deux modes :

- **Liée à l’équipement** (mode initial) : les objets déterminent le personnage et l’arme. Choisir un objet affiche immédiatement une proposition en 3D ; **Appliquer** la valide auprès du serveur. Les onglets Apparence et Arme/style restent consultables en lecture seule.
- **Apparence libre** : les cinq zones corporelles et les quatre modules d’arme restent réglables dans leurs ateliers. Ces choix sont conservés lorsque l’on revient au mode lié, et réapparaissent au retour en mode libre. Changer de mode ne modifie ni les objets ni leurs budgets. Le mode et les skins corporels libres sont conservés dans les sauvegardes de partie ; les pièces libres d’arme utilisent les variables archivées existantes.

Les boutons de collection chargent une proposition complète pour l’onglet courant : opérateur ou arme. Les six familles existent dans chacun des 21 emplacements. La liste contient **128 objets de test**, pas 128 armes originales. Les descriptions des capacités restent des intentions ; les nouvelles pièces n’activent aucun pouvoir.

| Famille | Direction visuelle de l’opérateur | Arme de test |
|---|---|---|
| Baseline | Bastion sable, petites pièces grises | Assemblage MP40, accessoires sobres |
| Predator | Éclaireur sable, accents ocre | Pièces Thompson, viseur et capteurs |
| Fortress | Bastion ardoise, plaques larges bleues | Pièces Nailgun/Thompson, protections épaisses |
| Rogue | Éclaireur ardoise, petits accessoires verts | Assemblage allégé MP40/Thompson |
| Engine | HEV cuivre, modules violets | Assemblage hybride et cartouches apparentes |
| Anomalous | HEV ardoise, modules roses | Pièces Thompson/Nailgun et boîtiers nervurés |

**Opérateur :** tête, torse, gants, jambes et chaussures choisissent chacun une apparence du catalogue. Épaules, ceinture, bouclier et spécial ajoutent des accessoires attachés au squelette. Retirer un de ces accessoires le fait disparaître ; une zone corporelle vide retrouve une sous-tenue Éclaireur. Les raccords restent ceux du système de segmentation existant.

**Arme :** châssis, canon, poignée/crosse et sous-canon déterminent les quatre pièces déjà découpées dans les modèles MP40, Thompson et Nailgun. Les huit autres emplacements ajoutent embout, habillage de chargeur, culasse, cartouche, ogive, optique, batterie et refroidisseur. Le chargeur suit son os animé `Bone71`. Les accessoires proviennent de `build_equipment_visuals.py` : **12 modèles procéduraux, chacun avec 6 variantes de famille**, soit 72 variantes. Ils sont volontairement simples ; certains emplacements internes sont rendus visibles comme boîtiers de démonstration.

Le personnage et le mannequin utilisent le choix confirmé par le serveur. Ce choix et le mode sont transmis aux autres clients. Les assemblages de l’arme restent une démonstration **en première personne** ; l’arme portée en troisième personne conserve son modèle antérieur. Le tir, les dégâts et la balistique restent ceux du MP5. Les prises de main et intersections de certains mélanges nécessitent encore du travail artistique. Depuis la 0.20, les mains R-01 conservent le squelette MP40 avec un maillage ajusté ; elles reprennent les gants équipés, et les manches reprennent la veste.

### Corrections visuelles

- **Toxic** : spores violettes fines, sans nuage vert. **ContamBloom** conserve le nuage vert dense, les projections acides et quelques spores violettes.
- **Torsion du torse** : les contrôleurs de colonne vertébrale des aperçus et des mannequins d’effets sont initialisés en position neutre. Un octet nul représentait −30° sur chacune des quatre articulations. Les contrôleurs des vrais joueurs restent pilotés par le mouvement et la visée.
- L’API optionnelle du renderer passe en **version 2**, avec **16 pièces** par assemblage (13 utilisées pour une arme complète, 9 pour un opérateur). Client et renderer doivent être reconstruits ensemble. L’ABI GoldSrc et la physique de déplacement ne changent pas.

### Reproduire et vérifier

```powershell
python vector-fields/build_equipment_visuals.py
./vector-fields/build-engine.ps1
./vector-fields/build.ps1
python vector-fields/play.py --visual-lab --deploy-only
python vector-fields/tests/equipment_engine_test.py
python vector-fields/tests/ui_engine_test.py
python vector-fields/tests/native_multiplayer_test.py --visual-lab
```

`vf_equipment_audit` soumet les 128 objets au renderer réel. Les rapports d’assemblage, captures et mesures sont sous `vector-fields/build/equipment-*`. Les événements de souris des tests sont injectés dans le routage natif de l’interface ; ils ne simulent pas une souris au niveau Windows. Les mesures d’aperçu sont des temps CPU, pas des mesures GPU isolées.

Validation locale : 944 contrôles de catalogue/équipement, 10 601 contrôles d’effets et 18/18 tests amont du moteur. Les premiers scénarios 1280×720 et 1024×768 ont produit chacun 32 captures (vérifications historiques ; les prochains essais utilisent uniquement 1920×1080 sans bordure) ; la régression d’interface en produit 19. Les deux aperçus Fortress mesurés sur 180 images demandent environ 1,00 ms (opérateur) et 1,27 ms (arme) de CPU à 1280×720, pour une cadence observée proche de 60 images/s. Aucun chargement supplémentaire de modèle pendant ces deux mesures.

Les sections suivantes conservent la documentation des étapes précédentes. Les réglages d’apparence décrits comme indépendants de l’équipement y correspondent désormais au mode **Apparence libre**.

## Effets visuels 0.8

**F3** ouvre directement **Guide → Effets**. Le guide contient les fiches,
les pictogrammes, les recettes et une **matrice 8 × 8 cliquable**.
**Page précédente / Page suivante** changent l’effet dans la salle ; **F9**
retire tous les effets locaux. F4 conserve le retour au laboratoire et F6
conserve la recharge des munitions.

### Vocabulaire

- **Vecteur primaire (VP)** : composante élémentaire, par exemple Hydro.
- **État** : empreinte sur la cible, par exemple Soaked pour Hydro.
- **Réaction couplée (RC)** : résultat nommé de deux vecteurs compatibles,
  par exemple Hydro + Electro → ArcChain.
- **État tactique (ET)** : Phase, Null, Ward, Ping ou Overclock ; ces cinq
  démonstrations sont séparées de la matrice élémentaire.

Les **8 VP** sont Hydro, Electro, Cryo, Thermal, Toxic, Corrosion, Sonic et
Kinetic. Chacun possède **exactement deux partenaires distincts**, l’un OU
l’autre, jamais une recette à trois composants. Les paires sont symétriques :
A+B et B+A produisent la même RC. Cela donne **8 RC distinctes** (8×2/2),
et non les 28 paires possibles sans restriction. Les cases vides n’ont pas
de réaction définie. Les réactions ne sont pas elles-mêmes combinées.

| Vecteurs | Réaction couplée | Intention future | Lecture visuelle actuelle |
| --- | --- | --- | --- |
| Hydro + Electro | **ArcChain** / Conduction | Propagation électrique sur cible imbibée | Arcs jaunes vers des relais et gouttes bleues |
| Electro + Cryo | **CryoCircuit** / Supraconduction | Conduction dans un état froid | Réseau blanc entre cristaux bleus |
| Cryo + Kinetic | **FracturePulse** / Fragmentation | Fracturer une enveloppe froide à l’impact | Éclats de glace et traits radiaux |
| Kinetic + Sonic | **ResonantShock** / Onde d’impact | Convertir l’impulsion en onde | Ondes roses et éclats métalliques |
| Sonic + Corrosion | **AcidEcho** / Cavitation | Disperser un milieu corrosif par vibration | Bulles vertes, ondes roses, filets acides |
| Corrosion + Toxic | **ContamBloom** / Contamination | Associer corrosion et contamination | Nuage vert pourpre, gouttes jaunes, spores |
| Toxic + Thermal | **CinderMist** / Ignition toxique | Enflammer un milieu contaminé | Flammes orange au sein d’un nuage vert |
| Thermal + Hydro | **SteamVeil** / Vaporisation | Former un écran de vapeur | Panaches blancs et gouttelettes |

**Provenance** : Hydro/Electro/Cryo/Thermal, ArcChain et SteamVeil figurent
explicitement dans l’extrait accessible de « Brainstorming Techwear Équipement ».
Toxic, Sonic, Kinetic, corrosion, phase et neutralisation sont mentionnés dans
le catalogue d’équipement local. Les six autres recettes, leurs noms et leur
interprétation sont des **propositions**, signalées dans le guide. L’historique
complet et les anciens visuels générés n’ont pas pu être récupérés. Ce catalogue
n’est donc pas présenté comme une restitution exhaustive des anciens échanges.

L’inspiration Warframe concerne la distinction entre élément, statut et
combinaison, ainsi que la lisibilité des cristaux et des nuages, documentées
par Digital Extremes dans [Update 36: Jade Shadows](https://www.warframe.com/en/patch-notes/pc/36-0-0).
Notre graphe à deux partenaires et nos noms sont propres à Vector Fields.
Aucun asset, coefficient ou système de dégâts de Warframe n’est importé.

### Manipuler les effets

Dans chaque fiche, **Voir cet effet dans la salle** place un mannequin GIGN
local devant le joueur, sur un sol libre. **Comparer A / B / résultat** place
les deux VP de part et d’autre de leur RC. L’espace doit être libre ; un
placement obstrué est refusé. **Appliquer à la cible** attache le visuel au
personnage ou mannequin visé avant l’ouverture de F3. Les halos sont dessinés
sur une copie locale : l’entité serveur n’est pas modifiée.

L’aperçu du guide montre le modèle 3D et les mêmes trajectoires de particules
projetées dans le cadre. Le halo natif est évalué **dans la salle** (bouton
« Halo salle »). Il ne constitue pas un matériau complet ni une texture peinte
sur le modèle. Rotation, zoom, pause et désactivation des particules permettent
d’inspecter les couches. Le halo et les particules peuvent être coupés séparément.

Les aperçus de ce guide restent locaux au client. Les états des vrais joueurs
et des quatre cibles GIGN sont maintenant gérés par le serveur. Les balles
peuvent déclencher les huit états primaires après six impacts en trois secondes ;
voir [la salle de test](docs/TEST-ROOM.md). Les dégâts et coefficients de protection
restent ceux du jeu actuel ; les effets ne calibrent pas encore de ralentissement,
dégât périodique ou invincibilité.

### Rendu et ressources

`data/effects.json` est la source du catalogue ; `build_effects.py` vérifie
le graphe et produit `cl_dll/vf_effect_catalog.h`. Le rendu lit ces recettes.
Les trajectoires sont dans `cl_dll/vf_effect_math.h` et les intégrations dans
`cl_dll/vf_effects.cpp` (HUD, TriangleAPI, entités locales, `kRenderFxGlowShell`).
Le cÅ“ur Xash3D n’a pas besoin d’une nouvelle modification pour ces effets.

Cinq sprites installés de Half-Life sont réutilisés : `bubble.spr`,
`hotglow.spr`, `steam1.spr`, `fire.spr`, `white.spr`. Ils sont copiés dans
`generated/effects`, puis `sprites/vf_effects`. Leur provenance, leurs dimensions,
leurs animations et leur SHA-256 figurent dans `build/effects-catalog-verification.json`.
Les cristaux, arcs, ondes et trajectoires sont des formes calculées par notre code.

Les démonstrations sont bornées à **3 émetteurs**, **3 couches par effet** et
**512 primitives par couche**. Elles n’accumulent pas d’entités serveur ou de
particules persistantes. F9, le changement de carte et la réinitialisation du
HUD vident les émetteurs ; un changement de mode vidéo invalide aussi les sprites.
Les fonctions de dégâts, les jauges SIG/BIO/TED/IP/HS/OI et le déplacement
ne sont pas appelés par ce sous-système.

### Vérifications

`build.ps1` compile le client et le serveur, conserve les 160 contrôles
d’équipement et ajoute les contrôles C++ du graphe, des trajectoires finies
et du respect des capacités (`tests/effects_test.cpp`).

`python vector-fields/tests/effects_engine_test.py` exécute le vrai moteur,
capture chaque effet dans le guide et dans la salle, vérifie la matrice,
les liens VP/RC, les trois mannequins, les couches indépendantes, le retrait,
l’attachement à un modèle existant, le changement de carte et l’animation
entre deux captures. La variante `--width 1024 --height 768` vérifie également
la présentation 4:3. Les rapports sont dans `build/effects-engine-verification-*.json`.
Les clics sont injectés dans le routeur natif de l’interface ; la souris
physique Windows n’est pas couverte par cette automatisation.

Les mesures sur 180 images couvrent la génération et la soumission CPU des
particules de trois émetteurs. Elles ne mesurent pas isolément le coût GPU,
ni un match réseau avec de nombreux joueurs. Les tests d’interface 0.7 restent
exécutables via `tests/ui_engine_test.py`.

## Interface 0.7

Cinq vues partagent les mêmes boutons, cartes, couleurs, pictogrammes et
pointeur : **Opérateur**, **Arme / Relais R-01**, **Apparence**, **Arme / style**,
**Arsenal**. Le bouton **Guide** présente les six familles retrouvées dans le
catalogue, avec leur emblème et leur intention résumée :

| Famille | Repère | Intention présentée |
| --- | --- | --- |
| Baseline | Curseurs, gris bleu | Fondations, régularité, utilité |
| Predator | Cible, ambre | Détection, acquisition, information |
| Fortress | Bouclier, bleu | Protection, amortissement, résistance |
| Rogue | Éclair fléché, turquoise | Mobilité, discrétion, rythme |
| Engine | Noyau, violet | Synergies, amorçage, états élémentaires |
| Anomalous | Losange fracturé, rose | Ruptures, phase, neutralisation |

Ces **familles de comportement** sont distinctes des **sous-types d'emplacement**
(casque, gants, torse, canon, alimentation, optique…) et des **univers visuels**
(Operator Overkill, Trenchworks, Bioforge, Neon Circuit, Xeno Relic,
Clean Sci-Foundry, Retro-Synth, Arsenal 1944). Le catalogue actuel contient ces
axes séparés ; il ne définit pas une arborescence supplémentaire de sous-familles.

Les six jauges ont aussi leur propre logo, leur couleur et leur définition au
survol : **SIG** radar cyan, **BIO** double hélice verte, **TED** réservoir thermique
orange, **IP** masse et vecteur bleus, **HS** onde violette, **OI** mécanisme validé
vert turquoise. Ces logos apparaissent dans les jauges et dans le guide, regroupés
par opérateur ou arme. **Guide → Jauges** donne à chaque code sa fiche : nom
complet, signification, somme des coûts actuelle, effets futurs non implémentés
et exemple de lecture 63/100 avec comparaison à la configuration appliquée.
Les six fichiers SVG transparents sont dans `assets/ui/budgets` ;
`export_ui_icons.py` les extrait des mêmes tracés que le jeu.

Les cartes des systèmes se filtrent par famille et affichent le niveau T1/T2/T3.
Les jauges montrent la capacité demandée et l'écart avec la configuration
appliquée ; le repère blanc conserve sa valeur de référence. Un dépassement
empêche l'application. Les prototypes **Sobre**, **Mobile** et **Expe.** changent
la proposition du système sélectionné et restent soumis à la validation.

Les skins disposent de filtres par jeu, de pages de six cartes, d'une commande
pour les cinq zones et d'un mode isolé. L'arme visuelle propose les préréglages
**MP40**, **Thompson** et **Hybride**, puis le choix indépendant des quatre pièces.
L'arsenal se parcourt par pages de huit modèles. Les assemblages restent des
apparences locales, sans nouvelles règles de tir. Les capacités spéciales
sont présentées comme **effets prévus**, pas comme des mécaniques actives.

L'interface est rendue directement par le client du jeu (`cl_dll/vf_ui.*`).
Les propositions non appliquées sont conservées lors de la navigation par onglets entre
les vues techniques et cosmétiques. Une fermeture puis réouverture recharge
la configuration du serveur. La souris alimente un pointeur propre à l'atelier ; sa trajectoire ne modifie
ni la visée ni les commandes de déplacement tant que le menu est ouvert.
Les textes utilisent un atlas de caractères, chargé comme un seul sprite,
et les emblèmes sont dessinés dans le code. L'échelle reste uniforme en 4:3
et en 16:9. `build_ui.py` peut régénérer l'atlas à partir de la police Segoe UI
installée localement sous Windows, avec Pillow. Aucun fichier TTF n'est copié.

Vérification : `python vector-fields/tests/ui_engine_test.py`, également avec
`--width 1024 --height 768`. Le test active les contrôles par leurs rectangles
avec des événements de pointeur, vérifie les confirmations serveur, le refus
d'une surcharge, les pages, les changements de zones et la fermeture.
Les captures sont dans `runtime/vector-engine/vf_visual/scrshots/ui_*`.
La commande de test `vf_ui_pointer` est inactive sans `developer 1`.
Ce test ne couvre pas l'injection physique du périphérique Windows.
Le contrôle du 8 octobre comprend 19 captures en 1280×720 et 19 en 1024×768,
ainsi qu'une réouverture après changement de carte. Les trois mesures d'aperçu
avec l'interface affichée restent autour de 16,67 ms par image (60 images/s),
après échauffement ; leur soumission 3D CPU est comprise entre 0,77 et 0,99 ms.
Ce dernier chiffre n'inclut pas tout le coût CPU de l'UI. Détails dans
`build/ui-performance.json` et `build/ui-verification-*.json`.

## Nouveautés 0.6 et choix de production

Les **145 apparences d'origine** ont chacune un nom lisible et un identifiant
stable. Les raccords universels du cou et de la taille utilisent maintenant
une transition plus large et progressive, avec des sections intermédiaires.
Une erreur d'ordre des sommets dans l'import MDL inversait les faces lors de
la recompilation ; elle est corrigée et couverte par un test de régression.
Les proportions de certains PNJ et créatures restent imparfaites sur le rig Soldier.

La piste conseillée pour produire les skins est celle des **silhouettes de
référence avec textures interchangeables**. Elle est testable avec trois bases :
Bastion (Soldier TFC), Éclaireur (Scout TFC), Opérateur HEV (Gordon multijoueur HL).
Chaque base dispose des finitions Ardoise, Cuivre et Sable : **9 variantes,
154 choix au total**. Les trois modèles partagent chacun leur géométrie entre
leurs textures ; ils conservent leur contour naturel, sans étranglement vers
les raccords universels. Les cinq zones restent indépendantes, donc gants et
chaussures peuvent prendre des finitions différentes. Le visage conserve sa
texture originale. Mélanger des couleurs d'une même silhouette est plus propre
que mélanger des proportions entre silhouettes ; les deux restent possibles.

**F2 → Tab deux fois** ouvre les armes modulaires. Quatre emplacements visuels
(corps, canon, crosse, avant), trois choix chacun, soit **81 combinaisons**.
Ils proviennent du [MP40 adapté à HL](https://gamebanana.com/mods/179714), du
[Thompson M1921](https://gamebanana.com/mods/351127) et du nailgun TFC installé.
Onze pièces ont été découpées dans les modèles ; une crosse tubulaire et trois
colliers de raccord ont été créés. Les coupes sont refermées, les UV conservés,
et les pièces attachées à l'animation par un socket commun. Le contrôle des
81 assemblages vérifie les modèles et les sockets ; le contrôle visuel porte
sur les configurations représentatives capturées, pas sur 81 prises en main finies.

L'atelier affiche aussi l'envers des surfaces pour examiner les anciens
modèles de première personne. Les mains et le chargeur utilisent les neuf
animations MP40. **Les poses des mains, le chargeur et le rechargement ne sont
pas encore réadaptés à chaque hybride.** Les silhouettes assemblées peuvent
donc présenter des contacts approximatifs. Le tir reste celui du MP5 et cette
apparence d'arme est locale, enregistrée dans les cvars du client ; les armes
en troisième personne restent celles du jeu. Les skins corporels, eux, sont
validés et répliqués par le serveur, y compris les familles de textures.

## Réservoirs de modèles et travail artistique restant

L'inventaire local conserve les **65 modèles d'armes et équipements TFC**,
les dix packs de fusils déjà étudiés et les deux nouveaux packs historiques.
65 modèles ne signifie pas 65 armes distinctes : il y a des vues en main,
des modèles externes, des projectiles et des équipements.

| Source examinée | Intérêt | État pour ce prototype |
| --- | --- | --- |
| GameBanana Half-Life : MP40 et Thompson ci-dessus | Modèles historiques déjà au format GoldSrc | Téléchargés, empreintes vérifiées, utilisés localement |
| [Armes Day of Defeat: Source](https://www.dayofdefeat.com/Manual/Classes.htm) | Garand, Kar98, Thompson, MP40, BAR, MP44, Springfield, MG42, etc. | Réservoir identifié ; contenu Source à convertir |
| [Kar98 : Original Remake Animations](https://gamebanana.com/mods/408281) | Exemple concret de modèle/animations pour DoD:S | Repéré, non intégré |
| [TacRP InterOps](https://github.com/TacRP-EX-Creators-Club/tacrp_interops) | Inventaire de modèles Source et crédits des auteurs | Repérage, pas un import automatique |

Cette recherche couvre des catalogues publics pertinents ; ce n'est pas un
recensement de tous les serveurs Source. Les MDL Source ne se copient pas
directement dans notre jeu : le [SDK Source](https://github.com/ValveSoftware/source-sdk-2013/blob/master/src/public/studio.h)
utilise un autre format que le MDL GoldSrc v10 lu ici. Il faut convertir la
géométrie, les matériaux, le squelette et les animations, puis recompiler.
Les packs GoldSrc offrent le chemin le plus court pour conserver ce rendu.

Pour le lot actuel, aucune arme complète n'a dû être modélisée à partir de
zéro. Le travail manuel porte sur **une crosse et trois raccords**, puis sur
l'ajustement artistique des prises, des chargeurs et des transitions. Un
nombre fiable d'équipements futurs à créer nécessite d'abord leur liste.
Les accessoires propres aux synergies de Vector Fields demanderont davantage
de création que les canons, crosses et corps classiques déjà disponibles.
Les crédits et conditions des auteurs sont conservés avec les métadonnées ;
les téléchargements et dérivés restent locaux, sans présumer une permission
de redistribution.

## Reproduire et vérifier la version 0.6

```powershell
python vector-fields/build_skins.py --output vector-fields/generated/visual_skins
python vector-fields/build_visual_catalog.py
python vector-fields/build_weapon_visuals.py
./vector-fields/build.ps1
./vector-fields/build-engine.ps1
python vector-fields/tests/visual_geometry_test.py
python vector-fields/play.py --visual-lab --deploy-only
python vector-fields/tests/visual_engine_test.py
python vector-fields/tests/native_multiplayer_test.py --visual-lab
```

Les deux archives historiques doivent être présentes dans `weapon-lab/extracted`
et le MP40 décompilé dans `generated/mp40` (les chemins exacts sont dans le
constructeur). Les résultats sont dans `build/visual-geometry-verification.json`,
`build/visual-engine-verification.json` et `build/visual-multiplayer-verification.json`.
Le benchmark mesure 180 rendus après 30 images d'échauffement : temps de
soumission côté CPU, intervalle réel entre images, chargements et volume estimé
des textures. Il ne mesure ni le temps GPU isolé ni une partie Internet chargée.
Les modules représentent 694 à 5 650 triangles selon l'assemblage, hors mains
et chargeur. Les silhouettes partagées évitent de charger un nouveau modèle
à chaque changement de couleur.

## Jauges indépendantes

Conformément au choix de Mathieu, le personnage utilise provisoirement
**SIG et BIO uniquement**. L'arme utilise **TED, IP, HS et OI uniquement**.
La séparation est vérifiée dès la lecture du catalogue, puis côté serveur.
Une arme ne peut pas consommer de capacité SIG/BIO, ni une armure de capacité
TED/IP/HS/OI. Le menu n'affiche que les jauges du système sélectionné.

| Système | Code | Concept |
| --- | --- | --- |
| Arme | TED | Thermo-Entropy Dissipation : dissipation thermique |
| Arme | IP | Inertial Profile : profil inertiel |
| Arme | HS | Harmonic Stabilization : stabilisation |
| Arme | OI | Operational Integrity : intégrité opérationnelle |
| Personnage | SIG | Signal Footprint : empreinte détectable |
| Personnage | BIO | Metabolic Load : charge métabolique |

Les concepts proviennent de la conversation **Brainstorming Techwear Équipement**
(`6962c094-6bc8-832f-81da-19aa4e775bd0`). Les coûts et seuils sont des valeurs
provisoires de prototype. Ces jauges mesurent des capacités requises ; elles
ne simulent pas encore chaleur, recul, fiabilité ou métabolisme en combat.

Le catalogue contient 45 pièces, 9 emplacements personnage et 12 emplacements
arme. Les anciennes propositions et descriptions sont conservées, avec trois
pièces Scout supplémentaires. Les effets spéciaux restent en préparation.

## Modularité réelle

- **Personnage :** cinq zones : tête, torse et bras, mains, jambes, pieds.
  La bibliothèque contient 145 apparences et variantes de têtes issues de
  TFC (19), Half-Life (34), Opposing Force (64) et Blue Shift (28).
  Les modèles humanoïdes sont adaptés au squelette Soldier ; le Chumtoad et
  les créatures non humanoïdes sont exclus. Les doublons binaires sont regroupés.
  Les limites sont coupées par des plans avec interpolation des UV, refermées
  par des faces, puis ajustées à des interfaces elliptiques communes. Six
  petites bandes de raccord masquent les différences de périmètre. Chaque
  source produit un MDL à cinq bodygroups vide/pièce. Le moteur dessine les
  cinq pièces sur une seule entité avec la pose commune du rig Soldier.
  Les deux animations présentes dans chaque pièce sont remplacées au rendu
  par les transformations du rig parent et ses 77 séquences.
- **Arme :** HK416 avec chargeur droit ou tambour procédural, plus un embout
  de canon optionnel. Le chargeur utilise les bodygroups ; l'embout est désormais
  un modèle indépendant fixé à un os par l'extension moteur. Les neuf
  animations du modèle source et les mains HEV sont conservées. Les pièces suivent les
  os appropriés, y compris le chargeur de rechange pendant le rechargement.
- **Aperçus :** le renderer du moteur dessine directement les MDL animés,
  avec profondeur matérielle et cadrage automatique. Les vues du personnage
  et de l'arme utilisent le même mécanisme d'assemblage qu'en jeu.
  Le chemin précédent en sprites reste disponible pour l'ancien moteur.
- **En jeu :** le fusil en première personne et un mannequin animé dans la
  salle reflètent la composition validée, ainsi que les personnages des autres
  joueurs. Les armes au sol et portées en troisième personne conservent leurs
  modèles classiques ; leurs variantes modulaires restent à adapter.

Les coupes sont maintenant planes et fermées, mais l'adaptation automatique
des silhouettes et les textures aux raccords demandent encore une finition,
notamment pour les monstres, les manteaux et les morphologies très différentes.
Il ne s'agit pas d'une retopologie manuelle parfaite de chaque personnage.
Les 145 sources sont compilées et chargeables ; chaque combinaison possible
n'a pas été contrôlée visuellement. Les textures du tambour demandent aussi
une finition. Les tailles de chargeur et les dégâts restent ceux du SDK.

Le choix des skins F2 est indépendant du catalogue technique F1 et ne consomme
aucune jauge. Les anciennes entrées de tête/torse/jambes de F1 sont conservées
comme propositions d'équipements ; elles ne pilotent plus l'apparence du
mannequin. Les gants et chaussures sont pour le moment échangés par paire.

## Bibliothèque Team Fortress Classic

Source locale : `F:/SteamLibrary/steamapps/common/Half-Life/tfc`.
`import_tfc.py` importe 585 fichiers de contenu et références, dont les 100
modèles, les cartes, textures WAD, sprites, sons et décors. Le manifeste avec
provenance et empreintes SHA-256 est dans
`runtime/xash3d/tfc_assets/import-manifest.json`.

Le moteur monte les ressources artistiques via `fallback_dir`. Les fichiers
d'interface TFC sont conservés dans `reference/`, hors des chemins de recherche :
son `commandmenu.txt` déclenchait un plantage de la DLL Half-Life, corrigé en
isolant ces fichiers. Les DLL, exécutables et configurations TFC ne sont pas
injectés dans le prototype.

Les BSP originaux restent intacts. Quinze copies `vf_tfc_<nom>` reçoivent un
point de départ solo : 2fort, avanti, badlands, casbah, crossover2, cz2, dustbowl,
epicenter, flagrun, hunted, push, ravelin, rock2, warpath, well.
Des entités propres à TFC ne sont pas reconnues par le SDK Half-Life : objectifs,
classes, équipes, réapparitions et certains accès spécifiques restent à adapter.
Leur présence comme ressources ne rend pas automatiquement toutes les armes
TFC utilisables avec les animations et le comportement de Half-Life.

Le contenu Valve et les modèles GameBanana restent locaux et hors de Git.
Le HK416 vient de https://gamebanana.com/mods/640445 ; les dérivés gardent les
conditions des auteurs. Cette étape ne publie aucun contenu.

L'onglet arsenal F2 expose 65 modèles : l'intégralité des `v_*.mdl` et
`p_*.mdl` TFC, ainsi que grenades, projectiles et constructions. Il s'agit
d'un catalogue en 3D avec le nombre de séquences originales. Les comportements
de ces armes ne sont pas encore portés ; le HK416 reste le fusil jouable.
Le manifeste `generated/skins/arsenal.json` conserve les noms des animations.

## Animations

Les keyframes sont modifiables dans les SMD : translation et rotation de
chaque os, nombre de frames, cadence et bouclage. Les QC portent les séquences
et événements. Le chemin de travail est : décompilation locale, édition des
SMD/QC, compilation StudioMDL, essai dans le moteur. Le modèle du HK416 conserve
ses neuf animations d'origine dans cette version ; aucune nouvelle animation
d'arme n'est annoncée comme terminée. Une modification du rechargement devra
également synchroniser les événements de sons et la logique de munitions.

## Code et vérification

- `game_shared/vf_loadout.*` : catalogue, budgets, validation et codage des variantes.
- `dlls/vf_equipment.*` : validation serveur atomique, mannequin, message `VFBuild` v2.
- `cl_dll/vf_character.*` : interaction, aperçu des choix et modèle en main.
- `cl_dll/vf_preview.*` : chargement des meshes et rendu 3D dans le menu.
- `cl_dll/vf_skinmenu.*` : atelier F2, filtres, isolation et arsenal.
- `game_shared/vf_appearance.*`, `dlls/vf_skins.*` : catalogue des apparences,
  validation serveur, cinq pièces atomiques, mannequin et sauvegarde.
- `studio_assets.py`, `build_skins.py` : lecture MDL locale, adaptation,
  coupes planes, interfaces, compilation et manifests de provenance.
- `pack_previews.py` : conversion sans perte et regroupement des textures.
- `build_modular.py` : décompilation locale, adaptation des squelettes,
  construction des pièces, compilation StudioMDL, export des aperçus.
- `import_tfc.py` : import non destructif et cartes d'exploration.

Le catalogue externe est ASCII :

```text
slot|id|tier|nom|categorie|univers|TED|IP|HS|OI|SIG|BIO|description|visual
```

`visual` vaut 0/1/2 pour les trois zones du personnage, 0/1 pour alimentation
et bouche, 0 ailleurs. Le client et le serveur vérifient la même empreinte de
catalogue. Les choix sont conservés dans les sauvegardes Half-Life ; une nouvelle
partie indépendante repart du kit de base. Un changement de catalogue remet
également le kit de base, pour éviter de réinterpréter les anciens indices.

```powershell
python vector-fields/build_modular.py
python vector-fields/build_skins.py
./vector-fields/build.ps1
python vector-fields/tests/skin_geometry_test.py
python vector-fields/play.py --smoke-skins
python vector-fields/play.py --smoke
python vector-fields/play.py --smoke-maps
```

La compilation produit les deux DLL Win32 et exécute 160 assertions, dont
l'indépendance des systèmes, le rejet des données invalides et les 27 combinaisons
corporelles. Le test en jeu vérifie la validation, le refus des configurations
invalides et la sauvegarde/recharge. Il exerce le tir et le rechargement et
produit des captures pour contrôle visuel. Le test des cartes ouvre chaque
carte séparément et capture son point de départ ; il ne parcourt pas toutes
ses salles. Rapports dans `build/verification.json` et `build/maps-verification.json`.

Le test des skins vérifie les cinq sélections, le rejet atomique d'un indice
invalide ou d'un catalogue différent, la restauration après sauvegarde, et les
noms/variantes des cinq MDL du mannequin. Il charge les 210 aperçus dans une
même session, vérifie l'absence d'épuisement des sprites et capture plusieurs
assemblages pour contrôle visuel. Rapport : `build/skins-verification.json`.
Le test de géométrie vérifie la conservation des surfaces et UV aux coupes,
les interfaces, les 145 MDL, leur hiérarchie compatible, la couverture des
modèles d'armes TFC et l'égalité exacte des pixels après regroupement.

La version 0.5 utilise une compilation locale du moteur Xash3D FWGS 0.21
(base 9137964, win32-i386). Voir [le contrat et la compilation du moteur](engine/README.md).
Le test natif charge les 210 modèles, anime les aperçus, exerce le tir et le
rechargement, refuse les assemblages invalides et vérifie la sauvegarde.
Le test à deux clients vérifie la synchronisation des skins et des 21 choix
d'équipement, y compris lorsqu'un joueur rejoint une partie existante.
Le réseau est testé en local ; l'hébergement Internet reste à éprouver.
Les 13 mesures des fonctions de déplacement du SDK restent identiques.
Les effets combinatoires et l'interface à la souris restent à développer.


## Personnages GIGN ajustes

Le lanceur `Jouer - Vector Fields.cmd` ouvre la famille GIGN : six tenues
plus la base de comparaison, cinq zones ajustées aux polygones du donneur,
un modèle partagé et un squelette aux proportions du GIGN. Les anciens
personnages restent disponibles dans leurs collections. Voir
[la construction, les textures et les limites](assets/personas/README.md).
Les rapports et captures sont dans `build/personas-verification.json`,
`build/personas-multiplayer-verification.json` et `build/gign-personas-in-game.jpg`.

## Cinq univers assortis

Le lanceur `Jouer - Vector Fields.cmd` équipe un GIGN et un R1 assortis.
Les cinq nouveaux ensembles (Grande Guerre, Bedrock, New York noir, naufragé
et plongeur) sont décrits dans [assets/EXPEDITIONS.md](assets/EXPEDITIONS.md).
Les personnages restent entièrement couverts, avec les yeux visibles.


## Effets de tir R1

Huit profils de présentation sont disponibles dans **F3 > Weapon FX / R1** :
Hydro, Electro, Cryo, Thermal, Toxic, Corrosion, Sonic et Kinetic. Le tireur voit une étoile frontale dédiée ; le jet axial est réservé aux vues
extérieures. Les flashes historiques du modèle R1 sont filtrés. Les marques de
balle sont réduites à 4–7 unités. Chaque profil possède ses particules, sa
trace et ses sons, avec des contacts métal, bois et chair distincts.
**Open FX test range** ouvre le stand de contrôle. Kinetic reste le profil
normal ; les profils de test ne changent pas les dégâts.
Voir [les commandes, les assets et les tests](WEAPON_FX.md).

## Validation et maintenance

`powershell -ExecutionPolicy Bypass -File vector-fields/build.ps1` compile les DLL,
les tests C++ et valide les suites unitaires et les assets. Après déploiement avec
`python vector-fields/play.py --visual-lab --deploy-only`, exécuter
`python vector-fields/validate.py --suite native`, puis `--suite multiplayer`.
`--suite all` enchaîne les quatre suites ; `--list` donne la liste maintenue.

Les traits de modèles sont dans `data/model_contract.json`. Les rigs et les
pièces d’arme disposent de caches séparés qui vérifient leurs dépendances et
sorties. Voir [les contrats](docs/ARCHITECTURE.md) et
[la version 0.20.7](docs/RELEASE-0.20.7.md).
