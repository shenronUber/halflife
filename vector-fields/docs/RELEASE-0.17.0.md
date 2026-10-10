# Vector Fields 0.17.0 — Rome / Inventeur et Dieselpunk

Deux nouvelles banques de matières sont intégrées aux 52 pièces R-01.
Elles conservent la grille fonctionnelle 4 × 4, avec une conception visuelle
plus libre que les premières propositions archivées.

- **Rome / Atelier d’inventeur** : noyer assemblé, poulies et cordages,
  toile portant des tracés de construction, bronze patiné, ivoire et cristal.
- **Dieselpunk** : carrosserie bleu pétrole nervurée, fonte huileuse,
  radiateurs en cuivre, bakélite rouge, huile sous verre et cadrans analogiques.

Les textures ont été générées avec l’outil intégré image_gen. Les atlas,
les prompts exacts, les sources de génération et les exports sont dans
[les banques R-01](../assets/r01/variants/README.md). Les versions initiales
sont conservées sous `texture-atlas-v1.png` et `prompt-v1.txt`.

## Essayer

**F11 → FINITION → Toute l’arme / Cette pièce → flèches → Appliquer**.
Rome / Inventeur porte l’indice 12 et Dieselpunk l’indice 13. Les deux styles
fonctionnent sur Atelier, Circuit, Nomade, Bastion, Traverse, Zénith, Arche et
Gyre, ainsi que sur les onze autres emplacements. Ils peuvent être mélangés.

Le noyau de Gyre utilise désormais la matière d’habillage répétée, et son
décor d’identité reste sur une seule petite plaque supérieure. Cela évite
les dessins et les cadrans répétés autour du cylindre. Les contacts avec
les modules, les animations et les paramètres de gameplay sont conservés.

Le catalogue contient 14 finitions, 728 variantes d’armes, 60 pièces GIGN et
24 équipements provisoires : **812 entrées de lootpool**, pour 240 objets
d’équipement. Les deux nouvelles collections sont réservées aux armes.

## Vérifications

Compilation des modèles et DLL réussie ; 12 122 contrôles C++ passent.
Les 728 couples pièce/finition ont la même géométrie à forme identique,
avec au plus 84 textures par modèle pour une limite StudioMDL de 100.
Les anciens indices de finition restent inchangés ; seule la géométrie de
Gyre reçoit la petite plaque et le nouveau découpage des matières.

Le test `build/inventor-native-check.py` produit 22 captures à 1920 × 1080 :
Arche et Gyre, isolés et assemblés, en main et pendant le rechargement, dans
les deux finitions. Il vérifie les flèches de l’interface, l’application,
un mélange Rome/Dieselpunk après sauvegarde et chargement, puis l’audit
commun de 1 284 assemblages sans rejet.

[Planche des captures natives](../build/r01-inventor-finishes-in-game.jpg).
Rapports : `build/inventor-finishes-verification.json`,
`build/inventor-compatibility.json` et `build/current-release-verification.json`.

Les engrenages, aiguilles et liquides sont des détails peints dans les textures,
sans animation supplémentaire. Les essais visuels portent sur des assemblages
représentatifs. Le modèle en troisième personne reste celui du jeu de base.
