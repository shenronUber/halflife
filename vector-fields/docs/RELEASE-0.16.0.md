# Vector Fields 0.16.0 — Arche et Gyre

Deux châssis supplémentaires réutilisent les douze finitions et les onze autres
interfaces R-01. Arche remplace la poutre centrale par des branches effilées et
un mécanisme suspendu ; Gyre utilise un noyau cylindrique, trois cerclages et
quatre longerons hélicoïdaux. Les modèles sont générés de façon reproductible
dans `build_reference_chassis.py`.

## Essayer

F11 → Châssis → Arche ou Gyre → Appliquer. Ces boutons changent uniquement le
châssis. Les objets figurent également en page 4. Les préréglages Atelier,
Circuit, Nomade et Bastion remplacent toujours l’ensemble des douze pièces.
Arche et Gyre utilisent le chargement par-dessous. Les boutons Latéral et
Dessus sélectionnent les châssis Traverse et Zénith.

## Intégration

- Huit châssis, quatre variantes dans chacun des onze autres emplacements.
- 52 pièces R-01, 240 objets d’équipement, 708 entrées de lootpool.
- Coûts, repères, animations et identifiants des anciennes pièces conservés.
- Identifiants persistants : `r01_receiver_arch`, `r01_receiver_gyre`.
- Textures originales : métal sombre, métal usiné, peinture ocre, céramique,
  cuivre, déclinés par les douze finitions existantes.

## Vérification reproductible

`build.ps1` compile les DLL, les modèles et les tests de catalogue. Le test
`tests/reference_chassis_test.py --mode assets` contrôle la limite de sommets,
les ouvertures réelles d’Arche, les UV isotropes, les douze finitions et le
catalogue. `--mode native` produit les captures du moteur et contrôle les deux
raccourcis, quatre ensembles de modules sur chaque châssis, les huit couples
chargeur/châssis en tir et rechargement, puis les deux sauvegardes avec finitions
mélangées. L’audit commun couvre 1 284 assemblages individuels et par paires.
Les rapports et la planche `r01-sculpted-chassis.jpg` sont dans `build/`.

Ces essais ne constituent pas une inspection visuelle exhaustive des 33 554 432
combinaisons. Le tir et la durée effective de rechargement restent ceux du MP5 ;
le modèle au sol et en troisième personne reste le modèle stock. Les deux
châssis n’introduisent pas encore de mécanisme central animé supplémentaire.

Résultats du 8 octobre : compilation réussie, 12 122 contrôles C++ validés,
46 captures natives pour Arche/Gyre, huit couples chargeur/châssis testés,
deux reprises de sauvegarde réussies et 1 284 assemblages acceptés. Les 57
modèles déployés correspondent aux sources compilées. La migration des
anciennes sauvegardes passe également. Les boutons ont été revérifiés dans
le menu de gameplay avec les DLL finales. Aperçus mesurés à environ 1,3 ms
CPU par image, sans chargement de modèle après préchauffage (mesure locale,
qui ne représente pas le temps GPU).
