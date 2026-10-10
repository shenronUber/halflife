# Vector Fields 0.20.7 — Équipements, effets, morts et intégration

Publication du 10 octobre 2026. GitHub était à la version 0.14.0 : cette livraison
rassemble les ajouts des versions 0.15 à 0.20.6 et les corrections d’intégration
0.20.7. Les notes intermédiaires sont conservées dans ce dossier et dans
[l’historique](../CHANGELOG.md).

## Équipements et identité visuelle

- 948 objets sélectionnables individuellement : 854 pièces R1, 70 pièces de tenue
  et 24 accessoires provisoires. Chaque variante possède un nom, un identifiant
  et une finition fixe ; tous les objets sont accessibles dans ce prototype.
- 61 géométries d’arme dans quatorze finitions, dont Rome / Atelier d’inventeur et
  Dieselpunk, avec leurs tenues GIGN assorties.
- Châssis sculptés, variantes à chargeur inférieur, latéral ou supérieur, culasses
  et modules thématiques. Le châssis détermine le montage du chargeur.
- Les gants et manches en première personne suivent séparément les équipements
  du personnage. Dépliage anatomique, doigts adoucis, retrait du boîtier et du
  bracelet, prise latérale détendue et rechargement supérieur incliné vers la gauche.
- Animations des porteurs R1 en tiers-personne, poignées avant, marche, course,
  accroupissement et contacts des mains pendant les rechargements. Ateliers 3D
  pour examiner les modèles, UV et animations hors du jeu.

## Combat, effets et voix

- Huit présentations de tir R1 : flashes, traces, particules, impacts et 40 sons
  de tir/contact. Une salle de contrôle dédiée permet de les comparer.
- Huit éléments, huit réactions et cinq états tactiques ; badges anglais,
  durées reçues du serveur, halos sur les bras et seize décors HUD originaux
  animés sur quatre images chacun.
- Six opérateurs avec voix originales, provocations et réponses contextuelles,
  dont les échanges avec les bots. Une banque de 102 cris non verbaux accompagne
  les morts selon leur cause.
- Salle GIGN avec quatre cibles réactives. Six impacts d’un même élément en trois
  secondes activent son état ; les cibles meurent et réapparaissent.

## Morts et démembrements

- Cadavres animés conservant la tenue, les parties manquantes et la cause du décès.
  Atlas de seize profils élémentaires et dix mouvements importés sur le squelette GIGN.
- Tête, bras et jambes détachables ; chaque perte produit une pièce anatomique et
  trois petits fragments physiques, avec blessures, sang dispersé et particules.
- Seize signatures sonores de mort et dix-sept sons d’arrachement se superposent
  au cri sur des canaux positionnels distincts. Un joueur rejoignant tardivement
  reçoit les cadavres et fragments existants sans rejouer les anciens sons.
- Les fragments conservent maintenant les finitions indépendantes manche/gant et
  pantalon/botte : 196 couples natifs, avec les mêmes vingt maillages physiques.

## Corrections d’intégration de la 0.20.7

- Les tests natifs de la salle et des cris utilisent les DLL courantes et vérifient
  leurs empreintes. Les contrôles manquants sont inscrits dans la validation centrale.
- La salle est générée depuis son code d’auteur, avec cache des sources, textures,
  outils et sorties. Build, lancement et essais isolés utilisent ce même BSP.
- Les deux cartes générées font partie des 326 fichiers vérifiés au déploiement,
  comprenant 76 modèles, les DLL, catalogues, effets et sons requis.
- Le lanceur des bots déploie le même inventaire et installe la mise à jour validée
  du moteur. Il refuse une interface incompatible avant de remplacer les assets.
- Les générateurs incrémentaux, contrats de modèles et documentation des protocoles
  sont partagés pour faciliter les prochaines extensions.

## Validation

Compilation client/serveur sans erreur ; 58 tests unitaires Python, tests de
politiques C++ et 19 contrôles d’assets réussis. Les essais ciblés dans le moteur
couvrent les tirs réels, 139 morts de cibles et 23 morts de joueurs, les finitions
mélangées, le menu, la sauvegarde/restauration et les budgets de cadavres/fragments.

Un serveur local à trois clients vérifie la mort distante, la réapparition et
l’arrivée tardive. Le moteur du lanceur bots accepte les nouvelles finitions ;
un essai avec deux vrais bots valide Metamod et le combat. Les 75 modèles de la
référence locale, hors modèle de fragments volontairement modifié, restent identiques.

[Rapport daté et empreintes](validation/maintenance-0.20.7.json).
Ces essais sont ciblés ; ils ne constituent pas un parcours complet de toutes les cartes.

## Lancement et sources

- `Jouer - Vector Fields.cmd` : jeu et inventaire actuels.
- `Jouer - Bots jk_botti.cmd` : laboratoire avec serveur local et bots.
- F1/F2 : personnage ; F11 : arme ; F3 : effets ; F4 : salle ; F8 : morts.
- Les lanceurs `Atelier` ouvrent les outils d’animations et d’écoute.

```powershell
powershell -ExecutionPolicy Bypass -File vector-fields/build.ps1
python vector-fields/play.py --visual-lab --deploy-only
python vector-fields/validate.py --suite native
python vector-fields/validate.py --suite multiplayer
```

Le dépôt livre le code, les catalogues, sources visuelles/sonores, recettes,
ateliers, tests et rapports. Les ressources des jeux installés, environnements
locaux et binaires compilés sont générés séparément ; voir le [guide](../README.md)
et le [contrat du moteur](../engine/README.md) pour les dépendances locales.
