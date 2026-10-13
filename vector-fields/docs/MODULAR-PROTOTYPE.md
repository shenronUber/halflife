# Prototype de grille modulaire

Lancer **Essayer la grille modulaire - Vector Fields.cmd** à la racine du projet.
La carte `vf_modular` est intégrée au jeu principal `runtime/vector-engine/vf_visual`, avec les mêmes client, serveur, moteur et ressources que la salle combinée de tir et de parcours. **F4** ouvre le menu pour choisir cette grille, la salle combinée ou les [modules jouables](TILE-LABORATORY.md). Son ancien lanceur reste un raccourci vers le jeu principal.

La compilation et la publication passent par `build_release.py`, qui valide un candidat privé complet avant de remplacer le jeu installé. Les anciens dossiers `vf_modular_lab` et `build/modular` restent des archives et ne sont plus utilisés par les lanceurs.

## Dimensions retenues

Les **270 BSP originaux installés** ont été mesurés directement : 125 Half-Life,
25 Counter-Strike, 15 Team Fortress Classic, 37 Blue Shift et 68 Opposing Force.
Les 165 cartes HL/CS/TFC fournissent la comparaison principale ; les extensions
sont ajoutées à l'inventaire pour couvrir les autres cartes disponibles.
Les copies importées dans nos runtimes
ne sont pas recomptées. Les résultats détaillés et les chemins des fichiers se trouvent
dans [dimensions.csv](validation/modular/maps/dimensions.csv) et
[dimensions.json](validation/modular/maps/dimensions.json).

| Ensemble | Nombre | Moyenne grand × petit côté | Médiane grand × petit côté |
|---|---:|---:|---:|
| Half-Life, campagne/démo/entraînement | 106 | 4 348 × 3 253 | 3 943 × 2 840 |
| Half-Life, cartes multijoueurs | 19 | 3 879 × 2 802 | 4 088 × 2 656 |
| Counter-Strike | 25 | 5 085 × 3 892 | 5 152 × 3 904 |
| Team Fortress Classic | 15 | 7 141 × 4 337 | 7 360 × 4 112 |
| Blue Shift | 37 | 4 976 × 4 078 | 4 824 × 3 936 |
| Opposing Force, ensemble installé | 68 | 5 508 × 4 379 | 5 608 × 4 294 |

Unités natives du moteur. Grand et petit côtés sont triés par carte avant le calcul
des statistiques. Leurs médianes ne décrivent donc pas nécessairement une carte précise.
On mesure les sommets des faces du modèle monde, en excluant les textures de ciel et
les faces techniques. C'est une **enveloppe géométrique**, comprenant encore le décor
et les espaces fermés ; ce n'est pas la surface navigable. Les sous-modèles de portes
et plateformes sont exclus, car leurs coordonnées peuvent être locales.

| Paramètre | Première valeur |
|---|---:|
| Côté d'une cellule | 1 280 |
| Interstice entre deux cellules | 256 |
| Pas de grille | 1 536 |
| Emprise des neuf cellules | 4 352 × 4 352 |
| Sol principal | Z = 0 ; épaisseur 64 |
| Largeur utile de passerelle | 192 |
| Mur de wall run | Longueur 640 ; sommet Z = 256 |
| Approche/arrivée du mur sur chaque cellule | 192 |
| Volume de récupération après chute | Z = −512 à −960 |

L'emprise est `3 × 1280 + 2 × 256 = 4352` par axe, soit environ 18,94 millions
d'unités carrées, proche des enveloppes CS mesurées. À 320 unités/seconde, une cellule
représente quatre secondes de course et l'interstice 0,8 seconde. Les distances réelles
augmentent avec les obstacles. Ces valeurs sont un point de départ pour les essais.
La source commune est `game_shared/vf_modular_layout.h` ; le générateur de BSP y lit
les dimensions, ce qui évite deux configurations divergentes.

## Ce qui est tiré au lancement

Le serveur choisit une partition exacte de la grille : carré d'une cellule, domino
de deux cellules, I de trois cellules ou L de trois cellules, rotations comprises.
Il existe 583 partitions géométriques autorisées au total. Le prototype en sélectionne
une parmi celles contenant trois à six modules, afin de montrer plusieurs transitions.
Les neuf cellules sont toujours occupées ; aucune pièce ne déborde et aucun module
ne contient de cellule isolée.

Les douze voisinages de la grille reçoivent chacun un traitement :

- **Même module** : sol plein sur toute la largeur de l'interstice. Un I ou un L
  forme ainsi un ensemble continu, sans étranglement artificiel entre ses cellules.
- **Modules distincts** : passerelle de 192 unités ou mur de wall run sur le vide.
  Chaque grille possède au moins une liaison de chaque type.
- **Passerelle** : un pilier peut descendre sous son centre. S'il y a plusieurs
  passerelles, le tirage montre au moins une version avec pilier et une sans.

Chaque cellule reçoit deux à quatre blocs parmi six emplacements réservés, avec
des hauteurs de 48 à 192 unités. La croix centrale et les approches des jonctions
restent libres. Cela fournit des volumes simples pour courir, glisser, sauter,
prendre un rebord et se couvrir. Toutes les cellules voisines restent reliées.

Les surfaces sont de vrais modèles BSP précompilés : le serveur active leur collision
et leur visibilité avant l'arrivée des joueurs. Le tirage ne modifie pas le fichier
sur disque et ne demande pas une recompilation entre deux parties. Les modèles
inactifs sont sans collision et invisibles. Le moteur exige `MOVETYPE_PUSH` pour les
solides BSP. Un marqueur réservé aux objets immobiles du prototype est transmis dans
leurs quatre octets de contrôleur existants. Le serveur de déplacement accepte ce
marqueur et présente ces objets comme immobiles au client installé (`MOVETYPE_NONE`
dans leur état réseau). Les portes et plateformes ordinaires restent exclues.

## Commandes

- **F4** : menu de cartes ; choisir Grille modulaire pour un nouveau tirage.
- **F5** : affiche graine, grille et liaisons dans la console.
- **F10 / F12** : troisième / première personne.
- **Console** : `vf_modular_seed 42`, puis `map vf_modular`, pour rejouer un tirage.
  Remettre `vf_modular_seed 0` pour les tirages automatiques.
- **Console** : `cmd vf_modular_check` vérifie les états des 102 candidats et fait
  des traces réelles sur les douze jonctions, sans changer la carte.
- **Lanceur** : `Essayer la grille modulaire - Vector Fields.cmd --seed 42`.

Pour le wall run, prendre de l'élan le long du mur et sauter en gardant Avancer.
Orienter le regard du côté du mur, même légèrement, ou maintenir la direction
latérale qui pousse vers lui permet d'accrocher. Le regard reste ensuite libre
jusqu'à 90° de chaque côté du cap conservé. Une chute ramène au départ par un
téléporteur de récupération. Voir [Wall run](WALLRUN.md).
La sauvegarde conserve l'agencement ; elle ne provoque pas un nouveau tirage.

## Construction et validation

```powershell
python vector-fields/measure_maps.py
powershell -ExecutionPolicy Bypass -File vector-fields/build_modular_server.ps1
python vector-fields/build_modular_range.py --ensure
python vector-fields/play_modular.py --prepare-only
python vector-fields/tests/modular_native_test.py
python vector-fields/tests/modular_multiplayer_test.py
```

Le test C++ `modular_layout_test.cpp`, intégré à `cpp_tests.py`, contrôle les partitions
et 10 000 graines. Le test natif vérifie les traces, les franchissements de toutes
les jonctions actives, les wall runs dans les deux sens, la récupération, la sauvegarde
et les changements de graine. Les résultats sont conservés dans
`docs/validation/modular`, avec des captures prises dans le jeu.
Le contrôle multijoueur vérifie la même partition et les mêmes collisions sur
deux clients réels, dont un rejoint tardivement, puis une traversée de wall run.

[Vue du dessus du tirage 42](validation/modular/modular_overview.png) ·
[Vue au sol](validation/modular/modular_ground.png) ·
[Résultats natifs](validation/modular/native.json) ·
[Résultats multijoueurs](validation/modular/multiplayer/network.json).

Le BSP initial contient **2 634 faces et 104 modèles**, dont le modèle monde et le
volume de récupération. Les candidats inutilisés consomment encore des modèles BSP
et des entités. La compilation utilise un VIS rapide et un éclairage simple pour
itérer. La carte ouverte rend de nombreuses cellules simultanément visibles : les
dimensions comparables à CS ne garantissent pas les performances d'une version dense.
Avant d'ajouter les biomes détaillés, il faudra mesurer les surfaces effectivement
affichées, les entités, les collisions et les temps de rendu sur les machines visées.
