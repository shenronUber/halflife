# Atelier Blender — Vector Fields

Blender 4.5 LTS est installé en version portable dans `devtools/blender`, avec un profil propre au projet. **Animer dans Blender - Vector Fields.cmd** ouvre `Mains-R1.blend`. **Animer le corps dans Blender - Vector Fields.cmd** ouvre `Corps-R1.blend`. Les textures sont incluses dans les projets. Les sources, les skins et le jeu ne sont pas remplacés par l'ouverture de l'atelier.

## Choisir une animation

Pour les derniers appuis et franchissements, **Animer les franchissements - Vector Fields.cmd** ouvre `Mains-R1-franchissements-revus.blend` et **Animer le corps des franchissements - Vector Fields.cmd** ouvre `Corps-R1-franchissements-revus.blend`. Ces bases contiennent le passage du muret avec appui gauche, la montée sur plateforme et le pied droit replié sous l'assise gauche. Les projets précédents restent disponibles.

Dans la vue 3D, appuyer sur **N** pour afficher le panneau de droite, puis ouvrir l'onglet **Vector Fields**. Choisir le **Geste** dans la liste : suspension, saisie, remontée, lâcher, obstacle bas, passage au tir ou glissade. Les pistes de visée et leurs secteurs sont aussi disponibles. Ce sélecteur connecte la bonne animation source et ses commandes de retouche. Utiliser ce sélecteur pour changer de geste.

Le sélecteur **Skin** change l'apparence dans l'atelier. Il ne modifie pas les textures sources. Le rebord gris est un repère visuel pour juger la prise ; il ne fait pas partie du modèle exporté et peut être déplacé depuis la liste des objets en désactivant son verrouillage de sélection.

## Corriger les mains

Le projet s'ouvre en **Pose Mode**, prêt à sélectionner les commandes. Les boutons **Main gauche / Main droite**, **Coude** et les segments numérotés des doigts permettent de sélectionner précisément une commande sans devoir chercher un nom d'os historique.

- **G** déplace une main ; le bras suit sans étirement. Déplacer la commande du coude règle la direction du pli du bras.
- **R** tourne la paume ou un segment de doigt. **R**, puis **X**, **Y** ou **Z** contraint la rotation à un axe ; l'orientation initiale est **Local**.
- Les doigts se règlent par rotation. La base porte le numéro **1**, les segments suivants **2**, **3**, puis **4** pour les doigts longs. Le pouce possède trois segments. La translation et l'échelle des doigts sont verrouillées.
- La clé automatique est activée. Après une manipulation, le bouton **Enregistrer la pose sélectionnée** garantit l'enregistrement des commandes sélectionnées à l'image courante. **I** insère également une clé dans Blender.
- **Ctrl+S** enregistre toutes les retouches dans le `.blend`. Pour garder une variante, utiliser **File / Save As** dans ce même dossier `blender/`, afin de conserver le chemin relatif vers les exports du jeu.

La souris du milieu fait tourner la vue, **Maj + souris du milieu** la déplace, la molette zoome. **Pavé numérique .** cadre la sélection ; **1**, **3**, **7** donnent des vues orthogonales. **Alt+G / Alt+R** réinitialisent les canaux sélectionnés : ils ne restaurent pas automatiquement la pose source. Utiliser **Ctrl+Z** pour annuler une manipulation.

Chaque image possède les clés de la base importée : une retouche à l'image 1 ne modifie pas automatiquement les autres images. Pour une suspension stable, corriger aussi les poses suivantes ou copier les clés corrigées dans la feuille d'animation. Les animations en boucle doivent revenir à leur pose de départ ; le compilateur GoldSrc copie la première pose sur la dernière image de la boucle. Le rebord est un repère approximatif : masquer son objet dans la liste des objets s'il cache la zone que tu veux travailler.

Une main hors de portée est signalée dans le panneau ; la pose est limitée à la portée du bras. Le corps utilise des commandes FK ordinaires : tourner les commandes des membres, des mains ou des doigts. L'IK des poignées est spécifique à l'atelier des mains.

## Exporter une correction

1. Enregistrer le `.blend` avec **Ctrl+S**.
2. Cliquer **Exporter ce geste pour le jeu** dans le panneau Vector Fields. Le fichier est écrit dans `traversal/retouches/first-person/` ou `third-person/`. Le nom est choisi automatiquement, par exemple `vf_hang_idle_0.smd`. Un export précédent est sauvegardé en `.smd.previous`.
3. Le bouton exporte toute la piste, avec les noms et les parents du squelette original. Il exclut les commandes Blender et le rebord. La longueur des os et l'échelle sont vérifiées.
4. Pour appliquer les exports au jeu après validation visuelle, fermer le jeu puis utiliser **Appliquer les animations - Vector Fields.cmd**, déjà présent à la racine du projet.

L'export ne lance pas le jeu et ne déploie rien. Les animations source sont conservées dans le rig masqué `VF_Source`. Les retouches portent sur `VF_Commandes`, et le mesh est déformé par le rig de résultat `VF_Jeu`. Éviter de modifier ces deux rigs techniques ou de changer leurs noms.

## Préserver les projets

La préparation de l'atelier ne remplace jamais un projet `.blend` existant : une nouvelle base est enregistrée sous un autre nom. Ouvrir les fichiers avec les lanceurs fournis afin de charger le profil du projet et son extension de commandes. Aucun script Python intégré au `.blend` n'a besoin d'être autorisé.

Blender Source Tools est aussi installé pour l'import/export SMD général. Pour nos retouches, privilégier le bouton dédié : il garde tous les os du jeu et exclut les commandes d'animation.

[Blender 4.5 LTS](https://www.blender.org/releases/4-5/) · [Blender Source Tools](https://github.com/Artfunkel/BlenderSourceTools)
