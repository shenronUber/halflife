# Atelier des gestes de déplacement

L'atelier **Blender** est désormais disponible pour corriger les mains avec des commandes lisibles et des poignées IK : double-cliquer sur **Animer dans Blender - Vector Fields.cmd**. Le projet du corps s'ouvre avec **Animer le corps dans Blender - Vector Fields.cmd**. Voir [le guide Blender](blender/LIRE-MOI.md). Les deux ateliers exportent vers les mêmes dossiers de retouches SMD, sans déploiement automatique au jeu.

fragMOTION 1.3.7 est installé dans `devtools/fragmotion/app` sur G:. Double-cliquer sur **Animer - Vector Fields.cmd** ouvre les mains ; **Animer le corps - Vector Fields.cmd** ouvre le personnage. Le fichier `atelier.smd` contient le modèle texturé et son animation de suspension. Les autres gestes sont fournis séparément. Les `.mdl` compilés servent aux contrôles du jeu, pas à File / Open dans fragMOTION. Le logiciel peut présenter ses propres conditions d'utilisation ou son dialogue de licence au premier démarrage ; ce dialogue se traite dans fragMOTION.

## Charger la géométrie et les textures

Dans **File / Open**, ouvrir `first-person/atelier.smd` pour les mains ou `third-person/atelier.smd` pour le corps. Ces fichiers réunissent squelette, mesh, UV et noms des BMP dans la pose de suspension ; si fragMOTION ne charge que Default Pose, fusionner la piste d’animation séparément avec File / Merge. Les textures BMP se trouvent dans le même dossier. **Textured (Shift+4)** affiche les textures ; **Show Skeleton (Alt+S)** affiche les os.

L’erreur **format not supported: IDST** apparaît lors de l’ouverture du MDL compilé. Le tutoriel Half-Life officiel passe par la décompilation, puis l’ouverture du SMD du mesh et **File / Merge** pour les animations. L’atelier fournit déjà ces SMD, donc aucune décompilation n’est nécessaire.

Pour commencer directement avec un autre geste et la géométrie visible, ouvrir `vf_climb_scene.smd`, `vf_drop_scene.smd` ou `vf_vault_scene.smd`. Les pistes `vf_..._0.smd` restent des animations seules à fusionner avec un modèle chargé. Pour un skin précis, consulter [la liste des mains](first-person/SKINS.md) ou [la liste du corps](third-person/SKINS.md) : chaque `atelier_skin_XX.smd` contient aussi le mesh et la suspension.

## Si le squelette semble décalé

Les scènes complètes utilisent leur première image comme pose de liaison du mesh. L’export corrige la géométrie pour qu’elle corresponde à cette image : il ne faut pas déplacer les mains manuellement pour compenser un ancien export décalé. Enregistrer les retouches éventuelles, puis rouvrir le `atelier.smd` régénéré. Les fichiers de référence restent en pose de référence et les animations seules sont prévues pour **File / Merge**.

## Sélectionner et plier un doigt dans fragMOTION

Si le panneau **Animations** ne montre que **Default Pose**, charger l’animation séparément : **File / Merge**, choisir `vf_hang_idle_0.smd`, puis confirmer l’import des clés sur le squelette portant les mêmes noms. Sélectionner cette animation et régler **FPS = 30**. L’ouverture d’un SMD avec mesh peut ne charger que sa pose de liaison.

1. Ouvrir l’onglet **Skeleton** et sélectionner l’os par son nom, par exemple **VFRight_Bone48** pour l’articulation de l’index droit.
2. Choisir l’image à modifier sur la barre de temps.
3. Dans le panneau **Tools**, remplacer la catégorie **Select** par **Skeletal Animation**, puis choisir **Rotate Key**. Avec ce mode, cliquer-glisser dans la vue autour de l’os sélectionné crée une clé de rotation.
4. Pour plus de précision, les propriétés **AngleX**, **AngleY** et **AngleZ**, puis **Rotate**, appliquent une rotation chiffrée. Garder **AffectChildren** activé pour que le bout du doigt suive.
5. Enregistrer le projet en `.arg`, puis exporter l’animation seule en SMD dans `retouches/first-person/vf_hang_idle_0.smd`.

**Select Bone** sélectionne l’os ; ce mode ne le déplace pas. **Translate Key** sert à déplacer un os dans une animation, mais les doigts doivent surtout être corrigés en rotation pour conserver leur longueur. Ne pas réassigner les sommets, supprimer les os auxiliaires ou utiliser Auto Assign pour régler une pose.

Les points de Bone08..Bone10 sont les os de l’ancienne prise d’arme. Dans le gant de déplacement corrigé, ils ne portent plus de sommets ; les vrais os du pouce droit sont **VFRight_Bone43..45**. Les repères d’arme et de manche restent dans le squelette pour la compatibilité. Les poseurs des mains et des doigts sont listés dans bones.csv.

[Tutoriel officiel : animer avec Rotate Key](https://fragmosoft.com/fragMOTION/Help/Tutorials/Animating.html).

## Identifier les os

![Repères des doigts](reperes-mains.png)

| Zone | Main gauche | Main droite |
| --- | --- | --- |
| Coude / avant-bras | Bone40 | Bone05 |
| Poignet / paume | Bone42 | Bone07 |
| Pouce | Bone43 → Bone44 → Bone45 | mêmes noms avec VFRight_ |
| Index | Bone47 → Bone48 → Bone49 → Bone50 | mêmes noms avec VFRight_ |
| Majeur | Bone51 → Bone52 → Bone53 → Bone54 | mêmes noms avec VFRight_ |
| Annulaire | Bone55 → Bone56 → Bone57 → Bone58 | mêmes noms avec VFRight_ |
| Auriculaire | Bone59 → Bone60 → Bone61 → Bone62 | mêmes noms avec VFRight_ |

Les chaînes vont de la base vers l’extrémité. Utiliser les noms des os, pas leur numéro de ligne dans le SMD. Les anciens Bone08..Bone10 ne sont pas les os du pouce droit ouvert. Les listes [bones.csv des mains](first-person/bones.csv) et [bones.csv du corps](third-person/bones.csv) donnent le rôle et le parent de chaque os. Conserver ces noms lors de l’export.

## Premier geste à corriger

1. Ouvrir **atelier.smd** et sélectionner son animation dans la liste **Animations**. Régler **FPS = 30** dans les propriétés pour la suspension : le SMD ne mémorise pas la cadence. Observer la main sur plusieurs vues, puis poser les doigts et les bras avec les outils d'animation. Les boutons exacts dépendront de la disposition de ton interface.
2. Garder les noms et les parents des os. Les doigts gauches sont **Bone43..Bone62** ; les doigts droits sont les os **VFRight_...**. Les poignets sont **Bone42** à gauche et **Bone07** à droite ; les avant-bras **Bone40** et **Bone05**. Les noms sont historiques : suivre le squelette affiché pour sélectionner l'os précis.
3. Enregistrer ton travail au format natif `.arg`, puis exporter **l'animation seule** au format **Half-Life SMD**. Pour la suspension à deux mains, exporter vers `retouches/first-person/vf_hang_idle_0.smd`. Les SMD de référence sont également fournis : File / Open `reference.smd`, puis **File / Merge** avec le SMD du geste, en faisant correspondre les os par nom.
4. Double-cliquer sur **Appliquer les animations - Vector Fields.cmd** : les exports sont validés, copiés dans les sources de retouche, recompilés et installés dans le jeu. Fermer le jeu avant d'appliquer. **F9** ouvre le parcours de déplacement.

Les fichiers `retouches/` et tes projets `.arg` ne sont pas remplacés par une régénération de l'atelier. Les retouches acceptées sont conservées dans `assets/animations/traversal-edits/`, en dehors des fichiers générés. Une nouvelle importation sauvegarde la précédente en `.smd.previous`.

## Gestes prioritaires

| Animation | Geste | Durée du jeu |
| --- | --- | --- |
| vf_hang_catch | Saisie à deux mains | 0,28 s |
| vf_hang_idle | Suspension stable | boucle de 1,2 s |
| vf_climb | Remontée depuis la suspension | 0,85 s |
| vf_drop | Lâcher, sans animation d'atterrissage | 0,30 s |
| vf_vault | Franchissement d'obstacle bas | 0,62 s |

Le suffixe `_0.smd` désigne la piste principale. Les poses de visée `vf_hang_aim_*` et `vf_hang_both_*` ont quatre pistes `_0..3` pour interpoler la caméra ; on peut les régler ensuite. Pour chaque vue, `gestures.json` indique les fichiers, le nombre d'images et les durées. Les deux vues sont éditées séparément.

Le contact des paumes en suspension est fixé par le moteur. Cela conserve la prise sur le rebord malgré la caméra : les poses des doigts restent celles de ton animation. Modifier les contacts de base dans `assets/animations/traversal.json` ne suffit donc pas à déplacer le contact final fixé par le moteur ; une modification de ce point nécessite aussi de modifier le rendu. Animer les rotations plutôt que la longueur des os. L'import refuse un squelette incompatible, des valeurs invalides ou un étirement des membres.

## Sources et périmètre

La posture suspendue et le début du lâcher utilisent **Freehang Drop** ; le mouvement du corps lors de la remontée est adapté de **Climbing To Top**. Les déplacements du personnage restent calculés par le code du jeu : on n'importe pas la trajectoire du squelette source. Le franchissement bas est dessiné sur nos propres rigs. Les autres clips téléchargés ont été examinés et écartés lorsqu'ils correspondaient à une autre action. Les références exactes et les empreintes des fichiers sont dans `assets/animations/traversal-banks/sources.json`.

Le déplacement latéral accroché reste à faire plus tard. Les chutes, les dégâts et les atterrissages ordinaires gardent le comportement Half-Life existant. Cet atelier donne une base éditable, pas une validation artistique définitive : tes références de pose permettront d'ajuster précisément les poignets, les coudes et les prises.

## Commandes directes

```powershell
python vector-fields/traversal_editor.py export
python vector-fields/traversal_editor.py import --view first-person --gesture vf_hang_idle mon_export.smd
python vector-fields/traversal_editor.py apply
```

[fragMOTION officiel](http://www.fragmosoft.com/downloads/index.php) · [Tutoriel Half-Life officiel](https://www.fragmosoft.com/fragMOTION/Help/Tutorials/HalfLife.html) · [Mixamo](https://www.mixamo.com/)
