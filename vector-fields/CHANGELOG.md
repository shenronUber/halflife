# 0.20.7 — Corrections d’intégration — 2026-10-10

- La validation centrale inclut la salle de test, la matrice des cris contextuels et les finitions des fragments. Les essais utilisent les DLL courantes et vérifient leurs empreintes.
- Les fragments gardent les textures du gant et de la manche, ou de la botte et du pantalon, indépendamment. Vingt maillages et les banques de textures existantes servent aux 196 couples ; les indices uniformes historiques sont conservés.
- La salle GIGN est générée depuis le code de la carte de base, avec un cache vérifiant sources, outils et sorties. Build, lancement et essais isolés partagent ce résultat. Les deux cartes générées sont contrôlées dans le déploiement. Le lanceur bots déploie le même inventaire de DLL, modèles et cartes. Il applique la mise à jour validée du moteur et refuse une interface incompatible avant de remplacer les assets.
- Tests de régression : cache et idempotence de la carte, BSP absent ou périmé, correspondance des deux finitions, décès réel en tenue mélangée et conservation réseau pour un arrivant tardif.

# Historique Vector Fields

## Sons elementaires et sang disperse — 2026-10-10

Seize sons de mort et dix-sept sons d arrachement generes, dont le neutre.
Cri, cause et arrachement se superposent sur trois canaux natifs distincts,
avec volumes independants et diffusion positionnelle aux joueurs presents.
La synchronisation tardive ne rejoue aucun son ancien. Le sang des coupes
utilise maintenant des gouttes rouges sombres dispersees avec de la gravite,
sans l ancienne gerbe verticale ni sa variation de palette.
Ecoute : `Atelier - Sons de mort.cmd`. Details : `docs/DEATH-SOUNDS.md`.

## Atlas des morts et fragments élémentaires — 2026-10-10

Sept morts Mixamo ajoutées, portant les imports à dix. Inventaire des 886 fichiers
d'une banque publique et inspection de 24 candidats. Seize profils associent
les éléments et réactions à leurs mouvements ; atlas et catalogue paginé dans F8.
Chaque perte crée une pièce anatomique entière et trois petits fragments physiques,
avec traînées de sang et particules de l'effet. Appuis adaptés au maillage découpé,
fragments posés au sol et durée limitée, synchronisation des nouveaux observateurs.
Détails et essais dans `docs/DEATH-ATLAS.md`.

## Bibliothèques de morts importées — 2026-10-10

Trois morts Quaternius/KayKit transférées et compilées sur les 28 os GIGN,
appuis et pose finale corrigés pour nos proportions. Sélecteur F8, variations
automatiques des morts ordinaires, démembrement et effets indépendants.
Les signatures suivent le torse animé ; les séquences historiques sont conservées.
Exports donneurs et provenance archivés, essais natifs des membres, du menu
et de la sauvegarde. Détails dans `docs/DEATH-VISUALS.md`.

## Textures de démembrement — 2026-10-09

Cinq matériaux de plaie, trois sources originales sobres, mesures précises et UV
continus à 16 pixels/unité. Coupes planes des bras et cuisses, bassin conservé,
étui séparé, raccords sur les mêmes os et éclairage des faces basses corrigé.
Gros plans natifs et test tête/électricité ; détails dans `docs/WOUND-TEXTURES.md`.

## Prototype de morts — 2026-10-09

Cadavres GIGN animés pour le joueur et les cibles, tête, bras gauche/droit et
jambes gauche/droite détachables avec fragments et blessures. Contractions
électriques puis chute, effet et tenue conservés sur le cadavre. Laboratoire
F8 ; règles de dégâts localisés reportées. Ressources compilées et déployées
par le lanceur, validation des modèles, essais natifs et réseau dédiés.

## 0.20.6 — 2026-10-09

HUD : remplacement des motifs provisoires des huit éléments et huit réactions
par seize textures originales, soit 64 images peintes. Animation par fondu,
ancrage et opacité RGBA communs, zone de visée protégée, intégration
au build incrémental et vérification des ressources livrées.

Maintenance à partir de la 0.20.5 : traits de modèles et porteurs partagés entre
Python, client et serveur ; génération incrémentale des pièces et animations,
dépendances transitives et empreintes des sorties vérifiées. Un seul format de
catalogue de finitions évite les reconstructions provoquées par deux auteurs.

Suites de validation regroupées, tests unitaires de régression ajoutés, prises
avant et tiers-personne incluses dans le build. Les tests natifs utilisent les
DLL actuelles. Vérification de livraison étendue aux porteurs tiers-personne,
DLL, catalogues et effets. Contrats moteur/réseau documentés depuis leurs
constantes C++. Aucune modification du protocole, des sauvegardes ou des modèles.

## 0.20.5 — 2026-10-09

Signatures des états sur les bords de l’écran, badges anglais avec durée et
halo limité aux gants/manches R1. Le lanceur installe le renderer vérifié
compatible avant le client. Voir `docs/RELEASE-0.20.5.md`.

## Historique de l’atelier des animations

Atelier animé avec les armes complètes : trois alimentations, ralenti,
image par image, cadrage des deux mains, comparaison avant/après et réglage
local de l’index. Correction de la prise de l’index gauche sur les trois
rechargements, avec stabilisation pendant la prise inférieure. Vérification
sur les animations compilées et l’enveloppe de prise commune aux chargeurs.
Les modèles et textures des 61 pièces d’arme restent identiques.

Trois tenues R-01 à la troisième personne avec les douze pièces réelles,
points de prise et bras résolus sans étirer les os. Maintien et tir personnalisés,
recharges MP5/fusil adaptées depuis CS avec chargeur mobile, debout et accroupi.
Les 77 indices existants, les contrôleurs et les jambes sont conservés ; seules
les rotations des bras/doigts sont retravaillées. L’atelier permet d’essayer les
jambes en marche/course, régler la tenue, exporter et recompiler une recette JSON.

Extension native v3 : 24 pièces par assemblage, échelle uniforme des sockets,
remplacement explicite de l’arme portée historique. L’affichage distant utilise
les pièces et finitions équipées par chaque joueur. Validation dans une copie
du runtime. Le moteur installé est aussi passé à cette interface v3. Recharge réseau MP5
raccordée sur le porteur serveur, avec conservation du geste pendant la marche,
progression conservée debout/accroupi, retour au maintien en fin de recharge et
annulation au rangement. Abaissement/bascule de l’arme et prise du chargeur
corrigée sur les trois alimentations. Le remplacement Gordon de `CheckPowerups`
ne détruit plus le modèle équipé et sa table de séquences. Rotation du torse
R-01 autour de la verticale pour éviter le roulis lors des déplacements accroupis.

Animations de déplacement de base conservées. Prise dédiée en première
personne pour la poignée inclinée : maintien, tir, sortie et retour après
recharge, pour les trois alimentations et toutes les finitions. Doigts ajustés
sur la géométrie de la poignée. Geste FP ramené aux 1,5 s de recharge déjà
prévues par le gameplay ; trajectoires du chargeur et de la main droite
conservées. Torsion de l’avant-bras de la recharge supérieure stabilisée.
Sélecteur d’appui avant dans l’atelier ; aucune variante dédiée ajoutée à la
troisième personne. Vérification hors jeu puis test natif ciblé.
Les équipements sans apparence définie cessent de sélectionner automatiquement
HEV quand GIGN est disponible. Le corps serveur GIGN sert aussi de secours
pendant l’attente de l’état réseau.

## 0.20.4 — 2026-10-09

Flashes R1 plus visibles : étoile frontale deux fois plus grande et plus
lumineuse, légèrement avancée devant la bouche ; jet extérieur allongé et
élargi. Vérification des huit profils en solo et de la vue de côté à deux clients.
Voir [les notes](docs/RELEASE-0.20.4.md).

## 0.20.3 — 2026-10-09

Huit étoiles frontales dédiées pour le tireur, avec émission centrée sur
la bouche. Jet de profil réservé aux vues extérieures ; suppression des
flashes Studio historiques qui se superposaient sur le R1.
Voir [les notes](docs/RELEASE-0.20.3.md).

## 0.20.2 — 2026-10-09

Huit présentations de tir R1, flash axial avec cÅ“ur frontal, marques de balle
réduites, traces, particules et 40 sons rétro avec contacts matériels.
Stand de test dans F3, contrôle des couches, validation serveur et
synchronisation des profils à l’arrivée d’un joueur.
Voir [les notes](docs/RELEASE-0.20.2.md) et [les essais](WEAPON_FX.md).

## 0.20.1 — 2026-10-09

Retrait complet des côtés du boîtier de poignet et du bracelet flottant.
Index gauche aligné sur la courbure des autres doigts. Rechargement supérieur
avec bascule de l’arme vers la gauche pour garder l’avant-bras dans le cadre,
contact de la main droite et longueurs des os conservés.
Voir [les notes](docs/RELEASE-0.20.1.md).

## 0.20.0 — 2026-10-09

Gants et manches en première personne liés séparément aux objets portés.
Quatorze apparences pour chaque partie, réutilisant les atlas des tenues.
Dépliage anatomique, détails prélevés à la résolution native, plaque carrée
supprimée et doigts arrondis par subdivision ciblée sans nouvel os. Atelier 3D
autonome pour contrôler les UV et les poses des modèles compilés.
Prise latérale par-dessus le chargeur, inclinée vers l’avant, coude bas et
poignet moins fléchi. Les textures et modèles des pièces d’arme restent communs.
Voir [les notes](docs/RELEASE-0.20.0.md).

## 0.19.0 — 2026-10-09

Inventaire de jeu simplifié, sélection manuelle de chaque objet et filtres sans
équipement automatique. 948 objets distincts, dont 854 pièces d’arme avec une
finition immuable, 70 pièces de tenue et 24 accessoires. Arche supérieure ajoute
un second châssis alimenté par le haut. Tenues Inventeur et Dieselpunk sur GIGN.
Protocole 4 avec indices sur 16 bits et migration des anciennes sauvegardes.
Voir [les notes](docs/RELEASE-0.19.0.md).

## 0.18.0 — 2026-10-09

Huit modèles propres aux thèmes Inventeur et Dieselpunk : deux culasses,
deux optiques, deux réserves et deux refroidisseurs. Deux boutons d’ensemble
chargent les formes et leur finition dans l’atelier ; chaque pièce reste
sélectionnable et recolorable séparément. Les formes réutilisent les atlas et
les trois rigs existants. Catalogue de 60 pièces R1, 248 objets et 924 entrées
de lootpool. Voir [les notes](docs/RELEASE-0.18.0.md).

## 0.17.0 — 2026-10-09

Deux banques de matières réinterprètent les seize fonctions du R-01 :
Rome / Atelier d’inventeur et Dieselpunk. Quatorze finitions sur 52 pièces,
728 variantes d’armes et 812 entrées de lootpool ; les nouvelles collections
sont réservées aux armes. Gyre emploie maintenant une matière répétable sur
son noyau et une plaque distincte pour le décor d’identité. Les douze anciens
styles conservent leurs identifiants. Voir [les notes](docs/RELEASE-0.17.0.md).

## 0.16.0 — 2026-10-08

Arche et Gyre ajoutent deux châssis aux silhouettes sculptées : arches ajourées
et noyau cylindrique sous cage hélicoïdale. Raccords et animation par-dessous
conservés ; douze finitions réutilisées. Deux raccourcis dans l’emplacement
Châssis préservent les autres modules. Catalogue de 52 pièces R1, 240 objets
et 708 entrées de lootpool. Voir [les notes](docs/RELEASE-0.16.0.md).

## 0.15.0 — 2026-10-08

Nomade et Bastion ajoutent deux types de pièce à chacun des douze emplacements
R-01 : 24 géométries supplémentaires, 50 pièces et 684 entrées de lootpool.
Réemploi intégral des douze finitions existantes. Nouveaux préréglages dans
l’atelier ; chargeurs compatibles avec les trois montages et les sauvegardes
par identifiants. L’audit des assemblages couvre chaque pièce et chaque paire
d’emplacements sans parcourir les 25 millions de configurations complètes.
Voir [les pièces et vérifications](docs/RELEASE-0.15.0.md).

## 0.14.0 — 2026-10-08

Séparation gameplay/développement. Les objets de tenue utilisent le modèle GIGN
ajusté ; les armes utilisent R1. Les neuf emplacements opérateur sont conservés,
avec les placeholders d'épaules, ceinture, bouclier et spécial. Lootpool de
396 entrées, six familles de gameplay et collections cosmétiques distinctes.
Les bibliothèques historiques passent dans les options développeur ; le retour
au gameplay restaure la configuration équipée.
Voir [les fonctionnalités et contrôles](docs/RELEASE-0.14.0.md).

## 0.13.0 — 2026-10-08

Build consolidé, lanceur unique, personnages GIGN ajustés, cinq ensembles
personnage/arme supplémentaires, douze finitions R1, trois plateformes et
préservation du skin libre pendant les changements d'arme.
Voir [les fonctionnalités et contrôles](docs/RELEASE-0.13.0.md).

## 0.12 — 2026-10-08

Trois plateformes R1 : chargeur dessous, latéral ou supérieur. Chargeurs
communs, trajectoires de rechargement adaptées, 26 modules, 8 192 assemblages.

## 0.11 — 2026-10-08

Relais R1 original, pièces texturées et finitions interchangeables ; correction
du mapping étiré des surfaces longues.

Les étapes précédentes du prototype sont documentées dans [README.md](README.md).
