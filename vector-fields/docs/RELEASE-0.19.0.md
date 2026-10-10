# Vector Fields 0.19.0 — Inventaire de jeu

Le menu de jeu propose deux pages, **Opérateur** et **Arme**. Choisir un
emplacement à gauche, sélectionner un objet dans la liste à droite, puis
**Équiper**. **Annuler** rétablit les choix précédents. La molette parcourt la
liste ; sur l’aperçu elle règle le zoom. Le glisser fait tourner le modèle.

Les flèches de collection filtrent uniquement la liste. Cliquer son intitulé
rétablit toutes les collections. Aucun filtre n’équipe un ensemble. Les outils
de préréglage, les changements libres de finition et les essais de modèles
restent disponibles avec **F6**, dans l’espace développeur.

## Objets accessibles

- **854 objets d’arme** : 61 géométries × 14 finitions, chacun avec un identifiant
  et un nom distincts. Exemple : « Culasse à manivelle des abysses ».
- **70 objets de tenue** : cinq zones × quatorze collections. Rome / Inventeur
  et Dieselpunk ajoutent chacun masque, veste, gants, pantalon et bottes.
- **24 accessoires** : épaules, ceinture, bouclier et spécial conservent leurs
  modèles provisoires et peuvent être retirés.

Les **948 objets sont disponibles individuellement** dans cette version de
prototypage. Le catalogue technique contient aussi 165 objets historiques ou
modèles de travail, pour un total de 1 113 entrées hors emplacement vide.
Les formes et matières d’arme ne créent pas encore de nouveaux comportements
de combat : capacité, cadence et durée de rechargement restent celles du MP5.

## Châssis et alimentation

Le châssis détermine la position du chargeur. **Arche supérieure** ajoute une
seconde possibilité d’alimentation par le haut, à côté de Zénith. Ses branches
courbes restent ouvertes ; son collier est supérieur et son support d’optique
est déporté. Elle réutilise les quatorze matières existantes, les quatre modèles
de chargeur et le cycle de rechargement supérieur.

| Position | Châssis |
| --- | --- |
| Dessous | Atelier, Circuit, Nomade, Bastion, Arche, Gyre |
| Latérale | Traverse |
| Dessus | Zénith, Arche supérieure |

Changer le châssis conserve les onze autres objets et leurs finitions.
Les optiques se fixent au support correspondant. Neuf châssis, quatre variantes
sur sept emplacements et six sur les quatre autres donnent 191 102 976
combinaisons de géométries ; les tests couvrent chaque pièce et chaque paire
d’emplacements, sans prétendre parcourir toutes les armes complètes.

## Identités et sauvegardes

Un objet de jeu lie désormais son modèle et sa finition de façon immuable.
Le serveur refuse une transaction qui combine son identifiant avec une autre
finition. Les modèles de travail sans finition liée restent réservés au dev.
Les anciens objets et leurs finitions séparées sont convertis vers les
identifiants d’inventaire correspondants au retour au jeu.

Le protocole réseau passe à **4**, avec des indices d’équipement sur 16 bits :
`VFBuild` fait 64 octets, `VFState` 75. Les indices d’apparences restent sur
8 bits. Les deux DLL et les catalogues doivent être déployés ensemble.
Les sauvegardes utilisent toujours les clés textuelles stables, indépendantes
de l’ordre des catalogues. Le lancement ouvre l’inventaire sans imposer de tenue.

## Création des tenues

Les deux atlas ont été générés avec **imagegen intégré**, à partir du dépliage
GIGN existant, puis intégrés au modèle commun. La géométrie et les cinq zones
restent communes aux quatorze tenues. Prompts exacts et images sources :

- [Inventeur : prompt](../assets/personas/roman-inventor/prompt.txt),
  [atlas](../assets/personas/roman-inventor/texture-atlas.png).
- [Dieselpunk : prompt](../assets/personas/dieselpunk/prompt.txt),
  [atlas](../assets/personas/dieselpunk/texture-atlas.png).

## Vérification

- Compilation client/serveur et validations C++ des objets, sauvegardes et effets.
- Contrôles des 70 zones de tenue, des impacts et des animations du corps commun.
- Contrôles géométriques et UV des nouveaux châssis et modules ; les finitions
  utilisent les mêmes géométries.
- `inventory_engine_test.py` : vrais clics, filtre sans équipement automatique,
  changement d’une seule zone, deux nouvelles tenues, nouveau châssis supérieur,
  quatre rechargements, six optiques, sauvegarde/reprise et migration 0.18.
- Audit moteur : 1 753 assemblages de pièces et 1 113 objets chargés sans rejet.
- `architecture_engine_test.py` : validation côté serveur, refus de finition
  falsifiée, migration après réordonnancement des catalogues et permissions.
- `r01_styles_multiplayer_test.py` : deux clients locaux, arrivée tardive,
  indices supérieurs à 255, finitions par objet et triche désactivée.
- `current_release_test.py` : lanceur, métadonnées et modèles réellement installés.

Les rapports et captures se trouvent dans `vector-fields/build/` et
`runtime/vector-engine/vf_visual/scrshots/`. L’arme portée en troisième personne
conserve son modèle historique ; l’assemblage détaillé est visible dans
l’inventaire et à la première personne.
