# Version 0.15.0 — Nomade et Bastion

Deux nouvelles pièces par emplacement d’arme, soit 24 géométries ajoutées.
Toutes utilisent les textures déjà présentes : douze finitions, applicables
à l’arme entière ou indépendamment à chaque pièce. Aucun atlas supplémentaire.

| Emplacement | Nomade | Bastion |
|---|---|---|
| Châssis | Châssis Nomade, flancs ajourés | Châssis Bastion, carter renforcé |
| Canon | Canon à longerons | Canon à caisson |
| Bouche | Cache-flamme à griffes | Compensateur hexagonal |
| Chargeur | Chargeur coudé | Chargeur à tambour bas |
| Culasse | Culasse à anneau | Culasse à double piston |
| Charge | Cassette bi-tube | Bloc triple chambre |
| Projectile | Berceau monodard | Rack à disques |
| Optique | Dioptre annulaire | Viseur prismatique |
| Sous-canon | Stabilisateur replié | Garde-main caréné |
| Poignée / crosse | Crosse triangulée | Crosse à joue réglable |
| Batterie | Réserve toroïdale | Batterie à trois cartouches |
| Refroidissement | Dissipateur à pointes | Ventilateurs doubles |

## Utilisation

Ouvrir **F11**, puis choisir **Nomade** ou **Bastion** au-dessus de l’aperçu.
Les flèches de pagination sous le catalogue permettent aussi de choisir une
seule nouvelle pièce et de la combiner avec les anciennes. **Appliquer** valide
l’ensemble. Les deux nouveaux châssis s’alimentent par-dessous. Les quatre
chargeurs partagent leur col d’insertion et leur prise de main ; ils fonctionnent
sur les plateformes inférieure, latérale et supérieure.

Les commandes `vf_reference 0|1|2|3` chargent respectivement Atelier, Circuit,
Nomade et Bastion. Le guide du jeu décrit les quatre variantes de chaque
emplacement et les six châssis.

## Contenu et compatibilité

Le R-01 comporte désormais 50 pièces : six châssis et quatre pièces pour chacun
des onze autres emplacements. Cela donne 25 165 824 combinaisons de formes.
Les 50 formes avec douze finitions représentent 600 entrées ; avec les 60 pièces
GIGN et les 24 accessoires provisoires, le lootpool contient **684 entrées**.

Les nouvelles géométries sont dans `build_reference_extensions.py`. Elles
conservent les interfaces animées `Bone71` pour le chargeur, `R01_Bolt` pour la
culasse et `Bone76` pour les autres pièces. Les prises des mains et les séquences
existantes sont réutilisées. Les lentilles des deux nouvelles optiques utilisent
le verre existant avec le même rendu additif.

Les identifiants A/B, Traverse et Zénith sont conservés ; les nouvelles pièces
portent les suffixes C/D. La persistance par identifiants conserve les anciens
équipements malgré le changement d’ordre du catalogue. Le protocole reste 3.
Le catalogue contient 238 objets sur les 254 disponibles ; 16 places restent
avant qu’une extension de capacité devienne nécessaire.

Cette livraison ajoute des formes et des objets sélectionnables. Le tir, les
munitions, la capacité et la recharge effective restent ceux du MP5, comme dans
la version précédente ; le tambour n’augmente pas encore la capacité de tir et
les ventilateurs ne changent pas la dissipation de chaleur.

## Vérifications reproductibles

`build.ps1` compile les DLL et vérifie les nouvelles géométries : présence des
24 pièces, 288 couples forme/finition, coordonnées de textures, col d’insertion
des chargeurs, rendu additif du verre et enregistrement des objets.

`python vector-fields/tests/reference_extensions_test.py --mode native`
exerce les nouveaux boutons, les 24 aperçus, les deux armes en main, le tir et
le rechargement des deux nouveaux chargeurs sur les trois montages, puis une
sauvegarde/reprise d’un assemblage mêlant anciennes et nouvelles pièces.

L’audit natif vérifie 1 194 assemblages : chaque pièce, puis chaque paire de
variantes dans deux emplacements. Il ne parcourt pas les 25 millions de
configurations complètes. La vérification géométrique ne remplace pas une
inspection visuelle de toutes les combinaisons.

Les rapports et la planche de contrôle sont dans `vector-fields/build/` :
`reference-extensions-assets.json`, `reference-extensions-native.json` et
`r01-new-parts.jpg`.
