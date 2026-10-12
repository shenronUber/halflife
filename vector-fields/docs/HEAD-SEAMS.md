# Raccords des têtes GIGN

Les lignes claires sur les côtés des cagoules provenaient de deux effets :

- L'export envoyait les coordonnées normalisées du MDL directement à
  StudioMDL. Celui-ci les convertit avec `dimension - 1` et tronque en entier :
  2 208 des 2 220 sommets exportés lisaient le texel situé un pixel à gauche.
- Le fond gris de l'atlas se trouvait immédiatement autour des îlots. Le
  filtrage mélangeait ces texels avec ceux de la cagoule, dessinant une ligne
  claire exactement sur la jonction entre face, côtés et arrière.

Les arêtes se rejoignent dans la géométrie. Les normales de leurs sommets
concordent ; leur produit scalaire compilé est supérieur à 0,9999999.

L'export des matières du personnage, des corps et des fragments inverse
désormais la conversion de StudioMDL. Le contrôle des 2 220 coordonnées
compilées les compare aux texels du GIGN donneur, en tenant compte du
recadrage effectué par le compilateur.

Les six îlots de tête et de cou reçoivent également une marge extérieure de
trois texels. Un bord intérieur étroit reprend les couleurs de sa propre
matière avant cette extrusion : deux texels en général, trois pour l'arrière
de la cagoule et quatre pour sa bande latérale. Les îlots voisins sont protégés.
Les yeux et les détails intérieurs des masques conservent leur texture source.
Les atlas haute résolution ne sont pas redessinés par ce traitement.

Le col rose de Miami Vice reste explicitement une matière de chemise ; les
deux véritables raccords de la tête restent bleu nuit. Les poignets roses sont
placés aux extrémités anatomiques des trois bandes de manches, qui alternent
droite, gauche et droite sur l'atlas.

Les vingt-deux tenues personnalisées disposent maintenant d'une couche
`head-continuity.png`, retouchée avec l'outil intégré **image_gen** depuis leur
atlas approuvé. La sélection géométrique reprend uniquement l'arrière de la
tête, la bande latérale et le sommet. Le visage, les accessoires du masque,
le col et les vêtements sont repris dans les textures approuvées. Les couches,
les références et les prompts exacts sont conservés dans chaque dossier ;
leur provenance figure dans
[head-continuity-generation.json](../assets/personas/head-continuity-generation.json).

`persona_head_continuity.py` relie ensuite les vingt arêtes découpées entre les
quatre îlots de tête. Un ajustement sur une bande de dix texels fait concorder
les couleurs réellement filtrées et leur variation d'ombre de part et d'autre
du raccord, en tenant compte des différences de densité UV. L'ajustement se
fond dans le dessin existant et conserve les détails au centre des îlots.
Les îlots voisins sont exclus, et la géométrie, les UV, les os et les animations
restent identiques. Le même traitement bénéficie au GIGN original.

La conversion en palette peut recréer un petit écart : quatre passes au maximum
améliorent les indices de couleur près des raccords, en gardant la palette et
les indices des vêtements exactement identiques. Le meilleur résultat mesuré
est retenu. L'audit consigne les écarts avant, après et après conversion indexée
pour chacune des vingt-trois familles. Les corps et les fragments utilisent
les mêmes matières corrigées.

Les différences de plis et la bande de raccord sont ainsi reprises, en plus
de la fuite du fond gris. Les bordures intentionnelles des masques, les motifs
décoratifs et la silhouette polygonale restent propres à chaque skin.

- [Avant / après, quatre tenues](images/head-seams-before-after.jpg)
- [Avant / après la reprise des plis](images/head-folds-before-after.jpg)
- [Miami Vice : col et manches dans le moteur](images/miami-collar-in-game.jpg)
- [Contrôle natif des 23 familles](validation/head-seams.json)
- [Audit des UV et des marges](../generated/personas/head-join-audit.json)
- [Atlas Miami révisé](../assets/personas/miami-vice/texture-atlas.png)
- [Prompt de cette révision, outil intégré image_gen](../assets/personas/miami-vice/collar-and-sleeves-prompt.txt)
- [Prompts et sources de la continuité des têtes](../assets/personas/HEAD-CONTINUITY.md)
