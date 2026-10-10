# Vector Fields 0.18.0 — Modules d’inventeur et dieselpunk

Huit formes nouvelles utilisent les deux atlas de la version 0.17 : une
culasse, une optique, une réserve et un refroidisseur pour chaque thème.
Elles restent compatibles avec les quatorze finitions et les trois
plateformes de chargement. Les 52 modèles précédents sont conservés à l’identique.

| Emplacement | Rome / Inventeur | Dieselpunk |
| --- | --- | --- |
| Culasse | Roue dentée ouverte, six rayons et manivelle décalée | Arbre à cames, ressort hélicoïdal et levier |
| Optique | Double anneau, graduations en relief et molette | Colonne périscopique, capot profilé et réglage latéral |
| Batterie | Tambours de remontage, courroies et arceau | Deux colonnes d’huile, tuyauterie et manomètre |
| Refroidissement | Deux éventails de sept lamelles séparées | Deux faisceaux de quatre tubes avec collecteurs et ailettes |

Ces détails sont des volumes du modèle, avec des espaces ouverts entre les
rayons, les lamelles et les tuyaux. Les cadrans et les matières réemploient
les textures existantes, sans nouvel atlas.

## Essayer

Dans **F11**, utiliser **Inventeur** ou **Dieselpunk** sous l’aperçu, puis
**Appliquer**. Les boutons chargent un ensemble complet et sa finition :
Arche et les modules Nomade pour Inventeur, Gyre et les modules Bastion pour
Dieselpunk, avec les quatre pièces propres au thème. L’équipement opérateur
reste conservé. **Annuler** permet de retrouver la configuration validée.

Pour composer librement, les nouveaux objets se trouvent en **page 3** des
emplacements Culasse, Optique, Batterie et Refroidir. Changer une pièce
conserve la finition de son emplacement. Les nouvelles formes acceptent aussi
les autres finitions et peuvent être mélangées avec les anciens modules.

Commandes : `vf_reference 4` pour Inventeur, `vf_reference 5` pour Dieselpunk,
puis `vf_commit`. Les identifiants suivent `r01_<emplacement>_inventor` et
`r01_<emplacement>_diesel`, pour `chamber`, `optic`, `power` et `cooling`.

## Intégration et limites

Le constructeur est `build_reference_themes.py`. Les culasses utilisent le
socket animé `R01_Bolt` des trois rigs ; les autres pièces utilisent `Bone76`.
Les culasses reculent au tir et pendant le cycle existant de rechargement.
Les roues, cames et aiguilles n’ont pas de mouvement indépendant. Les coûts,
les statistiques et le fonctionnement du tir restent ceux du prototype.

Le catalogue comporte 60 pièces R1, 248 objets d’équipement et 924 entrées
de lootpool. Les quatre emplacements enrichis offrent six formes ; les huit
châssis et les quatre formes des sept autres emplacements restent disponibles.
L’ensemble représente 169 869 312 combinaisons de formes.

## Vérification reproductible

`build.ps1` compile les DLL et exécute les contrôles des anciens modèles et
des huit nouveaux. `tests/reference_themes_test.py --mode assets` vérifie
les formes distinctes, les limites StudioMDL, les UV isotropes, les quatorze
finitions, les lentilles additives et les sockets de culasse animés.

`--mode native` sélectionne les ensembles par les boutons réels, capture
chaque pièce sous deux angles, teste le tir et le rechargement des deux
ensembles sur les trois plateformes, et recharge deux sauvegardes avec
une finition d’optique différente. L’audit commun parcourt 1 700 assemblages
individuels et par paires ; il ne constitue pas une inspection visuelle
exhaustive de toutes les combinaisons.

[Les huit pièces dans le moteur](../build/r01-themed-modules.jpg) ·
[Assemblages et vues en main](../build/r01-themed-sets.jpg).
Les rapports sont `build/reference-themes-assets.json`,
`build/reference-themes-native.json` et `build/current-release-verification.json`.

Résultats du 9 octobre : compilation réussie, 12 122 contrôles C++, 840
couples forme/finition validés, 32 captures natives, six rechargements,
deux reprises de sauvegarde et 1 700 assemblages acceptés. Les 65 modèles
R1 et opérateur installés correspondent aux fichiers compilés.
