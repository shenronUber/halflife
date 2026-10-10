# Vector Fields 0.20.1 — Gants et rechargements

Le gant de première personne conserve sa surface naturelle. Le boîtier de
poignet est maintenant retiré entièrement, y compris ses sept faces latérales
qui utilisaient le matériau du gant. Le bracelet flottant et ses panneaux
associés sont supprimés : leurs os suivaient le coude plutôt que le poignet.
Au total, 55 faces accessoires du modèle source sont exclues, sans ajouter de
plaque de remplacement. Gants et manches totalisent 825 triangles.

L’index gauche utilise la même courbure que le majeur sur toute sa chaîne
articulée, en conservant sa position et ses longueurs propres. La prise
latérale reste inclinée vers l’avant avec le poignet détendu.

Pour les deux châssis à alimentation supérieure, l’arme bascule de 65° vers
la gauche autour de son axe longitudinal. La main droite accompagne la
poignée, la main gauche suit le chargeur et le mouvement revient progressivement
à la pose initiale. La hauteur maximale du poignet pendant l’extraction diminue
d’environ 18 unités. Les longueurs des deux bras et le contact aux poignées sont
conservés. Les captures 1080p montrent la manche qui se poursuit hors du bas de
l’écran pendant le geste, sans exposer sa coupure proximale.

Les quatorze apparences classiques restent indépendantes pour les gants et
les manches. Les 61 modèles de pièces d’arme restent identiques. Le personnage
à la troisième personne, les coûts, le protocole et les sauvegardes conservent
leur fonctionnement actuel.

## Vérifications

- `build.ps1` : DLL et suites d’équipement, d’architecture, d’effets et de géométrie.
- `first_person_test.py --mode assets` : retrait complet des accessoires,
  surface du gant préservée, chaîne de l’index, bascule progressive, contact de
  la main droite, longueurs des deux bras et 196 associations d’apparences.
- `reference_platform_test.assets()` : 740 poses sérialisées, contact avec le
  chargeur, raccords des plateformes et 854 finitions.
- `first_person_test.py --mode native` : 43 captures, quatorze tenues, mélanges,
  sauvegarde/reprise, quatre chargeurs sur trois alimentations et 1753 assemblages.
- `first_person_test.py --mode sweep` : 35 captures supplémentaires pour vérifier
  le gant et le cadrage des manches pendant les deux rechargements.
- `current_release_test.py` : version installée, 68 empreintes de modèles,
  démarrage et sauvegarde/reprise.

`inspect_first_person.py` met à jour l’atelier 3D autonome. Des poses d’extraction,
de retrait et d’insertion supérieure permettent de vérifier le geste sous
plusieurs angles. Cet outil reste séparé du menu joueur.

La prise reste commune aux quatre épaisseurs de chargeur ; il n’y a pas de
sculpture spécifique par chargeur. Les textures HD restent expérimentales.
