# R1 : formes et finitions adaptées

Les 72 formes du R1 proposent **130 objets finis** dans l’inventaire de jeu.
Chaque forme a une ou deux finitions choisies sur les modèles compilés, avec
leurs UV et leurs textures réelles. Le choix et sa justification sont explicites
dans `data/r01-fitted-finishes.json` ; un modèle absent de cette politique provoque
une erreur de génération. Les finitions ne sont donc plus appliquées à toutes
les formes par défaut.

La pile **Cellule ambre 24V** conserve seulement sa finition électrique d’origine.
Les quatre culasses classiques restent également dans leur finition usinée.
Les tenues, gants, bottes et animations du joueur ne font pas partie de cette
sélection. Les banques historiques des pièces non révisées restent disponibles
dans les outils de développement ; les combinaisons retirées du jeu sont archivées
dans l’atelier. Les quinze modèles de la [révision poignées et forge](R1-GRIP-AND-FORGE.md)
emploient désormais deux maps propres avec des indices de skin historiques stables.

Deux nouveaux canons :

- **Aigrette** : chemise acier, ailettes longitudinales, frettes et bois rouge.
- **Relique** : fourreau d’os, petites crêtes et tendons autour d’un tube acier apparent.

Cinq nouvelles bouches, toutes des variantes visuelles de silencieux :

- **Sourdine** : long corps bleui et bagues moletées.
- **Tresse** : gaine textile sable, brides et couture.
- **Campanule** : chambres étagées en laiton et cerclages acier.
- **Ossifié** : os irrégulier, ligatures et insert mécanique apparent.
- **Étouffoir** : céramique facettée, joints graphite et nez métallique.

Chacune possède un projet Blender éditable, un GLB avec images embarquées,
un atlas couleur 2048 px et des cartes normales, rugosité, métal et occlusion
1024 px. GoldSrc emploie leur atlas diffus propre de 512 px. Ce sont des
modules statiques sur le repère Bone76 : X largeur, +Y avant, Z haut.

Les canons gardent la portée arrière Y=17 et la portée de bouche Y=31 ; les
bouches commencent à Y=30,8. Leurs sections mécaniques sont centrées sur
X=0, Z=1,3, avec un alésage ouvert. Les fourreaux organiques et textiles sont
reliés à leur noyau mécanique. Aucun tube central n’est courbé.

La validation comprend la compilation StudioMDL, le contrôle des UV,
des contacts et des sections natives, dix combinaisons visibles en jeu,
cinq tirs/rechargements et **2 409 assemblages** contrôlés sans rejet.

Pour essayer les pièces, lancer **Revoir les canons et silencieux - Vector Fields.cmd**.
Touches **1/2** : canons ; **5 à 9** : silencieux ; **F11** : inventaire.
Ce lanceur utilise les modèles installés sans générer d’assets ni compiler de DLL.

L’installation ajoute seulement les sept MDL, retire les lignes de finitions
R1 non retenues et met à jour les indices dérivés du catalogue. Les lignes et
métadonnées des objets joueur restent intactes. Les sauvegardes utilisent des
identifiants stables ; une finition retirée retombe sur le défaut de son
emplacement, comme prévu par le moteur actuel. Les catalogues complets avant
sélection sont sauvegardés dans `weapon-workshop/fitted-2026-10-11/integration-backup`.

Atelier local : `weapon-workshop/fitted-2026-10-11/review.html`,
`finishes.html` et `in-game.html`. Rapports : `manifest.json`,
`native-check.json`, `installation.json` et `catalogue-check.json`.
