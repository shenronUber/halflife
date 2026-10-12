# Famille de personnages GIGN

Six premières tenues peintes pour une base commune : récupérateur des ruines, sentinelle
de la forge, gardien d'os et de silex, veilleur de la canopée, veilleur
alchimiste et opérateur de porcelaine. La base GIGN sans changement de texture
reste disponible comme choix de comparaison. Cinq nouvelles tenues assorties aux armes
sont ajoutées dans le [pack Cinq univers](../EXPEDITIONS.md) : tranchées, mineur,
détective noir, naufragé et plongeur. Les tenues d'inventeur et diesel sont aussi
conservées. Le [pack de cinq nouveaux costumes](NEW-COSTUMES.md) ajoute Red Son,
Sélénite, Héros masqué, Pilote de rallye et Soldat pénitent.
Deux [variations artisanales](ARTISAN-SETS.md) prolongent la porcelaine :
Opérateur de jade et Opérateur d’ambre, entre techwear, matières nobles et biofluides discrets.
Le même [ensemble de tenues](ARTISAN-SETS.md) comprend **Savage Butcher**, boucher
militarisé au tablier taché, et **Miami Vice**, costume bleu, chemise rose et aviateurs.

## Essayer

Lancer `Jouer - Vector Fields.cmd` à la racine du projet. L'inventaire opérateur
propose les collections et leurs cinq pièces équipables. Apparence libre,
filtre GIGN, reste accessible dans les options développeur : choisir une tenue,
cliquer sur « Appliquer aux 5 zones », puis « Appliquer ». Les boutons de gauche
permettent également de choisir une
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
vingt-trois familles de textures : original + vingt-deux tenues. Changer de tenue ne
recharge pas la géométrie. La tête participe au changement de finition ;
les anciennes familles de simples teintures conservent leur visage initial.
Le réseau et les sauvegardes utilisent les cinq identifiants d'apparence
existants. Le fichier `personas.json` décrit les thèmes ; les identifiants
numériques attribués sont consignés dans `generated/personas/manifest.json`.

## Textures et reconstruction

Les atlas haute résolution se trouvent dans les vingt-deux sous-dossiers, avec
leurs prompts et les corrections conservées. Ils ont été créés avec l'outil intégré **image_gen**
en édition de `reference-uv.png`, qui reprend exactement la carte GIGN de
512 × 512 pixels. `generation.json` conserve la provenance des fichiers.
La compilation réduit chaque atlas à 512 × 512 pixels, avec une palette de
256 couleurs compatible GoldSrc. Les sources haute résolution sont conservées.

Pour toute nouvelle variante, la bande courbe en haut à droite du pantalon
(repère x = 67 %, y = 4,7 %, origine en haut à gauche de l'atlas) prolonge
habituellement la cagoule autour du cou. La vérification des positions 3D du
donneur confirme qu'il s'agit du col, lié aux os du cou et du haut du torse.
Miami Vice utilise explicitement ce relief comme col de chemise rose
(`shirt_collar: true`) ; cette matière doit alors rejoindre les autres morceaux
du col et la chemise. Le petit rectangle à deux panneaux voisin appartient
à la tête et doit toujours suivre la couleur de la cagoule.
Une troisième bande, entre la face et le bras en bas à droite (repère
x = 77 %, y = 74 %), recouvre les côtés de la tête et doit suivre la même règle.

`persona_head_seams.py` vérifie aussi ces raccords automatiquement lors de la
compilation des vingt-trois familles. Il repère les îlots dans les triangles UV du
GIGN original et reprend la couleur dominante de la cagoule en conservant
les ombres du raccord. Seuls les raccords dont la couleur ou la luminosité
diffère trop sont corrigés ; le col de chemise déclaré est conservé et consigné
comme tel dans l'audit. Une marge de trois pixels prolonge les matières autour
des six îlots de tête et de cou pour que le filtrage ne lise pas le fond gris.
Elle reprend les texels intérieurs sur un bord étroit, sans toucher les yeux
ni les îlots voisins. Les images sources restent intactes.
Les PNG sources sont conservés. Les atlas utilisés pour compiler sont dans
`generated/personas/corrected-atlases`, et `generated/personas/head-join-audit.json`
consigne chaque contrôle. Les personnages importés et les anciennes familles
conservent leurs propres textures et leurs propres cartes UV.

Les [couches de continuité des têtes](HEAD-CONTINUITY.md), retouchées avec
image_gen pour les vingt-deux skins, reprennent les plis de l'arrière, des
côtés et du sommet en gardant les visages et les vêtements approuvés.
`persona_head_continuity.py` fait concorder leurs couleurs et ombres aux
vingt arêtes de raccord de la tête. Il affine aussi les indices autour des
raccords après conversion en palette ; cette étape conserve exactement la
palette choisie et les indices des vêtements. Le GIGN original reçoit aussi
l'ajustement de continuité. Les sources, prompts et résultats restent archivés.

L'export SMD de ces matières inverse aussi la conversion de StudioMDL en
coordonnées entières (`dimension - 1`) : les UV compilées retrouvent exactement
les texels du GIGN donneur, au lieu du décalage d'un pixel vers la gauche.
Cette correction commune s'applique au personnage, aux corps et aux fragments.
Les sommets et leurs normales de raccord restent ceux du modèle d'origine.

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

Les tests couvrent les vingt-trois familles sur les cinq zones, les 45 arêtes de
raccord et leurs 44 sommets communs, ainsi que 18 poses issues de six
animations. L'écart mesuré entre les bords compilés est nul. Les captures
natives montrent les vingt-deux tenues de face et de dos, cinq zones isolées,
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
- Les gants et manches du R-01 ainsi que les pièces de déplacement reprennent
  les vingt-trois familles. Les autres modèles d'armes conservent leurs textures
  propres.

Aperçus : [les vingt-deux tenues dans le jeu](../../docs/images/gign-personas-in-game.jpg) et
`build/gign-fitted-comparison.jpg`. Rapports :
`build/personas-verification.json` et
`build/personas-multiplayer-verification.json`.
