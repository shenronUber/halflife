# Cinq costumes supplémentaires

Ces cinq costumes utilisent la carte UV, les 740 triangles et les cinq zones du
GIGN existant. Les nouvelles pièces sont ajoutées après les objets historiques :
les identifiants précédents restent inchangés.

| Tenue | Direction retenue | Famille de texture |
| --- | --- | --- |
| [Red Son](red-son/texture-atlas.png) | Cosmonaute rétrofuturiste, combinaison ivoire et rouge, instrumentation de cosmodrome, sans casque | 14 |
| [Sélénite](selenite/texture-atlas.png) | Combinaison hermétique noir et blanc, visière transparente, circuit respiratoire lunaire enchevêtré et réservoirs arrondis sans inscriptions ; surfaces lisses sans poussière, peau et yeux de couleur naturelle | 15 |
| [Héros masqué](masked-hero/texture-atlas.png) | Costume bleu, rouge et or, masque bleu sans contour rouge, jointure de tête bleue, panneau dorsal sans abdominaux et emblème original sur le torse | 16 |
| [Pilote de rallye](rally-driver/texture-atlas.png) | Combinaison blanche, bleue et orange, harnais, damiers et lunettes ambrées | 17 |
| [Soldat pénitent](penitent-soldier/texture-atlas.png) | Armure blanche salie de marron, masque balistique intégral, une seule croix jaune allongée du front à la bouche, dos en plaques articulées | 18 |

Lancer `Jouer - Vector Fields.cmd`, ouvrir l'inventaire opérateur et choisir la
collection. Chaque tenue possède un masque, une veste, des gants, un pantalon et
des bottes ; les cinq pièces peuvent être équipées ensemble ou mélangées. Le
filtre opérateur inclut ces nouvelles collections. Les tenues existent aussi
dans Apparence libre, filtre GIGN, parmi les options développeur.

Les mains et manches à la première personne, les pièces de déplacement et les
corps après une mort utilisent les mêmes familles de textures. Les finitions des
armes restent indépendantes des costumes. Les nouvelles pièces ont les mêmes
coûts et la même famille de gameplay Baseline que la tenue d'intervention.

Les images originales haute résolution sont enregistrées dans les dossiers
`red-son`, `selenite`, `masked-hero`, `rally-driver` et `penitent-soldier`, sous le
nom `texture-atlas.png`. Elles ont été créées avec l'outil intégré **image_gen**.
Les prompts sont conservés avec les atlas : `prompt.txt` pour Red Son et Pilote
de rallye ; `cowl-and-back-prompt.txt` puis `head-join-prompt.txt` pour Héros masqué ; `lunar-circuit-prompt.txt`
pour Sélénite ; `final-prompt.txt` pour Soldat pénitent.
`generation.json` consigne les images retenues et leurs empreintes.

La bande courbe située en haut à droite du pantalon, autour du repère
x = 67 %, y = 4,7 % (origine en haut à gauche), appartient à la jointure de
la tête. Le petit rectangle à deux panneaux voisin appartient également à la
tête : les deux îlots ont été vérifiés dans les UV du modèle. Leur couleur doit
reprendre celle de la cagoule des deux côtés. Pour Héros masqué, ces deux îlots
sont bleus, y compris leurs bords ; ce ne sont pas des accessoires rouges.
La bande latérale entre la face et le bras (x = 77 %, y = 74 %) appartient
également à la tête ; elle reprend la couleur de la cagoule.

La compilation contrôle les trois raccords sur toutes les tenues GIGN et
harmonise automatiquement les écarts avec la cagoule, en préservant les
ombres. Les sources restent conservées ; les variantes compilées sont dans
`generated/personas/corrected-atlases`. Le détail des corrections est enregistré
dans `generated/personas/head-join-audit.json`.

La compilation réduit les textures à 512 × 512 pixels avec une palette de 256
couleurs. Les cadrans, capsules, plaques, lunettes et raccords sont peints dans
les UV existants ; ils ne créent pas de volume ou d'accessoire supplémentaire.

Validation : `python vector-fields/tests/new_personas_test.py --assets` contrôle
les 25 pièces, les cinq ensembles, les banques de textures et la conservation
des identifiants. Après déploiement, lancer le même test sans `--assets` pour
les captures face/dos, les mains, la sauvegarde et les fragments de corps.
Le rapport est `build/new-costumes-verification.json`.

![Les cinq tenues de face et de dos](../../docs/images/new-costumes-in-game.jpg)
