# Famille de personnages GIGN

Six premières tenues peintes pour une base commune : récupérateur des ruines, sentinelle
de la forge, gardien d'os et de silex, veilleur de la canopée, veilleur
alchimiste et opérateur de porcelaine. La base GIGN sans changement de texture
reste disponible comme choix de comparaison. Cinq nouvelles tenues assorties aux armes
sont ajoutées dans le [pack Cinq univers](../EXPEDITIONS.md) : tranchées, mineur,
détective noir, naufragé et plongeur. Les anciens choix sont conservés.

## Essayer

Lancer `Jouer - Vector Fields.cmd` à la racine du projet. Cet atelier utilise
les ressources du jeu installé et ouvre directement Apparence libre, filtre
GIGN. Choisir une tenue, cliquer sur « Appliquer aux 5 zones », puis
« Appliquer ». Les boutons de gauche permettent également de choisir une
finition différente pour la tête, le torse/bras, les mains, les jambes et les
chaussures. Faire tourner le modèle, zoomer à la molette et utiliser les
boutons Animation/Pause pour inspecter les raccords.

Les entrées sont aussi ajoutées au catalogue de l'atelier principal. Une
session déjà ouverte garde son ancien client et ses modèles en mémoire ;
le lanceur dédié utilise le client actualisé sans interrompre cette session.

## Construction autour du GIGN

La géométrie provient du GIGN Counter-Strike classique installé localement.
Les cinq zones sont des partitions des 740 triangles existants, sélectionnés
aux contours du cou, des poignets, de la ceinture et des bottes. Aucun triangle
supplémentaire, anneau, capuchon de coupe ou déplacement vers les profils
universels des anciens personnages n'est ajouté. Les coordonnées et les UV
d'origine sont conservés ; les frontières communes partagent leurs sommets
et leurs influences d'os.

Le squelette `persona_rig.mdl` reprend les positions et axes des articulations
du GIGN avec les noms d'os, les rotations d'animation et l'ordre des 77
séquences compatibles avec le système de joueur existant. Les translations
locales des animations sont adaptées aux proportions du GIGN. Ce squelette
est sélectionné lorsque les cinq zones appartiennent à cette famille,
y compris lorsque leurs finitions diffèrent.

`persona_scout.mdl` contient une seule géométrie découpée en cinq groupes et
douze familles de textures : original + onze tenues. Changer de tenue ne
recharge pas la géométrie. La tête participe au changement de finition ;
les anciennes familles de simples teintures conservent leur visage initial.
Le réseau et les sauvegardes utilisent les cinq identifiants d'apparence
existants. Le fichier `personas.json` décrit les thèmes ; les identifiants
numériques attribués sont consignés dans `generated/personas/manifest.json`.

## Textures et reconstruction

Les atlas haute résolution se trouvent dans les onze sous-dossiers, chacun
avec son `prompt.txt`. Ils ont été créés avec l'outil intégré **image_gen**
en édition de `reference-uv.png`, qui reprend exactement la carte GIGN de
512 × 512 pixels. `generation.json` conserve la provenance des fichiers.
La compilation réduit chaque atlas à 512 × 512 pixels, avec une palette de
256 couleurs compatible GoldSrc. Les sources haute résolution sont conservées.

```powershell
python vector-fields/build_personas.py
./vector-fields/build.ps1
python vector-fields/play_personas.py --deploy-only
python vector-fields/tests/personas_engine_test.py
python vector-fields/tests/personas_multiplayer_test.py
```

Le constructeur est aussi appelé par la compilation générale avec `--ensure`.
Il contrôle l'empreinte des images, du modèle source et des animations et
conserve les identifiants existants du catalogue.

## Résultats et limites

Les tests couvrent les douze familles sur les cinq zones, les 45 arêtes de
raccord et leurs 44 sommets communs, ainsi que 18 poses issues de six
animations. L'écart mesuré entre les bords compilés est nul. Les captures
natives montrent les onze tenues de face et de dos, cinq zones isolées,
plusieurs poses et un assemblage de cinq thèmes. L'application par l'interface,
l'annulation, la sauvegarde et la restauration sont vérifiées. Les deux
clients locaux testent aussi la diffusion des apparences et l'arrivée tardive.
Ce contrôle ne prétend pas valider visuellement toutes les 77 animations.

- La silhouette reste celle du GIGN. Les os, feuilles, plaques et conduits
  peints changent la lecture des vêtements, sans créer de volume supplémentaire.
- Les raccords sont ajustés à cette famille. Mélanger une pièce GIGN avec un
  autre corps historique peut toujours produire une différence de contour.
- Mélanger des thèmes différents crée naturellement une rupture de matière ou
  de couleur, même lorsque les surfaces sont jointes.
- Les UV hérités comportent des zones symétriques ; ces tenues évitent donc
  les textes et insignes dont la lecture serait gênée par un miroir.
- Le rendu utilise une texture diffuse indexée : pas de matériau PBR, de relief
  physique ni de lumière réellement émise par les détails peints.
- Les gants des modèles d'armes en première personne restent ceux de leurs
  propres modèles. Ces tenues concernent le corps visible dans l'atelier,
  sur le mannequin et par les autres joueurs.

Aperçus : `build/gign-personas-in-game.jpg` et
`build/gign-fitted-comparison.jpg`. Rapports :
`build/personas-verification.json` et
`build/personas-multiplayer-verification.json`.
