# Quatre tenues et leurs signatures

Ces ensembles prolongent l'idée de l'Opérateur de porcelaine avec des matières
nobles intégrées à des vêtements techniques. Les biofluides restent contenus
dans de petits circuits et modules scellés. Les deux tenues conservent les UV,
la silhouette GIGN et des yeux humains avec leur couleur de peau naturelle.

## Opérateur de jade

Textiles anthracite et olive, inserts fonctionnels de composite jade céladon,
plaques minérales réparées par des joints ivoire et circuit fluidique scellé.
Le torse porte les plaques réparées, le dos leur réservoir ; les gants ont des
ports d'injection et le pantalon un étui de plaquettes de rechange. Ce gimmick
d'autoréparation reste un dessin d'équipement technique. Un œil humain reste visible ;
un oculaire d'inspection externe couvre l'autre. Le masque de réparation
porte un insert de jade réparé et une petite fenêtre de contrôle. La coiffe
et ses trois raccords utilisent le même textile olive sombre.

- Atlas final : [jade-symbiosis/texture-atlas.png](jade-symbiosis/texture-atlas.png).
- Prompts : [base techwear](jade-symbiosis/techwear-prompt.txt), [équipement](jade-symbiosis/gimmick-prompt.txt), [masque final](jade-symbiosis/face-personality-prompt.txt).
- Références d'édition : [base approuvée](jade-symbiosis/techwear-reference.png), [équipement approuvé](jade-symbiosis/gimmick-reference.png).
- Collection `jade-symbiosis`, finition `jade_symbiosis`, cinq pièces équipables.

## Opérateur d'ambre

Textiles gris ardoise et taupe, protections compactes en céramique ivoire,
boîtiers de filtration en résine d'ambre fumé. De petites cartouches et des
circuits fluidiques discrets forment un laboratoire de terrain : cassette de
prélèvements sur le torse, centrifugeuse compacte au dos, bracelet d'analyse
sur les gants et tubes protégés dans un étui de cuisse. Une visière d'analyse
ambrée laisse voir les yeux humains et leur peau naturelle à travers le verre.
Le masque de laboratoire porte une cage filtrante ivoire et des cartouches compactes.
La coiffe et ses raccords restent gris sombre.

- Atlas final : [amber-culture/texture-atlas.png](amber-culture/texture-atlas.png).
- Prompts : [base techwear](amber-culture/techwear-prompt.txt), [équipement](amber-culture/gimmick-prompt.txt), [masque final](amber-culture/face-personality-prompt.txt).
- Références d'édition : [base approuvée](amber-culture/techwear-reference.png), [équipement approuvé](amber-culture/gimmick-reference.png).
- Collection `amber-culture`, finition `amber_culture`, cinq pièces équipables.

## Savage Butcher

Tablier de boucher ivoire, sali de brun et taché de sang, sur des vêtements
de travail anthracite et un harnais balistique. Le tablier court s'arrête à la taille ;
le pantalon garde deux jambes distinctes. Le dos porte les bretelles croisées
et les attaches de travail. Les gants épais sont maculés de sang. Un masque
intégral ivoire usé couvre la face, les côtés et l'arrière de la tête ; seuls
les yeux humains restent visibles par deux ouvertures.
Le sang est peint sur les vêtements.

- Atlas final : [savage-butcher/texture-atlas.png](savage-butcher/texture-atlas.png).
- Prompts : [base](savage-butcher/prompt.txt), [pantalon et masque intégral](savage-butcher/legs-and-integral-mask-prompt.txt), [ouvertures des yeux et raccord](savage-butcher/eye-apertures-prompt.txt).
- Collection `savage-butcher`, finition `savage_butcher`, cinq pièces équipables.

## Miami Vice

Veste et pantalon de costume bleus, chemise rose, gilet pare-balles bleu nuit
porté par-dessus. Le relief du cou devient un col de chemise rose, raccordé
sur les morceaux avant, arrière et supérieurs du torse. Les trois bandes UV
des manches alternent leur orientation : poignets à droite, à gauche, à droite.
Le rose reste aux vrais poignets et les épaules sont bleues. Les gants restent
en cuir sombre. La tête garde une cagoule bleu nuit, avec des lunettes aviateur
à monture dorée sur les yeux d'origine. Le dos conserve la coupe du costume
et le panneau dorsal du gilet.
L'export de cette tenue utilise une palette octree : les petits détails dorés
gardent leur teinte dans les 256 couleurs du moteur.

- Atlas final : [miami-vice/texture-atlas.png](miami-vice/texture-atlas.png).
- Prompts : [base](miami-vice/prompt.txt), [col et orientation des manches](miami-vice/collar-and-sleeves-prompt.txt).
- Référence avant correction : [miami-vice/collar-and-sleeves-reference.png](miami-vice/collar-and-sleeves-reference.png).
- Collection `miami-vice`, finition `miami_vice`, cinq pièces équipables.

## Jouer et vérifier

Lancer `Jouer - Vector Fields.cmd`, ouvrir l'inventaire opérateur, puis choisir
les collections **Operateur de jade**, **Operateur d'ambre**, **Savage Butcher**
et **Miami Vice**. Les cinq
pièces sont masque, veste, gants, pantalon et bottes ; elles peuvent également
être mélangées avec les autres tenues. Les collections sont cosmétiques et
conservent la famille de jeu Baseline.

Les atlas ont été créés avec l'outil intégré **image_gen**, à partir de
`reference-uv.png`. Les PNG retenus, les prompts et la provenance sont conservés
dans le projet ; `generation.json` enregistre leurs empreintes.
Le constructeur contrôle automatiquement les trois îlots de raccord de la tête.
Il ajoute une marge de protection contre la fuite du fond gris aux bords des UV
et conserve les coordonnées de texels après compilation, pour toutes les tenues.
Les gants et manches du R-01, les pièces de déplacement et les corps utilisent
les nouvelles finitions. Les matières nobles, les textiles et les petits
circuits fluidiques sont peints dans la texture diffuse, selon les possibilités
du moteur existant.

[Comparaison native de face et de dos avec la porcelaine](../../docs/images/artisan-sets-in-game.jpg).
[Les quatre masques sous quatre angles](../../docs/images/artisan-heads-in-game.jpg).

```powershell
./vector-fields/build.ps1
python vector-fields/play.py --visual-lab --deploy-only
python vector-fields/tests/artisan_sets_test.py
python vector-fields/tests/artisan_sets_test.py --heads
```

Le test vérifie les vingt pièces et les identifiants historiques, l'équipement
complet dans le jeu, les vues de face, de dos et à la première personne,
les filtres de collection par l'interface, un assemblage sauvegardé puis
rechargé, et la réception des finitions mixtes sur les fragments de corps.
Les gros plans natifs contrôlent les quatre nouvelles têtes sous quatre angles.
Les 23 familles donnent 529 combinaisons de finitions pour les fragments.
Les champs réseau de texture signés utilisent 11 bits pour transmettre aussi
l'indice maximal 528.
