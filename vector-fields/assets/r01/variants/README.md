# Banques de textures du Relais R-01

Le [pack Cinq univers](../../EXPEDITIONS.md) ajoute cinq banques assorties aux
personnages GIGN : Grande Guerre, Bedrock, New York noir, Bois de naufrage
et Abysses. Le total actuel est de onze atlas créés, soit douze finitions
avec l’originale, sur les 26 pièces et trois rigs du R1. Indices nouveaux :
7, 8, 9, 10 et 11 ; tous les anciens indices sont conservés.

Six nouvelles planches ont été créées avec l’outil intégré **image_gen**.
Le premier essai médiéval est conservé en plus de sa version alchimique.
L’atlas industriel original reste dans [../texture-atlas.png](../texture-atlas.png).

| Banque | Matières et conception | Planche |
| --- | --- | --- |
| Guerre et récupération | Acier noirci, peinture olive, réparations soudées | [war-torn](war-torn/texture-atlas.png) |
| Forge médiévale | Fer, bronze martelé, chêne, cuir et émail | [medieval-forge](medieval-forge/texture-atlas.png) |
| Préhistorique | Obsidienne, os, tendon, résine et pierre poreuse | [prehistoric](prehistoric/texture-atlas.png) |
| Jungle vivante | Carapace, bambou, sève, gousses, optique à facettes | [living-jungle](living-jungle/texture-atlas.png) |
| Alchimie médiévale | Cotte de mailles, vitrail, cristal, réservoirs alchimiques | [medieval-alchemy](medieval-alchemy/texture-atlas.png) |
| Porcelaine fluidique | Céramique, silicone, gels et canaux capillaires | [porcelain-fluidics](porcelain-fluidics/texture-atlas.png) |

[Aperçu des six planches](apercu-six-variantes.jpg) ·
[Comparaison d’une même fonction entre les six univers](comparaison-fonctions.jpg)

## Contenu de chaque banque

- `texture-atlas.png` : image complète 1254 × 1254, opaque, grille de 4 × 4.
- `tiles/r01_t00.png` à `r01_t15.png` : 16 textures RGB de 256 × 256.
- `tiles/r01_t00.bmp` à `r01_t15.bmp` : mêmes textures, palette de 256 couleurs au maximum, format attendu par StudioMDL.
- `prompt.txt` : prompt exact transmis à image_gen.
- `manifest.json` : dimensions, empreintes SHA-256, coordonnées de découpe et modèles utilisant chaque matière.

Les fichiers sont nommés exactement comme les matières de
`build_reference_weapon.py`. La découpe reproduit sa formule, y compris
la marge intérieure de 3 pixels. Il y a **96 textures fonctionnelles**,
chacune livrée en PNG et en BMP. Les prompts complets et la provenance
des six générations sont également archivés dans `variants.json`.

## Correspondance des cases

Indices à partir de zéro ; lecture de gauche à droite, puis de haut en bas.
Les noms de modèles réellement concernés sont listés dans chaque manifeste,
d’après les géométries A et B du constructeur R-01.

| Fichier | Ligne / colonne | Rôle dans le R-01 |
| --- | --- | --- |
| r01_t00 | 1 / 1 | Structure sombre, corps des modules |
| r01_t01 | 1 / 2 | Carter / panneau latéral du châssis et de la crosse |
| r01_t02 | 1 / 3 | Habillage du châssis A, réserves et petits berceaux |
| r01_t03 | 1 / 4 | Marquage et habillage du châssis B |
| r01_t04 | 2 / 1 | Poignée, amortissement, colliers d’optique et sabot |
| r01_t05 | 2 / 2 | Bagues, contacts, vis, pièces dures et ailettes |
| r01_t06 | 2 / 3 | Surface ajourée du canon et du châssis |
| r01_t07 | 2 / 4 | Conduction, bobines, conduites et éléments de cartouches |
| r01_t08 | 3 / 1 | Face de la réserve d’énergie A |
| r01_t09 | 3 / 2 | Réserve B, cellules de cassette et ampoules |
| r01_t10 | 3 / 3 | Indicateur sur les modules d’énergie |
| r01_t11 | 3 / 4 | Verre / surface de l’optique A et B |
| r01_t12 | 4 / 1 | Signal de sécurité ; réservé, absent des géométries actuelles |
| r01_t13 | 4 / 2 | Isolation du canon, du refroidissement et du tube auxiliaire |
| r01_t14 | 4 / 3 | Faces du chargeur animé A et B |
| r01_t15 | 4 / 4 | Face de la culasse animée A et B |

Une texture peut servir à plusieurs pièces. Par exemple, r01_t05 habille
aussi bien des bagues que des vis : changer sa matière change tous ces
éléments. Les formes inhabituelles sont peintes sur les surfaces ; les
silhouettes 3D et les animations restent celles des modèles auxquels on
applique la banque. Une nouvelle silhouette en gousse ou en os demande
un nouveau maillage, même si la texture en donne déjà le langage visuel.
Les effets lumineux, la transparence et les jauges restent des motifs
dans les textures diffuses, sans shader ni animation ajoutés.

## Composer rapidement un jeu de matières

Réexporter les six banques depuis les planches archivées :

```powershell
python vector-fields/build_r01_texture_variants.py
```

Créer un jeu industriel avec une optique jungle et un chargeur préhistorique :

```powershell
python vector-fields/build_r01_texture_variants.py --theme war-torn --tile 11=living-jungle --tile 14=prehistoric --output vector-fields/generated/r01_texture_variants/mon-melange
```

`--tile` peut être répété pour n’importe quel indice de 0 à 15. Le thème
`original` est également accepté, comme base ou pour une seule case.
La destination doit être vide : le script ne remplace pas une banque
existante. `selection.json` conserve les choix du mélange.

Un exemple prêt à examiner est dans
`vector-fields/generated/r01_texture_variants/mix-demo`.

Les MDL GoldSrc embarquent leurs textures. Pour voir un jeu de matières
dans le moteur, utiliser ses BMP lors de la compilation des pièces R-01,
ou importer ces textures dans une copie du MDL. Remplacer seulement les
BMP sur disque après compilation ne change pas un MDL déjà produit.
La première livraison conservait les modèles actifs ; les finitions sont maintenant embarquées dans les pièces R-01 (voir ci-dessous).

## Vérification

Les six planches ont été inspectées visuellement. Les 96 exports BMP ont
été contrôlés : 256 × 256, mode indexé, palette d’au plus 256 couleurs.
Les mêmes indices et la même découpe sont utilisés dans toutes les banques.
Le manifeste racine archive la correspondance aux 24 pièces A/B du R-01.
Le mélange de démonstration vérifie la substitution d’une optique et d’un
chargeur sans changer les 14 autres matières.

## Finitions interchangeables dans le jeu

Les six nouvelles banques sont désormais intégrées au R-01, en plus de
l’originale : **sept familles de textures dans chacun des 24 modèles de
pièces**, avec un seul maillage par forme A/B. Le rig et les animations sont
partagés. Une finition ne crée aucun fichier MDL supplémentaire.

Lancer Jouer - Vector Fields.cmd, ou ouvrir le R-01 avec **F11**.
Dans le panneau droit, sous les deux formes disponibles :

1. Choisir **Toute l’arme** ou **Cette pièce**.
2. Utiliser les flèches de **FINITION** pour parcourir les sept styles.
3. Inspecter l’aperçu, puis choisir **Appliquer**.
4. **Annuler** restaure les formes et les finitions précédemment validées.

Chaque emplacement conserve sa propre finition en passant d’une forme
A à B. On peut ainsi utiliser une optique jungle sur un châssis en
porcelaine avec un chargeur préhistorique. Le choix est validé avec
l’équipement dans une seule transaction serveur, enregistré dans les
sauvegardes, et transmis aux autres clients, y compris à leur arrivée tardive.

Les nouvelles finitions sont visibles dans l’atelier et en première
personne. L’arme portée en troisième personne conserve encore le modèle
stock ; la transmission des choix prépare son remplacement ultérieur.

### Ajouter une nouvelle banque

1. Créer assets/r01/variants/<identifiant>/texture-atlas.png, avec la même
   grille fonctionnelle 4 × 4.
2. Ajouter à la fin de variants.json une entrée comprenant au minimum
   id et title. Conserver l’ordre des styles existants.
3. Exécuter ./vector-fields/build.ps1, puis
   python vector-fields/play.py --visual-lab --deploy-only.
4. Relancer le jeu : le catalogue et les nouvelles familles seront disponibles.

Le build détecte un changement d’atlas, de catalogue ou de constructeur.
Il découpe la nouvelle planche, génère les familles natives $texturegroup,
recompile les 24 pièces et produit data/r01_styles.txt. Aucune nouvelle
branche C++ ni copie de géométrie n’est nécessaire pour un style.
Le réseau vérifie l’empreinte du catalogue ; les anciennes sauvegardes
reviennent à l’original si le catalogue a changé, plutôt que de
réinterpréter un ancien indice.

Les textures consomment toujours de l’espace et de la mémoire ; la
géométrie et les animations restent communes. StudioMDL limite chaque
modèle à 100 textures embarquées, et le constructeur signale le dépassement.
Une silhouette différente demande une nouvelle forme de pièce : une image
de gousse sur un chargeur droit conserve la silhouette du chargeur droit.

Les BMP sur disque sont des sources de compilation. Pendant la partie,
le changement utilise directement l’indice de famille déjà chargé dans
le MDL. Un nouvel atlas demande une reconstruction et un redémarrage,
tandis que passer entre les styles installés est immédiat.

### Commandes et contrôles

vf_reference_style <indice> change le brouillon de toute l’arme ;
vf_reference_style <indice> <emplacement> change seulement une pièce
(emplacements 9 à 20). vf_commit valide l’ensemble.
Indices actuels : 0 original, 1 guerre, 2 forge, 3 préhistoire, 4 jungle,
5 alchimie, 6 porcelaine.

Les contrôles sont dans tests/r01_styles_engine_test.py et
tests/r01_styles_multiplayer_test.py. Ils couvrent les 168 couples
forme/finition, les changements visuels dans le vrai moteur, les commandes
de l’interface, l’annulation, la validation atomique, la sauvegarde, le
rechargement de l’arme et l’arrivée d’un second client. La régression R-01
existante couvre également les 4096 assemblages A/B.


### Mapping des surfaces du R-01

Le mapping isotrope couvre désormais les 24 modules : corps du châssis,
capot supérieur, plaques latérales, culasse, canon, tubes, chargeur,
poignée et crosse. Une texture carrée conserve la même échelle physique
sur ses deux axes, y compris sur les chanfreins. Les longues surfaces
sont découpées en cellules UV répétées ; les coordonnées restent entre
0 et 1 afin d'éviter l'agrandissement des textures par StudioMDL.

Les matériaux de fond ont une taille de motif réglée par matériau dans
TILE_SIZE. Les panneaux fonctionnels répètent leurs motifs dans le sens
long ; le résidu est recadré sans déformation. Les panneaux d'identité,
de batterie et de statut gardent un seul motif central, également recadré
sans étirement. Le chargeur tient compte de sa rotation verticale.
Toutes les répétitions conservent leur orientation : aucun effet miroir
alterné. La fenêtre UV de l'optique existante reste conservée.

Les surfaces sources et la silhouette restent identiques. Seule leur
subdivision et leur mapping changent ; les familles de textures et les
animations restent communes. La subdivision augmente légèrement le
nombre de triangles. Le compilateur fusionne les sommets avec sa
précision habituelle : les tests exigent des bornes identiques et moins
de 0,1 % d'écart d'aire dans les MDL compilés.

Contrôles : tests/r01_uv_mapping_test.py (24 modules, échelle UV,
orientation, conservation des surfaces et 42 vues natives des deux
châssis dans les sept styles), puis tests/r01_styles_engine_test.py
(changement de finition, équipement, tir, rechargement et sauvegarde).
La référence des surfaces est conservée dans tests/fixtures.

[Comparaison avant/après du châssis](../../../build/r01-receiver-uv-comparison.jpg)
et [nouvelle planche des armes complètes](../../../build/r01-styles-in-game.jpg).
Les fichiers corrigés sont déployés. Relancer le jeu charge les nouveaux
modèles lorsqu'une session utilise encore les anciens modèles en cache.
