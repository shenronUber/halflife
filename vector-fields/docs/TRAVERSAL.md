# DÃ©placements

Le lanceur habituel installe les dÃ©placements et leurs modÃ¨les. **F9** ouvre `vf_traversal`, un parcours avec muret, plateforme basse, rebord de 96 unitÃ©s, plafond empÃªchant la remontÃ©e, tour et piste de glissade.

| Geste | Commande |
| --- | --- |
| Saut ordinaire | Espace |
| Passer un muret Ã©troit | Avancer et appuyer sur Espace : appui gauche, arrivÃ©e automatique de l'autre cÃ´tÃ© |
| Monter sur une plateforme basse | Espace devant son bord : arrivÃ©e sur le dessus |
| Saisir un rebord | Garder Espace pendant le saut prÃ¨s du rebord |
| Rester suspendu Ã  deux mains | RelÃ¢cher Espace aprÃ¨s la saisie |
| Sortir l'arme en gardant la main gauche sur le rebord | Clic droit ; un premier clic gauche le permet aussi |
| Viser et tirer | Souris et clic gauche |
| Revenir Ã  deux mains | Clic droit |
| Monter depuis la suspension | Appuyer de nouveau sur Espace en regardant le mur |
| Se repousser du mur | S + Espace, ou regarder derriÃ¨re soi et appuyer de nouveau sur Espace |
| Attraper le rebord suivant | Garder Espace et orienter le regard vers le nouveau rebord pendant le vol |
| LÃ¢cher | Ctrl |
| Glisser | Courir, puis maintenir Ctrl |
| Interrompre la glissade | RelÃ¢cher Ctrl, ou Espace pour sauter |

Le saut depuis un rebord donne une impulsion de 270 unitÃ©s/seconde Ã  l'opposÃ© du mur et de 330 vers le haut. Il faut relÃ¢cher Espace aprÃ¨s la saisie, puis le presser avec S, ou aprÃ¨s avoir tournÃ© le regard d'au moins 100Â°. Le regard et le contrÃ´le en vol restent libres. Garder Espace permet une nouvelle prise aprÃ¨s 0,16 seconde, avant la fin du geste de 0,65 seconde. Face au mur, Espace seul conserve la remontÃ©e. Le tir et le rechargement restent bloquÃ©s pendant le geste.

Dans le parcours F9, deux rebords opposÃ©s Ã  `y = -500` permettent d'essayer la chaÃ®ne : premier rebord Ã  96 unitÃ©s, second Ã  160, avec un intervalle de 160 unitÃ©s. Les scÃ¨nes `Mains-R1-saut-mural.blend` et `Corps-R1-saut-mural.blend` contiennent les deux dÃ©parts, crÃ©Ã©s depuis les poses revues. Les lanceurs **Animer le saut mural - Mains.cmd** et **Animer le saut mural - Corps.cmd** ouvrent ces copies avec leurs commandes d'animation et leurs exports SMD.

La glissade demande au moins 280 unitÃ©s/seconde et dure au maximum 1,2 seconde. Elle conserve la vitesse de course, plafonnÃ©e Ã  400, avec une friction rÃ©duite de 0,35. AprÃ¨s toute sortie, un dÃ©lai de 0,85 seconde bloque la relance ; il faut relÃ¢cher puis rappuyer sur Ctrl. Ã€ 300 unitÃ©s/seconde, elle parcourt environ 320 unitÃ©s. La jambe gauche reste devant et le pied droit se replie sous la fesse gauche, avec le genou devant et Ã  droite. Une direction peut courber lentement la trajectoire.

Le muret Ã©troit, jusqu'Ã  64 unitÃ©s d'Ã©paisseur, se franchit en 0,82 seconde jusqu'au sol de l'autre cÃ´tÃ©. Une plateforme plus large reÃ§oit un geste distinct de 0,92 seconde et une arrivÃ©e sur le dessus. La main gauche prend l'appui et l'arme reste dans la main droite. Le contact de la paume est ajustÃ© au dessus rÃ©el de l'obstacle, aprÃ¨s le mÃ©lange des poses. Le regard s'incline temporairement vers cet appui ; la hauteur des yeux accompagne progressivement la flexion et retrouve sa hauteur debout avant la sortie. Les commandes de souris restent actives.

La remontÃ©e depuis une suspension dure 0,85 seconde. Le dÃ©placement vÃ©rifie les volumes de collision et le dÃ©gagement avant de s'engager. La suspension s'arrÃªte si son support disparaÃ®t ; les surfaces mobiles ne sont pas prises en charge. Le rechargement est interdit pendant la suspension, y compris un rechargement dÃ©jÃ  engagÃ© ou automatique. La chute et son atterrissage gardent le comportement historique ; aucune roulade ni animation de rÃ©ception n'est ajoutÃ©e. Le dÃ©placement latÃ©ral accrochÃ© reste reportÃ©.

Pendant la glissade, le R1 conserve ses animations ordinaires de visÃ©e, de tir, de rechargement et de changement d'arme. En troisiÃ¨me personne, le moteur compose le bas du corps assis avec le haut du corps de combat. La visÃ©e suit la camÃ©ra, indÃ©pendamment du dÃ©placement, et un rechargement engagÃ© pendant la glissade continue Ã  sa sortie. La pose accroupie ordinaire conserve Ã©galement le R1 en joue. Les poses subjectives ciblent le R1 ; les autres armes gardent leur modÃ¨le habituel.

Le corps subjectif rÃ©utilise les trois piÃ¨ces Ã©quipÃ©es (gilet, pantalon, bottes) avec leurs 23 skins, sÃ©parÃ©ment des bras et de l'arme de vue. Les manches extÃ©rieures sont retirÃ©es de ce passage car les bras de vue les fournissent dÃ©jÃ . Les vÃªtements sont visibles sur leurs deux faces, avec la profondeur normale du dÃ©cor. Le modÃ¨le de prÃ©sentation recule de 18 unitÃ©s pour placer le gilet derriÃ¨re l'Å“il ; une dÃ©coupe Ã  deux unitÃ©s sous l'Å“il Ã©vite le col. Pendant l'appui du franchissement, cette dÃ©coupe descend Ã  30 unitÃ©s pour dÃ©gager la vue de la paume. Ce rÃ©glage visuel ne dÃ©place pas le joueur et n'ajoute aucune collision Ã  la camÃ©ra.

Les neuf sÃ©quences historiques du R1 et les indices des 77 animations historiques du personnage sont conservÃ©s. Les paumes de suspension suivent le rebord, indÃ©pendamment du recul et de la camÃ©ra. Le tir derriÃ¨re le personnage place l'arme par-dessus l'Ã©paule, avec une garde vers le haut face au mur. Le bassin et les jambes gardent leur appui pendant les rotations du torse.

Pendant les dÃ©placements ordinaires en premiÃ¨re personne, les jambes suivent l'orientation du regard, mÃªme si le gait historique tourne vers la vitesse latÃ©rale ou diagonale. La correction s'applique uniquement Ã  la copie de rendu subjective ; elle conserve les animations de marche et ne change ni les collisions, ni la pose des observateurs.

Le cycle de marche conserve son historique entre les lectures de la physique et celles du rÃ©seau. Leurs horloges peuvent diffÃ©rer de quelques millisecondes dans une mÃªme image ; cet Ã©cart ne remet plus les jambes Ã  leur premiÃ¨re pose. Les deux vues utilisent les modÃ¨les Studio 3D et leurs animations de jambes.

Pendant la glissade, ce mÃªme corps Ã©quipÃ© fournit les jambes assises dans le monde. Leur orientation suit la direction de la glissade ; la souris peut tourner ou baisser le regard sans emporter les pieds. Le pantalon et les bottes prennent chacun leur skin Ã©quipÃ©. Leur prÃ©sentation subjective utilise l'origine du joueur, sans le recul de 18 unitÃ©s rÃ©servÃ© au corps debout, et une projection plus large pour voir la jambe avancÃ©e en regardant droit devant. Le gilet est retirÃ© de ce passage assis pour dÃ©gager la vue. La projection ordinaire est restaurÃ©e avant les autres dessins : le dÃ©cor, les bras, l'arme et la troisiÃ¨me personne conservent leur prÃ©sentation. Les anciennes jambes attachÃ©es Ã  la racine de l'arme ne sont plus ajoutÃ©es au modÃ¨le de vue. Le tir et le rechargement du R1 conservent leurs animations ordinaires.

Le client et le serveur compilent le mÃªme mouvement. L'Ã©tat, la direction, la hauteur et les coordonnÃ©es d'appui sont transmis avec la prÃ©diction et aux observateurs. Les champs de munitions restent rÃ©servÃ©s Ã  leur usage historique. Le lanceur vÃ©rifie les modÃ¨les, la carte, les DLL et le delta rÃ©seau livrÃ©s.

## Retoucher les gestes

Les lanceurs **Animer les franchissements - Vector Fields.cmd** et **Animer le corps des franchissements - Vector Fields.cmd** ouvrent les nouvelles bases `Mains-R1-franchissements-revus.blend` et `Corps-R1-franchissements-revus.blend`. Les fichiers d'origine restent disponibles. Le [guide Blender](../animation-workshop/traversal/blender/LIRE-MOI.md) dÃ©crit les poignÃ©es IK, les commandes des doigts, le changement de geste et l'export SMD. Les textures des 23 skins sont incluses dans ces nouvelles bases.

Les lanceurs Blender et fragMOTION prÃ©cÃ©dents restent disponibles pour les projets d'origine. **Appliquer les animations - Vector Fields.cmd** valide les exports SMD, recompile les poses et les dÃ©ploie. Les nouveaux exports d'enjambement ou de montÃ©e doivent passer par `traversal_editor import`, qui valide les longueurs des membres et marque la nouvelle rÃ©vision ; les anciens exports Ã  deux mains sont ignorÃ©s.

La suspension et le dÃ©but du lÃ¢cher sont adaptÃ©s de Freehang Drop ; le corps en remontÃ©e reprend Climbing To Top. Le clip local Vault Over Box a servi de rÃ©fÃ©rence de timing pour le muret ; ses gestes Ã  deux mains et sa rotation latÃ©rale ont Ã©tÃ© refaits pour l'appui gauche et le R1. Les sources conservent leur rÃ©vision et leur SHA256. Le lÃ¢cher dure 0,30 seconde avec la gravitÃ© ordinaire.

## Validation et livraison

Le wall run, les deux sauts depuis la suspension, la marche et le coup de crosse sont réunis dans le runtime principal `vf_visual`. Le lanceur habituel utilise cette compilation ; la revue privée du wall run est conservée séparément. Les porteurs de mêlée utilisent aussi les poses de collision communes. Voir [le rapport d’intégration du 12 octobre 2026](validation/integration-2026-10-12.json).

`tests/traversal_wall_jump_native_test.py` vÃ©rifie les deux commandes dans les deux vues, la reprise du rebord opposÃ© plus haut, le blocage du tir et la remontÃ©e ordinaire. `tests/traversal_wall_jump_walk_test.py` mesure le mouvement rÃ©el des deux pieds pendant la marche avant, arriÃ¨re, latÃ©rale et diagonale dans les deux vues, ainsi que l'arrÃªt et la hauteur de collision. La livraison du saut mural exige ces deux validations sur les mÃªmes DLL, renderer et champs rÃ©seau ; ses scÃ¨nes Blender sont des copies des sources revues.

`tests/traversal_posture_native_test.py --encode` capture les deux franchissements, la glissade sous deux angles, le combat accroupi et le corps subjectif. Il contrÃ´le le contact plantÃ©, les munitions et la direction du canon. Les audits Blender Ã©chantillonnent aussi les demi-images et les longueurs de membres ; les assets compilÃ©s sont comparÃ©s aux pistes prÃ©cÃ©dentes pour dÃ©tecter les modifications Ã©trangÃ¨res aux gestes retouchÃ©s.

`tests/traversal_slide_combat_native_test.py` contrÃ´le le tir et le rechargement pendant la glissade dans les deux vues, l'alignement du canon et la stabilitÃ© des jambes. Les captures rÃ©utilisent le cache de ressources, puis retirent leur session temporaire aprÃ¨s encodage.

`tests/first_person_motion_native_test.py` vÃ©rifie le geste H aprÃ¨s une glissade rÃ©elle, quatre directions de marche et la pose mondiale des pieds sous cinq angles de regard. `tests/traversal_slide_view_test.py` contrÃ´le les jambes visibles en regardant vers le bas, le corps assis extÃ©rieur et le retour debout. `tests/traversal_slide_combat_native_test.py --slide-feet` contrÃ´le le tir et le rechargement dans les deux vues, en conservant les assets installÃ©s pendant qu'une autre conversation retouche ses animations. Ces tests acceptent `--candidate-dir` pour vÃ©rifier une compilation privÃ©e avant livraison.

`tests/slide_presentation_native_test.py` ajoute la visibilitÃ© en vue droite, six directions de regard et la comparaison de la pose extÃ©rieure avec les deux rÃ©glages de prÃ©sentation. Il lit les modÃ¨les installÃ©s dans une session isolÃ©e et n'Ã©crit aucune banque d'animation. `vf_slide_body_forward` est un rÃ©glage de revue interne, limitÃ© Ã  âˆ’18â€¦48 unitÃ©s et fixÃ© par dÃ©faut Ã  zÃ©ro ; il reste indÃ©pendant de la camÃ©ra.

`animation-workshop/install-posture-review.py` livre uniquement les fichiers modifiÃ©s, avec sauvegarde prÃ©alable et contrÃ´le des empreintes de la version filmÃ©e. Le cÅ“ur du moteur dÃ©jÃ  installÃ© reste en place, sauf le pont `xash.dll` lorsqu'un changement d'API renderer exige sa mise Ã  jour. L'API 4 de l'Ã©quipement casque nÃ©cessite ce pont et le catalogue compatibles ; les deux revues natives doivent passer avant de rÃ©unir ces fichiers. Le renderer se compile avec `build-engine.ps1` ; `build.ps1` construit les DLL et les assets. Les tests de mouvement vÃ©rifient plusieurs durÃ©es d'image et la paritÃ© de prÃ©diction. Les tests `traversal_native_test.py`, `traversal_save_native_test.py` et `traversal_multiplayer_test.py` couvrent les gestes, la sauvegarde et la rÃ©ception par les autres clients.
