# Vector Fields 0.20.0 — Mains et manches équipées

Les **gants équipés** déterminent maintenant l’apparence des mains à la première
personne. La **veste équipée** détermine celle des manches. Les quatorze tenues
sont couvertes, dont Rome / Inventeur et Dieselpunk. Les deux choix restent
indépendants : des gants d’inventeur peuvent accompagner une veste de plongeur.
Il suffit de valider l’objet dans l’inventaire habituel.

Les textures des tenues sont réutilisées grâce à un dépliage anatomique :
un raccord continu entre paume et dos, une projection adaptée à chaque doigt et
un raccord sous la manche. Les îlots sont extraits à leur résolution native
avant leur rangement dans les atlas dédiés (512 × 512 pour les gants,
512 × 256 pour les manches) ; on évite ainsi de réduire tout le personnage
à 512 pixels avant de prélever les détails. Aucun nouveau détail HD n’est créé. Les anciennes mains orange et leur plaque
électronique laissent place aux matériaux des gants choisis. Les modèles et
textures du personnage à la troisième personne sont conservés.

## Chargeur latéral

La main prend le chargeur par-dessus, inclinée vers l’avant comme sur une
poignée de moto. Le coude reste bas pour dégager la vue. La rotation locale
du poignet au repos passe d’environ 38° à 23°. La main accompagne le chargeur
pendant son extraction et sa remise en place ; la longueur des os est conservée.
Les quatre formes de chargeur gardent le même point de prise.

## Organisation technique

Deux modèles communs, `r01_fp_gloves.mdl` et `r01_fp_sleeves.mdl`, suivent
les os des trois squelettes d’animation R-01. Chaque modèle possède quatorze
familles de textures. Il n’est pas nécessaire de générer une arme pour chaque
association de tenue : les **61 pièces d’arme restent identiques**.

Le modèle conserve le volume des bras et les points d’articulation d’origine.
Les douze faces du matériau de la plaque de poignet sont retirées. Les sept
faces latérales du boîtier et le bracelet détaché sont corrigés dans la
[version 0.20.1](RELEASE-0.20.1.md). Le gant
possède déjà une surface fermée dessous : aucune plaque de remplacement
n’est ajoutée. Une subdivision ciblée ajoute 334 triangles aux doigts, avec
un arrondi limité à 0,1 unité ; seuls les bords dont les deux sommets suivent
le même os sont subdivisés. Les deux pièces totalisent 868 triangles (772 pour
les gants, 96 pour les manches), sans nouvel os. Les normales du gant sont lissées. L’assemblage utilise 14 des 16
emplacements disponibles dans le moteur. L’état des objets déjà synchronisé
et sauvegardé suffit à retrouver les deux apparences ; protocole et format de
sauvegarde restent ceux de la version 0.19.

## Vérification

- Compilation des DLL client et serveur ; validations d’équipement,
  d’architecture, de géométrie et d’effets.
- `first_person_test.py --mode assets` : points d’articulation et poids conservés, UV non dégénérés,
  compatibilité avec les trois squelettes, 196 associations d’apparences,
  poignet détendu, coude bas et continuité de la recharge.
- `first_person_test.py --mode native` : quatorze tenues, mélanges de zones,
  sauvegarde/reprise, quatre chargeurs sur chacune des trois alimentations,
  aperçu avec/sans mains, chargement en cache et audit des assemblages.
- `reference_platform_test.assets()` : longueurs des os, contact main/chargeur,
  poses sérialisées, points de raccord et compatibilité des finitions.
- `current_release_test.py` : lanceur et empreintes des modèles installés.

Le système s’applique aux armes modulaires R-01 de l’inventaire de jeu.
Les armes historiques importées dans les outils développeur conservent leurs
mains propres. Le squelette et les séquences restent issus du modèle de première personne
existant ; il n’y a pas encore de prise sculptée
séparément pour chaque épaisseur de chargeur.

## Atelier 3D

`python vector-fields/inspect_first_person.py` produit
`vector-fields/build/first-person-inspector.html`, une page autonome avec
rotation, zoom, vue paume/dos, maillage, UV et choix indépendant des quatorze
gants/manches. Elle lit les modèles compilés et leurs textures, avec poses
latérales et de rechargement. Cet outil ne fait pas partie du menu joueur.

Les essais Counter-Strike ont été archivés : leur géométrie n’est pas utilisée.
Les trois essais de textures HD restent [expérimentaux](../assets/first-person/README.md).
