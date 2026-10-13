## Commande de lancement commune et contrôles de démarrage — 2026-10-13

- Le lanceur applique la graine et la variante avant une seule commande `map`. La commande redondante est retirée ; les configurations d'arrivée continuent de venir du registre des cartes.
- Les tests natifs utilisent désormais cette commande de production pour `vf_modular` et `vf_tiles`, au lieu d'une copie de l'ancien lanceur. Ils contrôlent la première graine générée, les collisions, la variante mélangée et un tir avec l'arme reçue.
- Huit tests unitaires supplémentaires couvrent les cartes du registre, les graines limites et invalides, les cartes importées, les configurations d'arrivée et le refus des installations non validées ou altérées.
- Le test réseau des modules attend désormais la génération du serveur et la connexion confirmée des deux clients avant ses commandes de contrôle. Les sondes ne partent plus pendant le sign-on ; six tests unitaires couvrent l'attente, les marqueurs incomplets, l'arrêt d'un processus et le délai maximal.
- Validation finale : 124 tests unitaires, 17 groupes C/C++ et 58 étapes réussies. Paquet `20261013-100010-e8358306` installé puis revérifié ; [rapport et cause du test réseau corrigé](docs/validation/launcher-hardening-2026-10-13.json).

## Modules jouables, menu de cartes et ambiances — 2026-10-13

- F4 ouvre un menu commun pour les cartes locales, les huit variantes de modules et les cartes CS/TFC importées en exploration. Les descriptions restent des données ; les commandes de lancement n'utilisent que des identifiants validés.
- `vf_tiles` assemble quatre à six modules, avec quatre familles d'intérieurs et deux variantes chacune. Les raccords, collisions et parcours réutilisent la génération serveur ; la grille `vf_modular` reste disponible.
- Cinq ambiances longues bouclent dans les deux cartes modulaires : vent, tourbillon et trois grincements de structures. Les recettes, sources et empreintes sont conservées.
- Build installé `20261013-040215-1514f323` : 58 étapes obligatoires réussies, avec les huit variantes, sauvegarde/restauration, chargements via le menu et deux clients réseau. Revérification avant publication : 110 tests unitaires et 17 groupes C/C++, puis concordance des sources, du moteur et des fichiers installés.
- [Guide des modules](docs/TILE-LABORATORY.md) et [rapport de publication](docs/validation/github-publication-2026-10-13.json).

## Dégâts anatomiques, builds et cache de poses — 2026-10-13

- Les tirs SDK conservent leur localisation anatomique malgré les indicateurs de fragments `NEVERGIB` et `ALWAYSGIB`. Tests ajoutés sur les véritables chemins MP5, 9 mm et chevrotine, avec armure et sauvegarde.
- Les empreintes de construction incluent protocole réseau, patches moteur, ressources et bibliothèques. Le contrôle du paquet installé et la publication vérifient aussi l'identité du moteur ; les sources supprimées ne restent plus dans le cache de compilation.
- Rétention automatique : candidat installé, un précédent candidat validé et un ancien mod. Rapports et sauvegardes archivés avant retrait ; 32 captures par session retirée. Sources Blender, textures et ateliers conservés. Environ 42,5 Go distincts libérés après reconstruction et installation finales.
- Cache serveur de poses à entrées exactes, limité à 32 joueurs (209 352 octets), sans changement de protocole. Réévaluation lors de toute variation de temps, état ou modèle ; suppression du double calcul du torse et des écritures dans le cache de collision historique inadapté.
- Deux clients réels : 4 096 requêtes de poses identiques passent de 67,92 à 2,08 ms en médiane. Cette mesure isole les poses et ne représente pas un multiplicateur de FPS.
- Validation : 110 tests unitaires, 16 suites C/C++, 18 tests moteur, 53 étapes de publication ; 25 cas anatomiques, 8 chutes, 70 poses et 1 400 hitboxes. Écart maximal de 0,112 unité. Les 6 616 fichiers installés et les empreintes des sources ont été revérifiés.
- Rapport : `docs/validation/maintenance-2026-10-13.json`.

## Transition de rechargement et spasme du dos — 2026-10-12

- La transition mémorise la visée réellement évaluée au-dessus de la démarche,
  au lieu de la valeur brute des entvars. Le rechargement ne rééchantillonne
  plus brièvement la pose de visée basse à partir d'un personnage droit.
- Reproduction et comparaison image par image sur les trois montages,
  debout et accroupi : saut maximal du torse réduit de 29,07° à 0,30° entre
  deux images ; 96 images analysées avant et après.
- Les 61 poses et 1 220 hitboxes restent concordantes. Les DLL vérifiées sont
  installées dans le runtime principal avec une sauvegarde de la version précédente.
- Rapport : `docs/validation/reload-transition-2026-10-12.json`.

## Frappe descendante à l'avant du canon — 2026-10-12

- La touche V utilise le geste de la référence fournie : la main gauche lâche
  et reste libre, la droite relève l'arme puis l'abat, canon en tête.
- Six variantes en première personne et trois montages debout/accroupi en
  troisième personne, avec suivi vers le bas et reprise de la prise normale.
- La variante accroupie part de la pose composée réellement utilisée par le
  jeu et la rejoint à la fin, sans bascule du torse ou du canon vers le sol.
- Contact au repère animé de 13/30 seconde, un seul impact serveur, 35 dégâts
  de base, portée 40, sans munition. Les interruptions gardent leur priorité.
- Géométrie des douze pistes, essais natifs et réseau, 61 poses / 1 220 hitboxes
  avec mesures supplémentaires à l'armement, au contact et au suivi.
- Rapport : `docs/validation/barrel-strike-2026-10-12.json`.

## Contrôle de la compilation réunie — 2026-10-12

- Wall run, saut depuis la suspension et coup de crosse vérifiés dans le
  runtime principal ; les anciennes revues privées restent distinctes.
- Les porteurs de mêlée utilisent le calcul partagé des hitboxes et gardent
  le corps visible en vue subjective. La pose extérieure suit le paquet serveur.
- La mise à jour du porteur ne remplace plus le modèle du coup en cours.
- Les effets des statuts restent sur les gants et manches pendant l’inspection
  et la mêlée ; les pièces d’arme restent exclues de cet effet.
- Contrôles des trois alimentations avec vérification du modèle réellement
  chargé, 43 poses / 860 volumes, huit cas de marche, 21 cas de dégâts et
  huit chutes, six configurations de frappe et essais entre plusieurs clients.
- Installation sous contrôle des empreintes, avec sauvegarde des dix fichiers
  remplacés. Rapport : `docs/validation/integration-2026-10-12.json`.

## Démembrement, poses de collision et chutes — 2026-10-12

- Dégâts cumulés par région après armure : perte seulement à la mort, au-delà
  de 50 % de la vie maximale et avec le coup fatal sur cette même région.
- Compteurs sauvegardés, réinitialisés à la réapparition ; aucun membre choisi
  au hasard pour un décès central ou non localisé. Quatre fragments par perte.
- Évaluateur d'os partagé par le serveur et le renderer GIGN/R1 : démarche,
  transitions, torse, glissade, appuis de franchissement et gestes de casque.
  Recherche des traces étendue aux hitboxes posées sans changer le volume de déplacement.
- Une chute conserve ses dégâts et sa douleur, sans activer d'état élémentaire.
- Régressions natives des seuils, du coup fatal, des fragments, des sauvegardes,
  de huit chutes et des vingt matrices de hitbox dans les poses affichées.

## Maintenance et mesures natives — 2026-10-12

- Contrat des 22 emplacements partagé avec les harnesses Python ; migrations,
  nouvelles ressources casque et gestes intégrés aux validations centrales.
- Cartes d’os conservées pendant les changements de pose/finition ; listes
  compactes des cadavres/fragments actifs, avec les mêmes budgets physiques.
- Anciens tests de menu et d’architecture isolés ; publication atomique des
  preuves sous verrou, accès aux ressources originales en lecture seule.
- Sons/HUD de casque inclus dans le build ; filtrage audio réutilisé par cache
  vérifiant les sources, l’encodeur et les sorties.
- Retours casque rattrapés après un tick tardif et avant un nouveau geste :
  la réplique de fermeture reste transmise une seule fois aux deux clients.
- Profiler CPU/GPU désactivé par défaut ; comparaison native de sept scènes
  répétée trois fois sur GTX 980 Ti à 1280 × 720.

## Confort et son de glissade — 2026-10-11

- Balancement de marche réduit de 90 % pendant la glissade, pour la caméra et l'arme ; valeur normale restaurée à la sortie.
- Frottement original de 1,2 seconde, synchronisé avec la durée maximale du déplacement ; arrêt immédiat au saut, au relâchement de Ctrl et aux autres sorties.
- Bruit de pas remplacé pendant la glissade ; tir et rechargement conservés. Son prédit localement et diffusé par le serveur aux autres joueurs.
- Export sonore réutilisé et vérifié par empreinte ; tests du déplacement et du mixeur audio réel, sans recompilation des animations.

## Corrections de persistance et stockage — 2026-10-11

- Sauvegarde/restauration explicite des déplacements : accrochage, phase armée,
  franchissement, remontée et glissade ; anciennes sauvegardes compatibles.
- Délai de dégainé transmis à la prédiction des armes : tir bloqué jusqu’à la fin
  de la transition d’accrochage armé.
- Contrats de validation indépendants des anciennes copies locales ; transition
  de dégainé distinguée des huit secteurs de visée, précision réseau explicitée.
- Tests C++ recompilés par la suite `policy`, nouveaux tests de reprise et
  d’isolation des ressources, régression native de sauvegarde entre processus.
- Sessions natives temporaires, ressources immuables partagées, logs/captures
  conservés ; nettoyage ciblé des anciens runtimes avec archivage des preuves.

## Atelier Blender — 2026-10-11

- Blender 4.5.14 LTS portable et Blender Source Tools installés dans le projet, avec un profil isolé et les empreintes des téléchargements officiels.
- Projets éditables des mains R1 et du corps : 114 pistes, textures des 19 skins incluses, commandes lisibles des doigts et poignées IK des mains.
- Export SMD des os du jeu vers les dossiers de retouches existants. Contrôles d'alignement, de déformation et de compilation GoldSrc ; aucun déploiement automatique.

## Atelier des prises et animations — 2026-10-10

- Suspension et remontée du corps adaptées de sources Mixamo vérifiées ; franchissement bas avec prise, appui et retrait des mains.
- Animation de lâcher de 0,30 seconde, avec gravité et atterrissage historiques.
- Main droite de suspension articulée : dix-neuf os de doigts ajoutés aux seuls porteurs de déplacement ; paumes contraintes après interpolation, poses de doigts conservées.
- Atelier fragMOTION installé sur G:, modèles des mains et du corps, exports SMD validés et retouches conservées hors des fichiers générés. Lanceurs d'édition et d'application.
- Retouches de la suspension transmises aux secteurs de caméra ; direction de coude authored conservée par la contrainte.

## DÃ©placements et prises de rebord â€” 2026-10-10

- Franchissement dâ€™un obstacle bas, saisie en sautant, suspension sans remontÃ©e automatique, remontÃ©e et lÃ¢cher explicites.
- Suspension gauche et tir Ã  droite dans toutes les directions, avec poses par-dessus lâ€™Ã©paule. Rechargement manuel, automatique et dÃ©jÃ  engagÃ© bloquÃ©s pendant la suspension.
- Glissade longue avec faible friction, jambes et bottes visibles dans les finitions Ã©quipÃ©es. La collision, la gravitÃ©, le saut normal et les dÃ©gÃ¢ts de chute historiques sont conservÃ©s.
- Paumes contraintes sur le rebord aprÃ¨s interpolation du moteur ; doigts dÃ©pliÃ©s sur la prise, pouce posÃ© au-dessus. Les animations historiques du R1 sont prÃ©servÃ©es dans des modÃ¨les dÃ©diÃ©s.
- Parcours F9 et essais de prÃ©diction, assets, moteur natif et rÃ©plication rÃ©seau.

# 0.20.7 â€” Corrections dâ€™intÃ©gration â€” 2026-10-10

- La validation centrale inclut la salle de test, la matrice des cris contextuels et les finitions des fragments. Les essais utilisent les DLL courantes et vÃ©rifient leurs empreintes.
- Les fragments gardent les textures du gant et de la manche, ou de la botte et du pantalon, indÃ©pendamment. Vingt maillages et les banques de textures existantes servent aux 196 couples ; les indices uniformes historiques sont conservÃ©s.
- La salle GIGN est gÃ©nÃ©rÃ©e depuis le code de la carte de base, avec un cache vÃ©rifiant sources, outils et sorties. Build, lancement et essais isolÃ©s partagent ce rÃ©sultat. Les deux cartes gÃ©nÃ©rÃ©es sont contrÃ´lÃ©es dans le dÃ©ploiement. Le lanceur bots dÃ©ploie le mÃªme inventaire de DLL, modÃ¨les et cartes. Il applique la mise Ã  jour validÃ©e du moteur et refuse une interface incompatible avant de remplacer les assets.
- Tests de rÃ©gression : cache et idempotence de la carte, BSP absent ou pÃ©rimÃ©, correspondance des deux finitions, dÃ©cÃ¨s rÃ©el en tenue mÃ©langÃ©e et conservation rÃ©seau pour un arrivant tardif.

# Historique Vector Fields

## Morts ancrees et variations - 2026-10-10

Les morts automatiques demarrent dans la pose et l orientation du personnage
vivant. Le bassin reste au point de mort pendant la chute ; les cadavres au sol
ne glissent plus avec le recul des degats. Chaque effet, la mort classique et
la perte de tete disposent de trois gestuelles, sans repetition consecutive.
Les impacts marques tiennent compte de la direction du tir. Trois contractions
electriques se terminent par des poses distinctes. L atelier utilise ces memes
variantes compilees. Les 77 sequences historiques et leurs indices sont conserves.

## Sons courts sans etirement - 2026-10-10

Les 33 signatures initiales de mort elementaire et d arrachement retrouvent leur
duree naturelle. Les 17 explosions de tete sont generees directement pour deux
secondes. Le traitement de niveau garde chaque echantillon a sa place, sans
etirement ni remplissage. Les 50 effets durent entre 1,06 et 2,08 secondes,
avec le niveau renforce ; les cris existants restent inchanges.

## Demembrement permanent et sons prolonges - 2026-10-10

Toutes les morts ordinaires des personnages compatibles retirent une zone : celle
de l impact mortel, ou un bras pour les impacts centraux et non localises.
Un seul membre physique part par zone, sans les trois segments qui le doublaient.
Les 50 sons generes couvrent les morts, les arrachements et les explosions de tete.
Ils durent quatre secondes et leur suite sonore reste audible. Le mix donne plus
de place aux effets. Une tete retiree joue sa seule explosion humide elementaire,
sans cri du personnage. Les choix explicites de l atelier restent disponibles.

## Sons elementaires et sang disperse â€” 2026-10-10

Seize sons de mort et dix-sept sons d arrachement generes, dont le neutre.
Cri, cause et arrachement se superposent sur trois canaux natifs distincts,
avec volumes independants et diffusion positionnelle aux joueurs presents.
La synchronisation tardive ne rejoue aucun son ancien. Le sang des coupes
utilise maintenant des gouttes rouges sombres dispersees avec de la gravite,
sans l ancienne gerbe verticale ni sa variation de palette.
Ecoute : `Atelier - Sons de mort.cmd`. Details : `docs/DEATH-SOUNDS.md`.

## Atlas des morts et fragments Ã©lÃ©mentaires â€” 2026-10-10

Sept morts Mixamo ajoutÃ©es, portant les imports Ã  dix. Inventaire des 886 fichiers
d'une banque publique et inspection de 24 candidats. Seize profils associent
les Ã©lÃ©ments et rÃ©actions Ã  leurs mouvements ; atlas et catalogue paginÃ© dans F8.
Chaque perte crÃ©e une piÃ¨ce anatomique entiÃ¨re et trois petits fragments physiques,
avec traÃ®nÃ©es de sang et particules de l'effet. Appuis adaptÃ©s au maillage dÃ©coupÃ©,
fragments posÃ©s au sol et durÃ©e limitÃ©e, synchronisation des nouveaux observateurs.
DÃ©tails et essais dans `docs/DEATH-ATLAS.md`.

## BibliothÃ¨ques de morts importÃ©es â€” 2026-10-10

Trois morts Quaternius/KayKit transfÃ©rÃ©es et compilÃ©es sur les 28 os GIGN,
appuis et pose finale corrigÃ©s pour nos proportions. SÃ©lecteur F8, variations
automatiques des morts ordinaires, dÃ©membrement et effets indÃ©pendants.
Les signatures suivent le torse animÃ© ; les sÃ©quences historiques sont conservÃ©es.
Exports donneurs et provenance archivÃ©s, essais natifs des membres, du menu
et de la sauvegarde. DÃ©tails dans `docs/DEATH-VISUALS.md`.

## Textures de dÃ©membrement â€” 2026-10-09

Cinq matÃ©riaux de plaie, trois sources originales sobres, mesures prÃ©cises et UV
continus Ã  16 pixels/unitÃ©. Coupes planes des bras et cuisses, bassin conservÃ©,
Ã©tui sÃ©parÃ©, raccords sur les mÃªmes os et Ã©clairage des faces basses corrigÃ©.
Gros plans natifs et test tÃªte/Ã©lectricitÃ© ; dÃ©tails dans `docs/WOUND-TEXTURES.md`.

## Prototype de morts â€” 2026-10-09

Cadavres GIGN animÃ©s pour le joueur et les cibles, tÃªte, bras gauche/droit et
jambes gauche/droite dÃ©tachables avec fragments et blessures. Contractions
Ã©lectriques puis chute, effet et tenue conservÃ©s sur le cadavre. Laboratoire
F8 ; rÃ¨gles de dÃ©gÃ¢ts localisÃ©s reportÃ©es. Ressources compilÃ©es et dÃ©ployÃ©es
par le lanceur, validation des modÃ¨les, essais natifs et rÃ©seau dÃ©diÃ©s.

## 0.20.6 â€” 2026-10-09

HUD : remplacement des motifs provisoires des huit Ã©lÃ©ments et huit rÃ©actions
par seize textures originales, soit 64 images peintes. Animation par fondu,
ancrage et opacitÃ© RGBA communs, zone de visÃ©e protÃ©gÃ©e, intÃ©gration
au build incrÃ©mental et vÃ©rification des ressources livrÃ©es.

Maintenance Ã  partir de la 0.20.5 : traits de modÃ¨les et porteurs partagÃ©s entre
Python, client et serveur ; gÃ©nÃ©ration incrÃ©mentale des piÃ¨ces et animations,
dÃ©pendances transitives et empreintes des sorties vÃ©rifiÃ©es. Un seul format de
catalogue de finitions Ã©vite les reconstructions provoquÃ©es par deux auteurs.

Suites de validation regroupÃ©es, tests unitaires de rÃ©gression ajoutÃ©s, prises
avant et tiers-personne incluses dans le build. Les tests natifs utilisent les
DLL actuelles. VÃ©rification de livraison Ã©tendue aux porteurs tiers-personne,
DLL, catalogues et effets. Contrats moteur/rÃ©seau documentÃ©s depuis leurs
constantes C++. Aucune modification du protocole, des sauvegardes ou des modÃ¨les.

## 0.20.5 â€” 2026-10-09

Signatures des Ã©tats sur les bords de lâ€™Ã©cran, badges anglais avec durÃ©e et
halo limitÃ© aux gants/manches R1. Le lanceur installe le renderer vÃ©rifiÃ©
compatible avant le client. Voir `docs/RELEASE-0.20.5.md`.

## Historique de lâ€™atelier des animations

Atelier animÃ© avec les armes complÃ¨tes : trois alimentations, ralenti,
image par image, cadrage des deux mains, comparaison avant/aprÃ¨s et rÃ©glage
local de lâ€™index. Correction de la prise de lâ€™index gauche sur les trois
rechargements, avec stabilisation pendant la prise infÃ©rieure. VÃ©rification
sur les animations compilÃ©es et lâ€™enveloppe de prise commune aux chargeurs.
Les modÃ¨les et textures des 61 piÃ¨ces dâ€™arme restent identiques.

Trois tenues R-01 Ã  la troisiÃ¨me personne avec les douze piÃ¨ces rÃ©elles,
points de prise et bras rÃ©solus sans Ã©tirer les os. Maintien et tir personnalisÃ©s,
recharges MP5/fusil adaptÃ©es depuis CS avec chargeur mobile, debout et accroupi.
Les 77 indices existants, les contrÃ´leurs et les jambes sont conservÃ©s ; seules
les rotations des bras/doigts sont retravaillÃ©es. Lâ€™atelier permet dâ€™essayer les
jambes en marche/course, rÃ©gler la tenue, exporter et recompiler une recette JSON.

Extension native v3 : 24 piÃ¨ces par assemblage, Ã©chelle uniforme des sockets,
remplacement explicite de lâ€™arme portÃ©e historique. Lâ€™affichage distant utilise
les piÃ¨ces et finitions Ã©quipÃ©es par chaque joueur. Validation dans une copie
du runtime. Le moteur installÃ© est aussi passÃ© Ã  cette interface v3. Recharge rÃ©seau MP5
raccordÃ©e sur le porteur serveur, avec conservation du geste pendant la marche,
progression conservÃ©e debout/accroupi, retour au maintien en fin de recharge et
annulation au rangement. Abaissement/bascule de lâ€™arme et prise du chargeur
corrigÃ©e sur les trois alimentations. Le remplacement Gordon de `CheckPowerups`
ne dÃ©truit plus le modÃ¨le Ã©quipÃ© et sa table de sÃ©quences. Rotation du torse
R-01 autour de la verticale pour Ã©viter le roulis lors des dÃ©placements accroupis.

Animations de dÃ©placement de base conservÃ©es. Prise dÃ©diÃ©e en premiÃ¨re
personne pour la poignÃ©e inclinÃ©e : maintien, tir, sortie et retour aprÃ¨s
recharge, pour les trois alimentations et toutes les finitions. Doigts ajustÃ©s
sur la gÃ©omÃ©trie de la poignÃ©e. Geste FP ramenÃ© aux 1,5 s de recharge dÃ©jÃ 
prÃ©vues par le gameplay ; trajectoires du chargeur et de la main droite
conservÃ©es. Torsion de lâ€™avant-bras de la recharge supÃ©rieure stabilisÃ©e.
SÃ©lecteur dâ€™appui avant dans lâ€™atelier ; aucune variante dÃ©diÃ©e ajoutÃ©e Ã  la
troisiÃ¨me personne. VÃ©rification hors jeu puis test natif ciblÃ©.
Les Ã©quipements sans apparence dÃ©finie cessent de sÃ©lectionner automatiquement
HEV quand GIGN est disponible. Le corps serveur GIGN sert aussi de secours
pendant lâ€™attente de lâ€™Ã©tat rÃ©seau.

## 0.20.4 â€” 2026-10-09

Flashes R1 plus visibles : Ã©toile frontale deux fois plus grande et plus
lumineuse, lÃ©gÃ¨rement avancÃ©e devant la bouche ; jet extÃ©rieur allongÃ© et
Ã©largi. VÃ©rification des huit profils en solo et de la vue de cÃ´tÃ© Ã  deux clients.
Voir [les notes](docs/RELEASE-0.20.4.md).

## 0.20.3 â€” 2026-10-09

Huit Ã©toiles frontales dÃ©diÃ©es pour le tireur, avec Ã©mission centrÃ©e sur
la bouche. Jet de profil rÃ©servÃ© aux vues extÃ©rieures ; suppression des
flashes Studio historiques qui se superposaient sur le R1.
Voir [les notes](docs/RELEASE-0.20.3.md).

## 0.20.2 â€” 2026-10-09

Huit prÃ©sentations de tir R1, flash axial avec cÃ…â€œur frontal, marques de balle
rÃ©duites, traces, particules et 40 sons rÃ©tro avec contacts matÃ©riels.
Stand de test dans F3, contrÃ´le des couches, validation serveur et
synchronisation des profils Ã  lâ€™arrivÃ©e dâ€™un joueur.
Voir [les notes](docs/RELEASE-0.20.2.md) et [les essais](WEAPON_FX.md).

## 0.20.1 â€” 2026-10-09

Retrait complet des cÃ´tÃ©s du boÃ®tier de poignet et du bracelet flottant.
Index gauche alignÃ© sur la courbure des autres doigts. Rechargement supÃ©rieur
avec bascule de lâ€™arme vers la gauche pour garder lâ€™avant-bras dans le cadre,
contact de la main droite et longueurs des os conservÃ©s.
Voir [les notes](docs/RELEASE-0.20.1.md).

## 0.20.0 â€” 2026-10-09

Gants et manches en premiÃ¨re personne liÃ©s sÃ©parÃ©ment aux objets portÃ©s.
Quatorze apparences pour chaque partie, rÃ©utilisant les atlas des tenues.
DÃ©pliage anatomique, dÃ©tails prÃ©levÃ©s Ã  la rÃ©solution native, plaque carrÃ©e
supprimÃ©e et doigts arrondis par subdivision ciblÃ©e sans nouvel os. Atelier 3D
autonome pour contrÃ´ler les UV et les poses des modÃ¨les compilÃ©s.
Prise latÃ©rale par-dessus le chargeur, inclinÃ©e vers lâ€™avant, coude bas et
poignet moins flÃ©chi. Les textures et modÃ¨les des piÃ¨ces dâ€™arme restent communs.
Voir [les notes](docs/RELEASE-0.20.0.md).

## 0.19.0 â€” 2026-10-09

Inventaire de jeu simplifiÃ©, sÃ©lection manuelle de chaque objet et filtres sans
Ã©quipement automatique. 948 objets distincts, dont 854 piÃ¨ces dâ€™arme avec une
finition immuable, 70 piÃ¨ces de tenue et 24 accessoires. Arche supÃ©rieure ajoute
un second chÃ¢ssis alimentÃ© par le haut. Tenues Inventeur et Dieselpunk sur GIGN.
Protocole 4 avec indices sur 16 bits et migration des anciennes sauvegardes.
Voir [les notes](docs/RELEASE-0.19.0.md).

## 0.18.0 â€” 2026-10-09

Huit modÃ¨les propres aux thÃ¨mes Inventeur et Dieselpunk : deux culasses,
deux optiques, deux rÃ©serves et deux refroidisseurs. Deux boutons dâ€™ensemble
chargent les formes et leur finition dans lâ€™atelier ; chaque piÃ¨ce reste
sÃ©lectionnable et recolorable sÃ©parÃ©ment. Les formes rÃ©utilisent les atlas et
les trois rigs existants. Catalogue de 60 piÃ¨ces R1, 248 objets et 924 entrÃ©es
de lootpool. Voir [les notes](docs/RELEASE-0.18.0.md).

## 0.17.0 â€” 2026-10-09

Deux banques de matiÃ¨res rÃ©interprÃ¨tent les seize fonctions du R-01 :
Rome / Atelier dâ€™inventeur et Dieselpunk. Quatorze finitions sur 52 piÃ¨ces,
728 variantes dâ€™armes et 812 entrÃ©es de lootpool ; les nouvelles collections
sont rÃ©servÃ©es aux armes. Gyre emploie maintenant une matiÃ¨re rÃ©pÃ©table sur
son noyau et une plaque distincte pour le dÃ©cor dâ€™identitÃ©. Les douze anciens
styles conservent leurs identifiants. Voir [les notes](docs/RELEASE-0.17.0.md).

## 0.16.0 â€” 2026-10-08

Arche et Gyre ajoutent deux chÃ¢ssis aux silhouettes sculptÃ©es : arches ajourÃ©es
et noyau cylindrique sous cage hÃ©licoÃ¯dale. Raccords et animation par-dessous
conservÃ©s ; douze finitions rÃ©utilisÃ©es. Deux raccourcis dans lâ€™emplacement
ChÃ¢ssis prÃ©servent les autres modules. Catalogue de 52 piÃ¨ces R1, 240 objets
et 708 entrÃ©es de lootpool. Voir [les notes](docs/RELEASE-0.16.0.md).

## 0.15.0 â€” 2026-10-08

Nomade et Bastion ajoutent deux types de piÃ¨ce Ã  chacun des douze emplacements
R-01 : 24 gÃ©omÃ©tries supplÃ©mentaires, 50 piÃ¨ces et 684 entrÃ©es de lootpool.
RÃ©emploi intÃ©gral des douze finitions existantes. Nouveaux prÃ©rÃ©glages dans
lâ€™atelier ; chargeurs compatibles avec les trois montages et les sauvegardes
par identifiants. Lâ€™audit des assemblages couvre chaque piÃ¨ce et chaque paire
dâ€™emplacements sans parcourir les 25 millions de configurations complÃ¨tes.
Voir [les piÃ¨ces et vÃ©rifications](docs/RELEASE-0.15.0.md).

## 0.14.0 â€” 2026-10-08

SÃ©paration gameplay/dÃ©veloppement. Les objets de tenue utilisent le modÃ¨le GIGN
ajustÃ© ; les armes utilisent R1. Les neuf emplacements opÃ©rateur sont conservÃ©s,
avec les placeholders d'Ã©paules, ceinture, bouclier et spÃ©cial. Lootpool de
396 entrÃ©es, six familles de gameplay et collections cosmÃ©tiques distinctes.
Les bibliothÃ¨ques historiques passent dans les options dÃ©veloppeur ; le retour
au gameplay restaure la configuration Ã©quipÃ©e.
Voir [les fonctionnalitÃ©s et contrÃ´les](docs/RELEASE-0.14.0.md).

## 0.13.0 â€” 2026-10-08

Build consolidÃ©, lanceur unique, personnages GIGN ajustÃ©s, cinq ensembles
personnage/arme supplÃ©mentaires, douze finitions R1, trois plateformes et
prÃ©servation du skin libre pendant les changements d'arme.
Voir [les fonctionnalitÃ©s et contrÃ´les](docs/RELEASE-0.13.0.md).

## 0.12 â€” 2026-10-08

Trois plateformes R1 : chargeur dessous, latÃ©ral ou supÃ©rieur. Chargeurs
communs, trajectoires de rechargement adaptÃ©es, 26 modules, 8 192 assemblages.

## 0.11 â€” 2026-10-08

Relais R1 original, piÃ¨ces texturÃ©es et finitions interchangeables ; correction
du mapping Ã©tirÃ© des surfaces longues.

Les Ã©tapes prÃ©cÃ©dentes du prototype sont documentÃ©es dans [README.md](README.md).
