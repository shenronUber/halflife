# Matériaux des casques

Sources conservées dans le projet, générées avec l'outil intégré `image_gen` :

- [Anti-émeute](riot-materials.png) : composite bleu ardoise, acier usiné,
  tissu/caoutchouc noir et panneaux de ventilation.
- [Spartiate](spartan-materials.png) : bronze martelé patiné, gravures,
  bronze poli aux rebords et crins bordeaux.
- [Prompts exacts](prompts.json).
- [Optiques et matériaux instrumentaux](optics-materials.png) : objectifs
  rouges et verts, métal graphite et coque rouge sombre.
- [Prompt exact des optiques](optics-prompt.txt).
- [Casque blindé et masque à gaz](ballistic-gas-materials.png) : peinture noire
  granuleuse, caoutchouc moulé, grille métallique du filtre et enveloppe à
  bandes vertes/jaunes discrètes.
- [Prompt exact du casque blindé et du masque](ballistic-gas-prompt.txt).
- Références fournies par l'utilisateur : [casque](references/ballistic-user.png)
  et [masque à gaz](references/gas-mask-user.png). Elles guident la géométrie
  et les matériaux ; elles ne sont pas utilisées comme textures du visage.
- [Provenance et empreintes](provenance.json).

Les quatre quadrants de chaque planche deviennent des matériaux diffus
indexés de 256 × 256 pixels dans le MDL. Le build recadre les limites des
quadrants et réduit les couleurs pour GoldSrc. Il assombrit la variante de
crins utilisée aux tranches des faisceaux. Le verre additif est un petit matériau technique
distinct ; les coques et les fixations restent opaques.

Les designs éditables sont dans `headgear_designs.py` et
`headgear_extra_designs.py`, et les primitives dans
`headgear_geometry.py` : rebords roulés,
plaques biseautées, rivets circulaires, charnières, rails et faisceaux du
cimier, pièces du respirateur et sangles sont des volumes du modèle. Les
poses relevées conservent la géométrie et les matériaux des pièces portées.
Les cagoules existantes ne sont pas peintes
dans ces planches et conservent leurs couleurs et leur personnalité.

Les originaux générés sont conservés sous le répertoire Codex
`generated_images/01a1279f-0717-7710-bb3e-171ecbb87a65/`. Le jeu et le build
utilisent exclusivement les copies présentes ici.
