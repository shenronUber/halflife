# Banques de textures du Relais R-01

Le R-01 propose **14 finitions sur 60 pièces** : l’atlas industriel original
et treize banques générées avec l’outil intégré **image_gen**. Les finitions
utilisent les mêmes géométries, points de fixation et animations.

| Indice | Banque | Matières principales |
| --- | --- | --- |
| 0 | [Original](../texture-atlas.png) | Acier, peinture ocre, cuivre |
| 1 | [Guerre](war-torn/texture-atlas.png) | Acier noirci, peinture olive, soudures |
| 2 | [Forge médiévale](medieval-forge/texture-atlas.png) | Fer, bronze, chêne, cuir |
| 3 | [Préhistorique](prehistoric/texture-atlas.png) | Obsidienne, os, tendon, résine |
| 4 | [Jungle vivante](living-jungle/texture-atlas.png) | Carapace, bambou, sève, gousses |
| 5 | [Alchimie médiévale](medieval-alchemy/texture-atlas.png) | Mailles, vitrail, cristal |
| 6 | [Porcelaine fluidique](porcelain-fluidics/texture-atlas.png) | Céramique, silicone, gels |
| 7 | [Grande Guerre](ww1-trench/texture-atlas.png) | Acier de tranchée, bois, toile |
| 8 | [Bedrock](bedrock-miner/texture-atlas.png) | Basalte, cuivre, acier, ocre |
| 9 | [New York noir](new-york-noir/texture-atlas.png) | Métal poli, cuir, noyer sombre |
| 10 | [Bois de naufrage](castaway/texture-atlas.png) | Bois flotté, fibres, silex |
| 11 | [Abysses](abyss-diver/texture-atlas.png) | Néoprène, laiton, verre marin |
| 12 | [Rome / Atelier d’inventeur](roman-inventor/texture-atlas.png) | Bois, cordages, toile dessinée, bronze, ivoire |
| 13 | [Dieselpunk](dieselpunk/texture-atlas.png) | Carrosserie nervurée, fonte, bakélite, huile, cadrans |

[Aperçu des treize banques](apercu-toutes-variantes.jpg).
Les deux nouvelles collections sont réservées aux armes ; les douze ensembles
opérateur existants ne changent pas. Les premières propositions, plus proches
du calque industriel, sont archivées dans les deux dossiers sous
`texture-atlas-v1.png` et `prompt-v1.txt`. Les fichiers sans suffixe contiennent
la révision retenue, aux matières et mécanismes plus distinctifs.

## Utilisation en jeu

**F11 → FINITION → Toute l’arme / Cette pièce → flèches → Appliquer**.
Annuler restaure les formes et les finitions validées. Une finition reste
attachée à son emplacement lors d’un changement de forme. Les choix sont
validés ensemble par le serveur, transmis aux clients et sauvegardés avec
leurs identifiants stables. Ils apparaissent dans l’atelier et en première
personne ; le modèle porté en troisième personne reste celui du jeu de base.

`vf_reference_style 12` sélectionne Rome sur toute l’arme ;
`vf_reference_style 13 16` applique Dieselpunk à l’optique seulement.
`vf_commit` valide le brouillon. Les emplacements d’arme vont de 9 à 20.

## Contrat des matières

Chaque atlas opaque possède une grille **4 × 4**. La découpe utilise une marge
intérieure de 3 pixels et produit seize PNG RGB et seize BMP indexés de
256 × 256 pixels, avec au plus 256 couleurs par BMP. Les dimensions exactes,
les SHA-256, les limites de découpe et les modèles utilisateurs figurent dans
les `manifest.json`. Les treize banques représentent **208 matières**.
Les prompts exacts sont dans chaque `prompt.txt` ; `variants.json` conserve
la provenance et l’ordre des styles.

| Case | Fonction |
| --- | --- |
| 00 | Structure |
| 01 | Carter amovible |
| 02 | Habillage / matière de coque |
| 03 | Identité / panneau décoratif |
| 04 | Prise en main |
| 05 | Contacts, bagues, pièces dures |
| 06 | Refroidissement |
| 07 | Conduction / enroulement |
| 08 | Réserve d’énergie A |
| 09 | Réserve d’énergie B |
| 10 | Indicateur d’état |
| 11 | Surface optique |
| 12 | Signal de sécurité, actuellement réservé |
| 13 | Isolation |
| 14 | Chargeur |
| 15 | Culasse / verrou |

Ces fonctions n’imposent ni les mêmes vis, ni les mêmes panneaux, ni les mêmes
découpes dessinées. Une bobine peut devenir une poulie à cordes, un indicateur
un cadran, un carter de la toile sur nervures. Les matières de fond 00, 02 et
05 doivent supporter leur répétition sur les surfaces courbes et longues.
Les textures restent diffuses : les engrenages, fluides, aiguilles et reliefs
peints ne constituent pas des mécanismes animés ou une nouvelle silhouette.

Les UV isotropes conservent l’échelle dans les deux directions. Les surfaces
longues sont subdivisées en cellules, avec coordonnées entre 0 et 1 ; les
panneaux particuliers sont recadrés sans étirement. La fenêtre optique
centrale est conservée. Gyre emploie la case 02 sur son noyau cylindrique et
réserve la case 03 à une seule petite plaque supérieure, pour ne pas répéter
les dessins ou cadrans autour du cylindre.

## Reconstruction et mélange

```powershell
python vector-fields/build_r01_texture_variants.py
./vector-fields/build.ps1
python vector-fields/play.py --visual-lab --deploy-only
```

L’exporteur met à jour les banques, manifestes et planches de comparaison.
Le constructeur recompilé embarque les finitions dans les familles natives
`$texturegroup` de chaque MDL. Modifier seulement un BMP après compilation
ne modifie pas le jeu. Le changement entre styles installés est immédiat ;
un nouvel atlas nécessite compilation, déploiement et redémarrage du jeu.

Pour exporter une banque mélangée dans un dossier vide :

```powershell
python vector-fields/build_r01_texture_variants.py --theme roman-inventor --tile 11=dieselpunk --output vector-fields/generated/r01_texture_variants/mon-melange
```

`--tile` accepte les indices 0 à 15, plusieurs fois, ainsi que `original`.
Le fichier `selection.json` archive les choix. Ce mélange exporté ne s’ajoute
pas automatiquement aux finitions installées.

Pour ajouter un style, créer son dossier et son atlas, puis ajouter une entrée
complète à la fin de `variants.json` sans réordonner les identifiants existants.
Déclarer sa collection dans `data/gameplay-content.json` :
`weapon_collections` suffit pour une finition réservée aux armes. Réexporter,
compiler et déployer. Les sauvegardes actuelles utilisent les identifiants
stables ; les anciennes sauvegardes connues passent par le catalogue historique
de migration. Une finition inconnue revient à l’originale.

StudioMDL limite chaque modèle à 100 textures. Avec quatorze finitions et au
plus six matières différentes par pièce, les modèles actuels atteignent au
maximum 84 textures. L’ajout de finitions reste donc limité par ce format.

## Vérification

`build.ps1` contrôle le catalogue, les extensions et les châssis.
`tests/r01_styles_engine_test.py` contrôle les 840 couples pièce/finition,
la géométrie partagée, l’interface, les transactions et la sauvegarde.
`tests/reference_chassis_test.py` contrôle les UV et la plaque de Gyre.
Les captures de la nouvelle série et les résultats natifs sont conservés dans
`build/r01-inventor-finishes-in-game.jpg` et
`build/inventor-finishes-verification.json`.
