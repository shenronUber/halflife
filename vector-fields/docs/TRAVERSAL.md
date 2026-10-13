# Déplacements

Le lanceur habituel utilise le build principal validé `vf_visual`. **F4** ouvre le [menu de cartes](TILE-LABORATORY.md) pour choisir la salle commune `vf_range`, la grille simple `vf_modular`, les modules jouables `vf_tiles` et les cartes de référence. Le parcours historique `vf_traversal` reste une carte de régression.

| Geste | Commande |
| --- | --- |
| Saut ordinaire | Espace |
| Accrocher en wall run | Courir et sauter près du mur en gardant Avancer, avec le regard du côté du mur ou gauche/droite vers lui |
| Continuer le wall run | Garder Avancer ; regard libre jusqu’à 90° de chaque côté du cap |
| Rebondir depuis le wall run | Relâcher puis rappuyer sur Espace |
| Passer un muret étroit | Avancer et appuyer sur Espace : appui gauche, arrivée automatique de l'autre côté |
| Monter sur une plateforme basse | Espace devant son bord : arrivée sur le dessus |
| Saisir un rebord | Garder Espace pendant le saut près du rebord |
| Rester suspendu à deux mains | Relâcher Espace après la saisie |
| Sortir l'arme en gardant la main gauche sur le rebord | Clic droit ; un premier clic gauche le permet aussi |
| Viser et tirer | Souris et clic gauche |
| Revenir à deux mains | Clic droit |
| Monter depuis la suspension | Appuyer de nouveau sur Espace en regardant le mur |
| Se repousser du mur | S + Espace, ou regarder derrière soi et appuyer de nouveau sur Espace |
| Attraper le rebord suivant | Garder Espace et orienter le regard vers le nouveau rebord pendant le vol |
| Lâcher | Ctrl |
| Glisser | Courir, puis maintenir Ctrl |
| Interrompre la glissade | Relâcher Ctrl, ou Espace pour sauter |

Le saut depuis un rebord donne une impulsion de 270 unités/seconde à l'opposé du mur et de 330 vers le haut. Il faut relâcher Espace après la saisie, puis le presser avec S, ou après avoir tourné le regard d'au moins 100°. Le regard et le contrôle en vol restent libres. Garder Espace permet une nouvelle prise après 0,16 seconde, avant la fin du geste de 0,65 seconde. Face au mur, Espace seul conserve la remontée. Le tir et le rechargement restent bloqués pendant le geste.

Dans le parcours de la salle combinée F4, deux rebords opposés à `y = -500` permettent d'essayer la chaîne : premier rebord à 96 unités, second à 160, avec un intervalle de 160 unités. Les scènes `Mains-R1-saut-mural.blend` et `Corps-R1-saut-mural.blend` contiennent les deux départs, créés depuis les poses revues. Les lanceurs **Animer le saut mural - Mains.cmd** et **Animer le saut mural - Corps.cmd** ouvrent ces copies avec leurs commandes d'animation et leurs exports SMD.

La glissade demande au moins 280 unités/seconde et dure au maximum 1,2 seconde. Elle conserve la vitesse de course, plafonnée à 400, avec une friction réduite de 0,35. Après toute sortie, un délai de 0,85 seconde bloque la relance ; il faut relâcher puis rappuyer sur Ctrl. À 300 unités/seconde, elle parcourt environ 320 unités. La jambe gauche reste devant et le pied droit se replie sous la fesse gauche, avec le genou devant et à droite. Une direction peut courber lentement la trajectoire.

Le muret étroit, jusqu'à 64 unités d'épaisseur, se franchit en 0,82 seconde jusqu'au sol de l'autre côté. Une plateforme plus large reçoit un geste distinct de 0,92 seconde et une arrivée sur le dessus. La main gauche prend l'appui et l'arme reste dans la main droite. Le contact de la paume est ajusté au dessus réel de l'obstacle, après le mélange des poses. Le regard s'incline temporairement vers cet appui ; la hauteur des yeux accompagne progressivement la flexion et retrouve sa hauteur debout avant la sortie. Les commandes de souris restent actives.

La remontée depuis une suspension dure 0,85 seconde. Le déplacement vérifie les volumes de collision et le dégagement avant de s'engager. La suspension s'arrête si son support disparaît ; les surfaces mobiles ne sont pas prises en charge. Le rechargement est interdit pendant la suspension, y compris un rechargement déjà engagé ou automatique. La chute et son atterrissage gardent le comportement historique ; aucune roulade ni animation de réception n'est ajoutée. Le déplacement latéral accroché reste reporté.

Pendant la glissade, le R1 conserve ses animations ordinaires de visée, de tir, de rechargement et de changement d'arme. En troisième personne, le moteur compose le bas du corps assis avec le haut du corps de combat. La visée suit la caméra, indépendamment du déplacement, et un rechargement engagé pendant la glissade continue à sa sortie. La pose accroupie ordinaire conserve également le R1 en joue. Les poses subjectives ciblent le R1 ; les autres armes gardent leur modèle habituel.

Le corps subjectif réutilise les trois pièces équipées (gilet, pantalon, bottes) avec leurs 23 skins, séparément des bras et de l'arme de vue. Les manches extérieures sont retirées de ce passage car les bras de vue les fournissent déjà. Les vêtements sont visibles sur leurs deux faces, avec la profondeur normale du décor. Le modèle de présentation recule de 18 unités pour placer le gilet derrière l'œil ; une découpe à deux unités sous l'œil évite le col. Pendant l'appui du franchissement, cette découpe descend à 30 unités pour dégager la vue de la paume. Ce réglage visuel ne déplace pas le joueur et n'ajoute aucune collision à la caméra.

Les neuf séquences historiques du R1 et les indices des 77 animations historiques du personnage sont conservés. Les paumes de suspension suivent le rebord, indépendamment du recul et de la caméra. Le tir derrière le personnage place l'arme par-dessus l'épaule, avec une garde vers le haut face au mur. Le bassin et les jambes gardent leur appui pendant les rotations du torse.

Pendant les déplacements ordinaires en première personne, les jambes suivent l'orientation du regard, même si le gait historique tourne vers la vitesse latérale ou diagonale. La correction s'applique uniquement à la copie de rendu subjective ; elle conserve les animations de marche et ne change ni les collisions, ni la pose des observateurs.

Le cycle de marche conserve son historique entre les lectures de la physique et celles du réseau. Leurs horloges peuvent différer de quelques millisecondes dans une même image ; cet écart ne remet plus les jambes à leur première pose. Les deux vues utilisent les modèles Studio 3D et leurs animations de jambes.

Pendant la glissade, ce même corps équipé fournit les jambes assises dans le monde. Leur orientation suit la direction de la glissade ; la souris peut tourner ou baisser le regard sans emporter les pieds. Le pantalon et les bottes prennent chacun leur skin équipé. Leur présentation subjective utilise l'origine du joueur, sans le recul de 18 unités réservé au corps debout, et une projection plus large pour voir la jambe avancée en regardant droit devant. Le gilet est retiré de ce passage assis pour dégager la vue. La projection ordinaire est restaurée avant les autres dessins : le décor, les bras, l'arme et la troisième personne conservent leur présentation. Les anciennes jambes attachées à la racine de l'arme ne sont plus ajoutées au modèle de vue. Le tir et le rechargement du R1 conservent leurs animations ordinaires.

Le client et le serveur compilent le même mouvement. L'état, la direction, la hauteur et les coordonnées d'appui sont transmis avec la prédiction et aux observateurs. Les champs de munitions restent réservés à leur usage historique. Le lanceur vérifie les modèles, la carte, les DLL et le delta réseau livrés.

## Retoucher les gestes

Les lanceurs **Animer les franchissements - Vector Fields.cmd** et **Animer le corps des franchissements - Vector Fields.cmd** ouvrent les nouvelles bases `Mains-R1-franchissements-revus.blend` et `Corps-R1-franchissements-revus.blend`. Les fichiers d'origine restent disponibles. Le [guide Blender](../animation-workshop/traversal/blender/LIRE-MOI.md) décrit les poignées IK, les commandes des doigts, le changement de geste et l'export SMD. Les textures des 23 skins sont incluses dans ces nouvelles bases.

Les lanceurs Blender et fragMOTION précédents restent disponibles pour les projets d'origine. **Appliquer les animations - Vector Fields.cmd** valide les exports SMD, recompile les poses et les déploie. Les nouveaux exports d'enjambement ou de montée doivent passer par `traversal_editor import`, qui valide les longueurs des membres et marque la nouvelle révision ; les anciens exports à deux mains sont ignorés.

La suspension et le début du lâcher sont adaptés de Freehang Drop ; le corps en remontée reprend Climbing To Top. Le clip local Vault Over Box a servi de référence de timing pour le muret ; ses gestes à deux mains et sa rotation latérale ont été refaits pour l'appui gauche et le R1. Les sources conservent leur révision et leur SHA256. Le lâcher dure 0,30 seconde avec la gravité ordinaire.

## Validation et livraison

Le wall run, les deux sauts depuis la suspension, la marche et la frappe au canon sont réunis dans le runtime principal `vf_visual`. Le lanceur habituel passe par la publication complète `build_release.py`. Les anciens builds privés servent de références historiques ; les validations actuelles portent sur le candidat complet. Voir les [conditions du wall run](WALLRUN.md). Les porteurs de mêlée utilisent aussi les poses de collision communes. Voir [le rapport d’intégration du 12 octobre 2026](validation/integration-2026-10-12.json).

`tests/traversal_wall_jump_native_test.py` vérifie les deux commandes dans les deux vues, la reprise du rebord opposé plus haut, le blocage du tir et la remontée ordinaire. `tests/traversal_wall_jump_walk_test.py` mesure le mouvement réel des deux pieds pendant la marche avant, arrière, latérale et diagonale dans les deux vues, ainsi que l'arrêt et la hauteur de collision. La livraison du saut mural exige ces deux validations sur les mêmes DLL, renderer et champs réseau ; ses scènes Blender sont des copies des sources revues.

`tests/traversal_posture_native_test.py --encode` capture les deux franchissements, la glissade sous deux angles, le combat accroupi et le corps subjectif. Il contrôle le contact planté, les munitions et la direction du canon. Les audits Blender échantillonnent aussi les demi-images et les longueurs de membres ; les assets compilés sont comparés aux pistes précédentes pour détecter les modifications étrangères aux gestes retouchés.

`tests/traversal_slide_combat_native_test.py` contrôle le tir et le rechargement pendant la glissade dans les deux vues, l'alignement du canon et la stabilité des jambes. Les captures réutilisent le cache de ressources, puis retirent leur session temporaire après encodage.

`tests/first_person_motion_native_test.py` vérifie le geste H après une glissade réelle, quatre directions de marche et la pose mondiale des pieds sous cinq angles de regard. `tests/traversal_slide_view_test.py` contrôle les jambes visibles en regardant vers le bas, le corps assis extérieur et le retour debout. `tests/traversal_slide_combat_native_test.py --slide-feet` contrôle le tir et le rechargement dans les deux vues, en conservant les assets installés pendant qu'une autre conversation retouche ses animations. Ces tests acceptent `--candidate-dir` pour vérifier une compilation privée avant livraison.

`tests/slide_presentation_native_test.py` ajoute la visibilité en vue droite, six directions de regard et la comparaison de la pose extérieure avec les deux réglages de présentation. Il lit les modèles installés dans une session isolée et n'écrit aucune banque d'animation. `vf_slide_body_forward` est un réglage de revue interne, limité à −18…48 unités et fixé par défaut à zéro ; il reste indépendant de la caméra.

`animation-workshop/install-posture-review.py` livre uniquement les fichiers modifiés, avec sauvegarde préalable et contrôle des empreintes de la version filmée. Le cœur du moteur déjà installé reste en place, sauf le pont `xash.dll` lorsqu'un changement d'API renderer exige sa mise à jour. L'API 4 de l'équipement casque nécessite ce pont et le catalogue compatibles ; les deux revues natives doivent passer avant de réunir ces fichiers. Le renderer se compile avec `build-engine.ps1` ; `build.ps1` construit les DLL et les assets. Les tests de mouvement vérifient plusieurs durées d'image et la parité de prédiction. Les tests `traversal_native_test.py`, `traversal_save_native_test.py` et `traversal_multiplayer_test.py` couvrent les gestes, la sauvegarde et la réception par les autres clients.
