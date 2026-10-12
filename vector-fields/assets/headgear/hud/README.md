# Textures de vision des équipements

Les cinq PNG originaux RGBA dans `sources/` sont des peintures créées avec l'outil intégré ImageGen. Le jeu utilise ces images préalablement créées, comme les textures des effets de statut. Les prompts complets et leur mode de création sont conservés dans [prompts.json](prompts.json).

- `riot.png` : verre bleuté, charnières et joint de visière.
- `ballistic.png` : plaques opaques et ouverture horizontale étroite.
- `gas_mask.png` : joint en caoutchouc, verre panoramique et valve.
- `red_optics.png` : trois modules et bordure optique rouge.
- `green_optics.png` : œilletons et contours binoculaires verts.

`build_headgear_hud.py` conserve les originaux et adapte uniquement leur résolution à 1024 × 576, dans la limite du chargeur de sprites, avant de les encoder en sprites natifs Version 32. Les canaux RGBA restent identiques entre le PNG adapté dans `frames/` et le sprite : transparence réelle, plaques opaques, reflets translucides et centre de visée libre.

Le runtime charge `sprites/vf_headgear_hud/<id>.spr`. Il fait varier uniquement l'opacité pendant le geste avec H. Les formes, joints et reflets viennent entièrement des textures. Aucune génération d'image ni requête réseau n'a lieu au lancement.

Pour remplacer une apparence, modifier son PNG source, puis exécuter :

```powershell
python vector-fields/build_headgear_hud.py
```

Le catalogue et le manifeste sont régénérés hors ligne. Les futures apparences peuvent suivre cette même filière, indépendamment du modèle 3D et des voix.
