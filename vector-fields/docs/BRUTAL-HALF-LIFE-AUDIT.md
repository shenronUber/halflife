# Brutal Half-Life : faisabilité d'intégration

Vérification du 9 octobre 2026. Analyse documentaire, lecture de code ancien
et analyse statique de l'archive V3 fournie par l'utilisateur.
Aucun changement de gameplay, remplacement de DLL ou lancement du mod.

Le franchissement V3 a été localisé dans la DLL et les modèles. Voir
[le relevé consacré au franchissement](BRUTAL-HALF-LIFE-VAULTING.md).

## Conclusion

Les comportements de mouvement et d'interaction de Brutal Half-Life peuvent
servir de référence pour Vector Fields. Notre base SDK Half-Life / Xash3D FWGS
offre des points d'extension adaptés. La possibilité de copier directement
une implémentation V3 sous forme de source n'est cependant pas établie :
l'archive fournie ne contient aucun code C/C++ ni PDB. L'analyse du code
compilé a localisé la détection et l'impulsion de franchissement.

## Version et récupération

La liste officielle affiche V3, publiée par zoonyarts le 26 décembre 2024,
comme dernière version officielle disponible. Des correctifs de tiers plus
récents figurent aussi dans cette liste.

- [Fichiers officiels et correctifs](https://www.moddb.com/mods/brutal-half-life/downloads)
- [Archive V3 officielle](https://www.moddb.com/downloads/brutal-half-life-v3)
- [Présentation de l'auteur](https://www.moddb.com/mods/brutal-half-life)

L'auteur cible Half-Life Steam, mise à jour du 25e anniversaire, sur GoldSrc.
Il annonce notamment franchissement d'obstacles, manipulation d'objets et
récupération du contenu des sacs des soldats.

Archive annoncée : bhl_v3.zip, 331 654 642 octets (316,29 Mio).
MD5 publié : 9b8fe2dc10f933ca2619d5fcc4cb74b7.

État local : archive V3 fournie par l'utilisateur dans Téléchargements et
vérifiée. Sa taille et son MD5 concordent avec la fiche officielle.
SHA-256 : 29759d1c91fbe00b42e56df2f277663ef89eab8a715542a4722884558bb80cac.
L'inventaire compte 1 400 fichiers, dont trois DLL et aucun source C/C++ ou PDB.
Les fichiers utiles sont extraits sous runtime/brutal-half-life-research/v3.
L'analyse statique a identifié le franchissement ; un essai en jeu reste à faire.

## Code ancien récupéré

Le dépôt [LostGamerHL/BHL](https://github.com/LostGamerHL/BHL) se présente comme
du code Brutal Half-Life, mais ne constitue pas une source V3 vérifiée.

- Révision : 3fd025d064e15317e3315c2982013b7c35613206.
- Dernier commit : 22 février 2017, bien avant la V3.
- README : SDK Half-Life pour Xash3D et GoldSource.
- Aucune licence de projet reconnue par les métadonnées GitHub ; des en-têtes
  de droits Valve sont présents. Les droits sur les ajouts restent à établir.
- Archive locale : runtime/brutal-half-life-research/BHL-source-2017.zip.
- Taille : 1 133 581 octets.
- SHA-256 : eeeae5ec1176f58d554525b32b7cc5cb8cde607070e388feb63ee5d7d98c6a73.
- Extraction : runtime/brutal-half-life-research/source-2017/BHL-3fd025d064e15317e3315c2982013b7c35613206/.

Les chemins de l'archive ont été contrôlés avant extraction. Le dossier reste
local dans le runtime ignoré par Git. Aucun code téléchargé n'a été exécuté.

Observations dans ce dépôt, sans prétendre décrire la V3 :

- dlls/prop.cpp, CProp::Use : suivi d'une cible devant le joueur par correction
  de vitesse ; le bouton de tir déclenche une vitesse de lancer.
  CProp::PropRespawn emploie MOVETYPE_BOUNCE et SOLID_SLIDEBOX.
  C'est un exemple d'interaction utilisant les mécanismes existants du SDK.
- dlls/m249.cpp, CM249::PrimaryAttack : recul de caméra et impulsion vers
  l'arrière au sol.
- Aucun mécanisme de franchissement V3 n'a été identifié dans la lecture ciblée
  de player.cpp et pm_shared ; cela ne prouve pas son absence ailleurs.

Ce code n'a pas été compilé et sa fidélité au mod officiel n'a pas été établie.

## Correspondance avec notre projet

Vector Fields emploie une dérivation locale de Xash3D FWGS, base
9137964147d8f749dbeddf1cb5482c3d16f86e4a, et le SDK Half-Life. Voir
vector-fields/engine/README.md et le manifeste construit
runtime/vector-engine/vector-engine-build.json.

GoldSrc et notre moteur ne sont pas identiques. Ils partagent néanmoins les
interfaces de mod Half-Life pertinentes. Cette proximité rend l'adaptation
plausible ; elle ne garantit pas que toute DLL V3 fonctionnera sans problème.

| Comportement visé | Zone d'intégration proposée | Travail à valider |
| --- | --- | --- |
| Franchissement d'obstacles | pm_shared/pm_shared.c, commandes, présentation client | Traces, place libre pour le volume joueur, trajectoire, annulation, prédiction |
| Attraper / porter / lancer | Entité serveur, CBasePlayer::PlayerUse, effets client | Collisions, libération, portée, propriétaire, sauvegarde, états d'arme |
| Coup de pied / poussée | Commande d'action, traces et dégâts serveur, animation client | Portée, cadence, impulsion, interaction avec les boutons, synchronisation |
| Loot des sacs | Entités serveur et inventaire Vector Fields | Attribution unique, validation du contenu, sauvegarde, synchronisation |

Ces zones proposées sont une analyse d'architecture, pas le résultat de la
décompilation de la V3. Le coup de pied est une piste d'étude ; son code V3 n'a
pas été examiné.

Notre pm_shared/pm_shared.c est compilé dans les deux DLL, client et serveur.
Le commentaire de PM_Move décrit la logique commune de prédiction. Un nouveau
mouvement doit conserver cette cohérence pour éviter les corrections de
position en multijoueur.

Une grande partie de ces mécanismes devrait pouvoir vivre dans le code du mod.
Une modification du moteur n'est à envisager qu'en présence d'une limitation
constatée des collisions, du réseau ou du rendu.

## Méthode pour la suite

1. Réalisé : archive V3 vérifiée, SHA-256 calculé et chemins inventoriés.
2. Examiner liblist.gam, DLL, configurations, documentation, FGD, événements et
   modèles effectivement présents. Une animation ou un FGD ne contient pas à
   lui seul la logique C++ d'une mécanique.
3. Observer chaque comportement sur une installation séparée : déclenchement,
   portée, vitesses, collisions, interruption et interactions avec les armes.
4. Chercher une publication des sources par l'auteur et leurs conditions de
   réutilisation. À défaut, concevoir notre propre implémentation à partir des
   comportements observés et de notre SDK.
5. Prototyper une mécanique à la fois, avec les touches et les règles propres
   à Vector Fields. Pour le franchissement, vérifier obstacles bas, plafonds,
   bords, pentes, objets mobiles et cohérence client / serveur.

Remplacer notre DLL par celle du mod lancerait sa logique de jeu ; cela ne
transférerait pas sélectivement ses fonctionnalités dans notre travail. Une
DLL compilée ne restitue pas automatiquement le code source original.
La copie de code ou de ressources doit s'appuyer sur des conditions de
réutilisation identifiées ; un téléchargement public ne les établit pas.

