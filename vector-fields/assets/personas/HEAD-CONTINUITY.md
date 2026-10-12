# Continuité des têtes

Les vingt-deux skins personnalisés ont été retouchés séparément avec le mode
intégré **image_gen**. Chaque sous-dossier contient :

- `head-continuity-reference.png` : copie immuable de l'atlas approuvé.
- `head-continuity-prompt.txt` : prompt de la retouche initiale ; Red Son et
  Porcelaine ont une révision finale dans `head-continuity-colour-prompt.txt`.
- `head-continuity.png` : résultat original de l'outil intégré, conservé dans le projet.

Le registre [head-continuity-generation.json](head-continuity-generation.json)
donne les vingt-deux chemins, prompts, références et empreintes SHA-256.
Les atlas historiques `texture-atlas.png` restent conservés. Le constructeur
sélectionne uniquement les îlots arrière, latéral et supérieur de la nouvelle
couche, en gardant le visage, le col et les vêtements de l'atlas approuvé.
La partie basse de l'îlot arrière, qui appartient au col, est également conservée.

La correspondance des arêtes 3D et de leurs échantillons filtrés assure ensuite
la continuité de couleur et d'ombre. Elle s'applique aux vingt-trois familles,
GIGN original compris, et aux matières des corps et fragments. Les mêmes UV,
la même géométrie et les mêmes identifiants de skin sont conservés.

- [Explication et validation](../../docs/HEAD-SEAMS.md)
- [Comparaison native avant / après](../../docs/images/head-folds-before-after.jpg)
- [Audit de compilation](../../generated/personas/head-join-audit.json)
- [Contrôle natif de toutes les têtes](../../docs/validation/head-seams.json)

<!-- head-layer-index -->

| Skin | Texture de tête | Prompt final |
| --- | --- | --- |
| Recuperateur des ruines | [head-continuity.png](war-torn\head-continuity.png) | [prompt](war-torn\head-continuity-prompt.txt) |
| Sentinelle de la forge | [head-continuity.png](medieval-forge\head-continuity.png) | [prompt](medieval-forge\head-continuity-prompt.txt) |
| Gardien d'os et de silex | [head-continuity.png](prehistoric\head-continuity.png) | [prompt](prehistoric\head-continuity-prompt.txt) |
| Veilleur de la canopee | [head-continuity.png](living-jungle\head-continuity.png) | [prompt](living-jungle\head-continuity-prompt.txt) |
| Veilleur alchimiste | [head-continuity.png](medieval-alchemy\head-continuity.png) | [prompt](medieval-alchemy\head-continuity-prompt.txt) |
| Operateur de porcelaine | [head-continuity.png](porcelain-fluidics\head-continuity.png) | [prompt](porcelain-fluidics\head-continuity-colour-prompt.txt) |
| Sentinelle des tranchees | [head-continuity.png](ww1-trench\head-continuity.png) | [prompt](ww1-trench\head-continuity-prompt.txt) |
| Mineur des profondeurs | [head-continuity.png](bedrock-miner\head-continuity.png) | [prompt](bedrock-miner\head-continuity-prompt.txt) |
| Detective de minuit | [head-continuity.png](new-york-noir\head-continuity.png) | [prompt](new-york-noir\head-continuity-prompt.txt) |
| Naufrage des rivages | [head-continuity.png](castaway\head-continuity.png) | [prompt](castaway\head-continuity-prompt.txt) |
| Plongeur des abysses | [head-continuity.png](abyss-diver\head-continuity.png) | [prompt](abyss-diver\head-continuity-prompt.txt) |
| Artisan de la Renaissance | [head-continuity.png](roman-inventor\head-continuity.png) | [prompt](roman-inventor\head-continuity-prompt.txt) |
| Mecanicien diesel | [head-continuity.png](dieselpunk\head-continuity.png) | [prompt](dieselpunk\head-continuity-prompt.txt) |
| Red Son | [head-continuity.png](red-son\head-continuity.png) | [prompt](red-son\head-continuity-colour-prompt.txt) |
| Selenite | [head-continuity.png](selenite\head-continuity.png) | [prompt](selenite\head-continuity-prompt.txt) |
| Heros masque | [head-continuity.png](masked-hero\head-continuity.png) | [prompt](masked-hero\head-continuity-prompt.txt) |
| Pilote de rallye | [head-continuity.png](rally-driver\head-continuity.png) | [prompt](rally-driver\head-continuity-prompt.txt) |
| Soldat penitent | [head-continuity.png](penitent-soldier\head-continuity.png) | [prompt](penitent-soldier\head-continuity-prompt.txt) |
| Operateur de jade | [head-continuity.png](jade-symbiosis\head-continuity.png) | [prompt](jade-symbiosis\head-continuity-prompt.txt) |
| Operateur d'ambre | [head-continuity.png](amber-culture\head-continuity.png) | [prompt](amber-culture\head-continuity-prompt.txt) |
| Savage Butcher | [head-continuity.png](savage-butcher\head-continuity.png) | [prompt](savage-butcher\head-continuity-prompt.txt) |
| Miami Vice | [head-continuity.png](miami-vice\head-continuity.png) | [prompt](miami-vice\head-continuity-prompt.txt) |
