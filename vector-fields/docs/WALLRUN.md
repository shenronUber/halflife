# Wall run

Le wall run est intégré au jeu principal `vf_visual`. **F4** ouvre la salle
commune de tir et parcours ; **F9** ouvre la grille modulaire. **F10 / F12**
passent en troisième / première personne. La publication passe par
`build_release.py`, avec les mêmes DLL et ressources pour les deux cartes.

Courir, sauter près du côté d'un mur et garder **avancer**. Pour accrocher,
il suffit de l'une de ces deux intentions :

- orienter horizontalement le regard du côté du mur par rapport à sa tangente,
  même avec un angle faible ; il n'est pas nécessaire que le viseur touche une
  face précise, et regarder vers le haut ou le bas ne bloque pas l'accroche ;
- maintenir **avancer + gauche/droite**, avec la direction latérale qui pousse
  réellement vers ce mur selon l'orientation du regard.

Un regard exactement parallèle, sans direction latérale vers le mur, laisse
le saut ordinaire. La proximité seule et un déplacement latéral sans saut ou
sans avancer ne suffisent pas. Un contact réel avec un support reste obligatoire.
L'entrée exige
280 unités/seconde de vitesse horizontale et 200 le long du mur. Le personnage
conserve sa hauteur et son élan, plafonné à 400, tant que la touche reste enfoncée
et que le mur soutient le joueur. Relâcher avancer fait tomber immédiatement.
Ctrl, le sol, un obstacle frontal et la fin ou disparition du mur interrompent
aussi la course. Il n'y a pas de limite de durée artificielle.

Après l'accroche, la direction de course est conservée. Le regard reste libre
jusqu'à **90° de chaque côté** de cette direction, avec une hauteur libre.
Dépasser cette limite fait lâcher immédiatement. La direction latérale n'a
plus besoin de rester enfoncée après l'entrée ; **avancer** suffit.

Pendant la course, relâcher puis rappuyer sur **Espace** pour rebondir dans la
direction du regard, y compris sa hauteur. L'impulsion garantit une composante
vers l'extérieur du mur, même en regardant dedans. Un court délai de 0,18 seconde
évite de recoller immédiatement au départ ; le mur suivant peut ensuite être
rejoint en gardant avancer. Garder Espace depuis le saut initial ne déclenche pas
automatiquement un rebond.

Le corps 3D réutilise la boucle `ACT_RUN` existante. Le renderer compose les
jambes inclinées de 60 degrés et les pieds près de la surface avec le haut du
corps ordinaire. Visée, tir, recharge et équipements conservent leurs pistes.
Le même évaluateur sert aux hitboxes et aux observateurs. Les surfaces mobiles,
les échelles, la nage et les plafonds ne sont pas des supports de wall run.

## Intégration

- `game_shared/vf_wallrun.h` : constantes et tag d'état.
- `pm_shared/pm_wallrun.inc` : entrée, maintien, collision, sortie et impulsion.
- `engine/vf_wallrun_pose.inc` : composition de la course et du combat.
- `build_release.py` : candidat complet, validations et publication du jeu.
- `game_profiles.py` : cartes principale et modulaire, plus les régressions.

Les raccords dans le déplacement, l'animation serveur, la vue d'arme et le
build moteur sont limités à ce nouvel état. Les phases 0–7 et leurs indices
restent inchangés, y compris le rebond depuis une suspension ajouté en parallèle.
Le tag de course est le bit 16 avec phase basse 0 ; ce bit reste le drapeau
de plateforme large lorsque la phase basse vaut 1. Le bit 15 indique le côté du
mur pendant la course. Le mot reste sur 24 bits et conserve le yaw à sa place.
Passer par `VF_TR_Phase`, plutôt qu'un masque direct, pour lire le nouvel état.
Les deux coordonnées de surface et la hauteur sont mondiales et sauvegardables.
`fuser1` est un cycle de course normalisé selon la distance parcourue pendant
cet état, sans limite d'endurance. Il synchronise aussi le joueur local et les
clients qui arrivent après le début de la course. `vuser3.z` reste réservé aux
munitions ; aucun delta réseau n'est ajouté.

Les anciens builds d'essai isolés restent des archives. Pour construire et
publier la version courante :

```powershell
python vector-fields/build_release.py
```

Les tests de mouvement compilent le vrai solveur serveur/client à 8, 16 et
33 ms, y compris les anciens déplacements et deux rebonds successifs entre
deux murs. Les entrées par angle faible ou par direction latérale sont vérifiées
des deux côtés, dans les deux sens de course, contre un mur oblique et après un
vrai saut depuis le sol. La revue native vérifie aussi les armes, la sauvegarde,
le relâchement et les poses réellement rendues. Les preuves du candidat publié
sont dans `build/releases/<id>/integration`, référencées par son manifeste.
`tests/wallrun_multiplayer_test.py` vérifie aussi
la réception de la phase étendue et de la course par un observateur et un client
qui rejoint la partie après le début du wall run.
