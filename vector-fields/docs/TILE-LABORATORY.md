# Modules jouables et menu de cartes

Lancer **Jouer - Vector Fields.cmd**, puis **F4**. Le menu donne accès aux cinq cartes locales, aux huit variantes de `vf_tiles` et aux quarante cartes CS/TFC déjà importées, en mode exploration. Les objectifs propres à CS/TFC restent désactivés. Sélection à la souris, à la molette ou avec les flèches ; Entrée ou **Lancer la carte** charge le choix. Échap ou F4 ferme le menu. Les anciennes touches F9 et Home ne lancent plus de carte dans le jeu principal. Les ateliers historiques conservent leurs contrôles propres.

**Modules jouables** tire une nouvelle disposition et mélange quatre familles, avec deux variantes chacune. **Laboratoire fermé A/B** utilise un toit, des cabinets ou des cloisons. **Chantier ouvert A/B** expose le ciel avec des machines ou conteneurs comme couvertures. **Galeries A/B** ajoute un second plateau accessible par escalier, des tirs en hauteur et un passage dessous. **Conduits A/B** ferme le volume et ajoute des chicanes et un raccourci bas. Le kit reste un blockout : les objets sont des volumes colorés, pas encore les modèles des concept arts.

Chaque cellule mesure 1280 unités, avec 256 unités entre cellules. La grille totale mesure 4352 unités. Le tirage assemble quatre à six modules en mono, domino, I ou L. Une variante est choisie par module entier ; ses cellules partagent donc la même famille. Une jonction interne reçoit un sol continu et, dans les modules fermés, un raccord couvert. Entre modules distincts, le tirage conserve passerelles, piliers optionnels et murs de wall run. Les plateformes ouvertes et les fenêtres de raccord exposent l'atmosphère animée et les cinq ambiances sonores du build principal.

Les huit choix individuels utilisent la graine 6 pour comparer les intérieurs sur la même disposition, qui contient les quatre formes. Le mode mélangé tire une nouvelle graine à chaque lancement. Les variantes modifient les cloisons, les couvertures et l'étendue du plateau haut, sans déplacer les points d'entrée communs.

| Couleur | Lecture |
| --- | --- |
| Orange | Structure, toit, cloison |
| Cyan | Surface de wall run |
| Violet | Passage bas / glissade |
| Jaune | Corniche, marche, accès haut |
| Vert | Raccord entre cellules |
| Rouge | Bord exposé / garde-corps |
| Gris | Sol et couverture de combat |

Prendre de l'élan puis s'accroupir pour glisser sous le raccourci violet. Sauter vers la corniche jaune basse pour l'accrocher ; relâcher puis maintenir Saut en reculant ou en regardant derrière permet de rattraper la corniche opposée, plus haute. Le mur cyan offre un parcours aérien au-dessus d'une couverture basse. Un escalier régulier mène à la galerie commune ; la famille Galeries dispose aussi d'un accès au second plateau à droite.

Les nouveaux volumes réutilisent la génération serveur existante. Le BSP contient 141 candidats sélectionnables et 143 modèles de brosses au total, avec matériaux embarqués. Le ciel et les nuages restent des ressources cosmétiques communes. La carte historique `vf_modular`, ses tests et ses sources sont conservés.

`game_profiles.py` reste le registre : il pilote compilation, livraison et catalogue du menu. Ajouter une carte au registre suffit à la faire apparaître, sans ajouter de touche. `cl_dll/vf_maps.cpp` lit les descriptions mais ne les exécute jamais ; seules les identités de carte/configuration validées et les variantes numériques deviennent des commandes.

La publication exige les tests d'assets, la politique sur 10 000 graines, les parcours réels des huit variantes, les douze raccords, la sauvegarde de la variante et les clics du menu suivis d'un chargement réel. Deux clients, dont une arrivée tardive, vérifient aussi les quatre formes et les collisions du tirage serveur. Les preuves sont dans `docs/validation/tile-laboratory/`. Les anciennes sources d'animation, cartes de référence, médias et lanceurs de compatibilité restent disponibles.
