# Morts animées et démembrement — prototype

Relancer **Jouer - Vector Fields.cmd**, puis **F4** pour la salle GIGN et **F8**
pour le laboratoire des morts. Choisir une animation à gauche, une cible, une mort classique ou
électrique, puis le membre : tête, bras gauche/droit, jambe gauche/droite,
corps entier ou tous les membres. Le bouton ferme le menu et cadre la cible.
La cible revient après deux secondes ; son ancien cadavre reste quinze secondes.
« Retirer les cadavres » nettoie aussi les fragments de cet essai.

Le membre perdu génère désormais une pièce entière et trois petits fragments portant la finition du vêtement, avec
projection de sang et surface de blessure sur le corps restant. Les cinq zones
de tenue sont conservées séparément au moment du décès. Une mort électrique
contracte le corps pendant environ 0,85 seconde, puis le fait tomber ; des arcs
et le son électrique complètent la signature. Le mouvement complet dure
1,68 seconde. Le squelette et les 77 indices des animations historiques sont
conservés ; la séquence électrique est ajoutée à l’indice 77.

Démembrement et cause de décès sont deux données indépendantes. On peut donc
combiner une tête explosée ou une jambe absente avec une mort électrique.
« Effet choisi » reprend l'effet de l'atlas ou celui du laboratoire des effets.
Les huit éléments et huit réactions sont associés à des gestuelles : contractions,
agonie, recul ou perte d'équilibre. Les fragments emportent des traînées de sang
et de particules élémentaires. Voir [l'atlas, l'inventaire et les essais](DEATH-ATLAS.md).

Cinq matériaux de plaie sont maintenant calculés et appliqués aux coupes du cou,
des bras et des cuisses, avec des UV continus et des raccords animés.
Voir [les textures, dimensions et captures natives](WOUND-TEXTURES.md).

## Périmètre et prochaines étapes

Les cibles de la salle et les joueurs/bots utilisant nos porteurs GIGN sont
raccordés. Une mort ordinaire capture l’état actif avant sa suppression et
produit un cadavre animé. Les explosions intégrales historiques restent dans
leur parcours existant. Ce prototype ne raccorde pas encore tous les monstres
Half-Life à un modèle démembrable.

Les boutons forcent le membre perdu sur un vrai coup fatal. Aucun seuil de
headshot ou d’accumulation de dégâts par membre n’est ajouté pour l’instant.
La politique de dégâts pourra ensuite sélectionner le masque des membres
perdus sans multiplier les animations : chaque animation fonctionne avec
les 32 combinaisons de pertes. Les réglages de l’arme et les seuils seront
abordés après la revue visuelle.

Le découpage utilise les faces et os existants ; il constitue une première
version visible. Les sections des bras et cuisses sont planes ; le cou suit le col existant.
Ce sont des séquences animées et des fragments balistiques GoldSource.
Un ragdoll articulé demanderait une autre extension du moteur.

## Architecture et vérification

`build_deaths.py` génère deux MDL, les groupes de corps et blessures, les vingt
variantes de fragments, dix mouvements importés et la contraction électrique. Les modèles vivants ne
sont pas remplacés. La reconstruction suit les empreintes des sources et des
sorties. `build.ps1` et `play.py` incluent la génération ; `release.py` vérifie
également les empreintes des deux modèles déployés.

Le serveur crée une entité de cadavre indépendante, conserve les cinq finitions,
l’effet et le masque des membres. `VFCorpse` transporte ces données, l’âge et
la durée restante en 13 octets. Un nouvel arrivant reçoit les cadavres présents ;
la réapparition et le changement de tenue de la victime ne les modifient pas.
Le renderer v3 existant assemble les cinq zones sur le squelette du cadavre.
Le serveur limite ces entités à douze cadavres et 72 fragments spécifiques.
Les cadavres disparaissent après quinze secondes ; les fragments suivent une
trajectoire balistique, se posent au sol puis disparaissent après douze secondes.
`VFFragment` diffuse leur effet, âge, variante et identifiant de génération en
dix octets. Les arrivants tardifs ne rejouent pas les explosions anciennes.

Commandes de développement, en solo ou avec `sv_cheats 1` :

```text
vf_death_lab
cmd vf_range_death 0 head electro
cmd vf_range_death 0 left_arm standard
cmd vf_range_death 0 right_leg corrosion
cmd vf_death_test head electro
cmd vf_death_clear
vf_death_client
```

Les régions reconnues sont `none`, `head`, `left_arm`, `right_arm`, `left_leg`,
`right_leg`, `all`. Sans paramètre d’effet, la commande conserve l’état actif.
La commande `vf_death_test` tue le joueur pour contrôler son parcours réel.

```text
python vector-fields/tests/death_visual_native_test.py --assets
python vector-fields/tests/death_visual_native_test.py
python vector-fields/tests/death_visual_multiplayer_test.py
python vector-fields/tests/death_ui_native_test.py
```

Les contrôles couvrent le squelette, les UV et la silhouette intacte, les 77
séquences, les 32 combinaisons, les fragments, les morts classiques/électriques,
la réapparition, l’expiration et les captures du moteur. Les essais réseau
vérifient la mort distante, une tenue mélangée, la réapparition de la victime
et l’arrivée d’un troisième client. Le test de menu simule le clic réel,
contrôle la sauvegarde, le plafond de cadavres, leur retrait et la hauteur
au sol après une mort accroupie. Les rapports et captures sont sous
`build/death-visual` et `build/animation-native/death-*`.

## Bibliothèques importées

Recherche et intégration vérifiées le **10 octobre 2026**. Trois vrais mouvements
externes sont désormais compilés sur notre GIGN : `Death01` de Quaternius à
l’indice 78, `Death_A` de KayKit à l’indice 79 et `Death_B` à l’indice 80.
Leurs durées sont respectivement 2,375 s, 0,8 s et 2,633 s. Les 77 animations
historiques et la contraction électrique à l’indice 77 sont conservées.

En mode automatique, les morts ordinaires varient entre les trois premières chutes.
Les morts élémentaires suivent maintenant les seize profils de l'atlas. Sept
mouvements Mixamo ont été ajoutés aux indices 81 à 87. Le catalogue F8 permet de
forcer un mouvement, indépendamment du membre et de l'effet. Les deux familles
électriques couplées sont ArcChain et Superconduction ; Shatter utilise la chute
raide du froid. Voir [l'inventaire des 24 candidats](DEATH-ATLAS.md).

Le transfert est reproductible via `external_death_animations.py` : lecture
glTF/GLB, référence T-pose, correction des axes, rotations globales reportées
sur les 28 os existants, longueurs préservées et appui du corps au sol. La fin
de chute corrige l’orientation des jambes à la hanche pour que les différences
de proportions ne suspendent pas le torse au-dessus du sol. Les signatures
visuelles suivent un centre du torse extrait de chaque séquence compilée.

Les fichiers donneurs originaux et leurs empreintes sont conservés dans
`assets/animations/death-banks/sources.json`. Ils proviennent de miroirs publics
des exports des auteurs ; aucune géométrie ou texture donneuse n’est importée.
Le fichier Quaternius conservé contient 46 clips, dont une mort ; le fichier
KayKit General en contient 15, dont deux morts et leurs poses finales. Les autres
clips restent disponibles pour des transferts futurs. Sept clips Mixamo les complètent maintenant : dix morts importées sont livrées.
Le miroir Mixamo recense 886 animations de toutes sortes, dont 24 candidats
inspectés pour cet atlas ; ce nombre ne désigne pas 886 morts.

Sources des banques : [Quaternius](https://quaternius.itch.io/universal-animation-library)
et [KayKit](https://kaylousberg.itch.io/kaykit-character-animations).
La [seconde bibliothèque Quaternius](https://quaternius.itch.io/universal-animation-library-2) vise surtout le combat, le parkour et les
mouvements de zombies ; aucune nouvelle mort de cette banque n’est livrée ici. [Mixamo](https://www.mixamo.com/) est maintenant intégré ; les exports GLB
et leur provenance sont archivés avec les deux banques précédentes.

Commandes de revue :

```text
cmd vf_range_death 0 head electro kaykit_a
cmd vf_range_death 0 left_arm standard quaternius
cmd vf_range_death 0 right_leg corrosion kaykit_b
cmd vf_range_death 0 head standard legacy
cmd vf_death_test left_leg electro quaternius
cmd vf_death_view
```

Le dernier argument est optionnel : `auto`, `legacy`, `quaternius`, `kaykit_a`,
`kaykit_b`, puis les identifiants Mixamo et les variantes listées dans
`assets/animations/death-atlas.json`. Un identifiant inconnu ne cause aucun dégât. `vf_death_view` cadre
le dernier cadavre dans une allée de la salle pour sa revue animée ; il est
réservé au développement sur `vf_range`, comme l’inspection des plaies.

```text
python vector-fields/tests/external_death_animations_test.py --assets
python vector-fields/tests/external_death_animations_test.py
```

La validation couvre chaque pose compilée, les longueurs des os, le contact au
sol, les trois chutes combinées avec tête, deux bras et deux jambes retirés,
l’électricité, un choix F8 par clic réel, la sauvegarde et une mort du joueur.
Captures et rapports : `build/external-deaths`.

Le test réseau accepte `--motion quaternius`, `--motion kaykit_a` ou
`--motion kaykit_b`. La chute Quaternius et le parcours électrique historique
ont été vérifiés avec trois clients, réapparition, changement de tenue et
arrivée tardive. Les raccords des cinq plaies sont contrôlés sur les 934 poses
importées en plus des poses historiques.

## Finitions des fragments depuis 0.20.7

Le membre détaché conserve deux finitions capturées au décès : torse/gants pour les bras, jambes/bottes pour les jambes. La tête garde sa finition propre. Chaque petit fragment suit les mêmes règles que son membre entier. Une réapparition ou un changement de tenue de la victime ne modifie pas ces textures.

Les vingt maillages physiques restent partagés. Deux références de matériaux choisissent les textures des vêtements et des extrémités dans le modèle Studio natif ; 196 familles de références couvrent les quatorze finitions, sans créer 196 images ni utiliser d’assemblages supplémentaires. Les familles uniformes 0 à 13 restent compatibles. La banque de la seconde zone reprend les pixels existants ; les textures de plaie restent fixes. Le compilateur classique produit les quatorze familles uniformes puis `fragment_skins.py` ajoute les références combinées au MDL, sans modifier la géométrie.

Les tests des assets vérifient tous les couples, le test C++ vérifie l’encodage/décodage, et le test natif couvre une véritable mort avec vingt fragments et des gants/bottes distincts. Le test à trois clients vérifie aussi la finition du bras détaché chez l’observateur tardif.
