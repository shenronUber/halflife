# Retoucher la prise du rebord

Ouvre `Retoucher la prise de reference - Vector Fields.cmd` à la racine du projet. Il charge **Mains-R1-prise-reference.blend**, avec l’image fournie affichée à droite. L’image et les textures sont intégrées au fichier.

La prise a été reconstruite depuis les mains R1 : dos des mains vers la caméra, pouces vers le centre, doigts courbés sur le dessus du rebord. Les articulations de `Hanging_Idle.glb` servent de base pour la flexion des doigts ; l’appui est ajusté à la géométrie des gants R1. Cette géométrie reste plus anguleuse que la référence.

Dans la vue 3D, ouvre le panneau **N → Vector Fields** pour choisir le geste. Les commandes **Main_G** et **Main_D** placent et orientent les mains avec **G** et **R**. Les commandes **G_Pouce**, **D_Pouce**, **Index**, **Majeur**, **Annulaire** et **Auriculaire** règlent chaque articulation avec **R**. Pour conserver une retouche animée, clique sur **Enregistrer la pose sélectionnée** dans ce panneau, puis enregistre le fichier avec **Ctrl+S**.

Le mur en fil de fer indique la surface d’appui et ne fait pas partie du modèle exporté. **Pavé numérique 0** retrouve la vue FPS ; la rotation de la vue permet de contrôler l’appui de côté.

Les actions retouchées portent le préfixe `REFERENCE|`. Les actions d’origine sont conservées dans le fichier. Le bouton d’export écrit dans `retouches/reference-rebord/first-person`, séparément des versions précédentes. Les animations de glissade ne sont pas retouchées ici. Cette révision est préparée pour examen dans Blender ; elle n’est pas installée dans le jeu.
