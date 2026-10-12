# Wall run

Lancer **Essayer le wall run - Vector Fields.cmd**. Ce lanceur utilise les DLL
testées dans `build/wallrun`, les équipements installés et une session privée.
Il ne remplace aucune DLL du jeu habituel, aucun modèle ou export Blender.
F9 revient au couloir d'essai ; F10 montre le personnage en troisième personne,
F12 revient en première personne.

Courir, sauter près du côté d'un mur et garder **avancer**. L'entrée exige
280 unités/seconde de vitesse horizontale et 200 le long du mur. Le personnage
conserve sa hauteur et son élan, plafonné à 400, tant que la touche reste enfoncée
et que le mur soutient le joueur. Relâcher avancer fait tomber immédiatement.
Ctrl, le sol, un obstacle frontal et la fin ou disparition du mur interrompent
aussi la course. Il n'y a pas de limite de durée artificielle.

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

## Intégration indépendante

- `game_shared/vf_wallrun.h` : constantes et tag d'état.
- `pm_shared/pm_wallrun.inc` : entrée, maintien, collision, sortie et impulsion.
- `engine/vf_wallrun_pose.inc` : composition de la course et du combat.
- `build_wallrun.py` : snapshot privé des sources, caches et binaires isolés.
- `build_wallrun_range.py` : carte dédiée, sans retouche du parcours existant.

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

La compilation habituelle des sources inclut cette mécanique. La version
d'essai séparée permet de la vérifier sans publier ou remplacer le travail
installé en parallèle. Pour reconstruire l'essai :

```powershell
python vector-fields/build_wallrun.py
python vector-fields/tests/wallrun_native_test.py
```

Les tests de mouvement compilent le vrai solveur serveur/client à 8, 16 et
33 ms, y compris les anciens déplacements et deux rebonds successifs entre
deux murs. La revue native vérifie la course, les deux côtés, les armes, la
sauvegarde, le relâchement et les poses réellement rendues. Les preuves sont
dans `docs/validation/wallrun`. `tests/wallrun_multiplayer_test.py` vérifie aussi
la réception de la phase étendue et de la course par un observateur et un client
qui rejoint la partie après le début du wall run.
