# jk_botti : test dans Vector Fields

Vérification du 9 octobre 2026, avec Vector Fields 0.19.0 et notre moteur natif.

## Résultat

Le prototype fonctionne avec **notre DLL de jeu, notre client et nos personnages**.
Deux bots utilisent le MP5 qui porte actuellement les visuels de notre fusil :
déplacement, tir, consommation du chargeur, recharge, dégâts, mort et réapparition.
Le test initial de 30 secondes dans `vf_range` a mesuré 151 événements de tir MP5,
5 frags et 5 morts. Le bot qui n'est jamais mort a vidé et rempli deux fois son
chargeur : cette mesure valide des recharges et ne dépend pas d'une réapparition.

Cette compatibilité correspond à l'état actuel : le fusil conserve l'identifiant,
les munitions, le tir et la recharge du MP5. Des mécanismes d'armes ou de déplacement
nouveaux demanderont une adaptation des décisions et de la navigation du bot.

Le laboratoire est séparé sous `runtime/jk-botti-research/engine`. Le jeu courant
reste sous `runtime/vector-engine/vf_visual`. Le prototype est un serveur de
**deathmatch Half-Life**, même lorsqu'il charge une géométrie venant de CS ou TFC.

## Voix et provocations

Le lanceur synchronise maintenant les DLL de jeu et les 233 sons des six personnages depuis la compilation courante. Les bots choisissent une voix aleatoire a chaque apparition. Ils peuvent provoquer un adversaire proche et visible, puis repondre aux provocations entendues d'un humain ou d'un autre bot. Ces decisions vocales utilisent les hooks du joueur dans notre DLL, avec les memes priorites et delais que les joueurs humains.

Les reglages sont conserves dans `runtime/jk-botti-research/engine/valve/vf_voice_behavior.cfg`. `vf_bot_taunts 0` coupe leurs provocations ; `vf_bot_taunt_chance` et `vf_bot_counter_chance` reglent independamment l'initiative et les reponses, de 0 a 1. Dans la console du client, utiliser par exemple `rcon vf_bot_counter_chance 1`, ou `rcon exec vf_voice_behavior.cfg` apres avoir modifie le fichier. J choisit automatiquement une reponse quand une provocation recente est encore audible a portee.

Voir [la documentation des voix](OPERATOR-VOICES.md) pour les six personnages, la portee, le delai, le cooldown et les commandes. Le test `python vector-fields/tests/bot_voice_test.py` utilise deux vrais bots jk_botti et un vrai client humain dans un runtime isole ; il ne force pas leurs evenements de dialogue.

## Refaire le test

Double-cliquer sur `Jouer - Bots jk_botti.cmd`, à la racine. Deux bots rejoignent
le laboratoire. F4 revient au laboratoire ; F5 rejoint Crossfire. Fermer le client
arrête le serveur créé par ce lancement. Le serveur utilise IPv4 127.0.0.1:27035 ;
IPv6 est désactivé. Les journaux, captures et chemins appris restent dans le runtime
de recherche. Il utilise les ressources Half-Life installées sous
`F:/SteamLibrary/steamapps/common/Half-Life`, comme les autres tests du projet.

Autres cartes :

```powershell
python vector-fields/bots/jk_botti_lab.py play --map crossfire
python vector-fields/bots/jk_botti_lab.py play --map vf_bot_dust2
python vector-fields/bots/jk_botti_lab.py play --map vf_bot_2fort
```

Tests et préparation reproductibles :

```powershell
python vector-fields/bots/prepare_jk_botti.py
python vector-fields/bots/jk_botti_lab.py audit
python vector-fields/bots/jk_botti_lab.py smoke --map vf_range --seconds 30
python vector-fields/bots/jk_botti_lab.py smoke --map crossfire --seconds 18
python vector-fields/bots/jk_botti_lab.py smoke --map vf_bot_dust2 --seconds 18 --duel
python vector-fields/bots/jk_botti_lab.py smoke --map vf_bot_2fort --seconds 18 --duel
```

La préparation exige les outils C++ Visual Studio utilisés par le projet. Elle
réemploie les téléchargements déjà présents et vérifie leur SHA-256. Le fichier
Metamod provient d'une publication continue : si cette publication change, un
nouveau téléchargement sera refusé tant que son empreinte n'aura pas été examinée.
`--skip-download` réemploie les archives déjà extraites. Les fichiers `.wpt` appris
sont conservés lors d'une nouvelle préparation.

## Ce qui a réellement été testé

| Carte | Préparation | Observation | Limite |
| --- | --- | --- | --- |
| `vf_range`, initial | Notre carte et notre équipement actuels | Tir MP5, recharge, dégâts, 5 frags et réapparitions | 2 points initiaux insuffisants : un bot est resté immobile en combattant |
| `vf_range`, après apprentissage | Un vrai client a parcouru la salle ; sauvegarde et rechargement | Le premier parcours produit 17 points et 44 liens ; les deux bots se déplacent et combattent après rechargement | Parcours du laboratoire seulement |
| `crossfire` | Chemins officiels livrés avec jk_botti | Les deux bots se déplacent, récupèrent des armes et tirent, dont avec le MP5 | Test court ; aucun parcours exhaustif de la carte |
| `vf_cs_de_dust2` | Copie d'exploration déjà présente | Apparition et déplacements sans crash | Aucun tir observé dans cet essai de 18 secondes ; aucun chemin préparé |
| `vf_tfc_2fort` | Copie d'exploration déjà présente | Apparition et déplacements sans crash | Pas d'apparitions HLDM dédiées ; navigation incomplète et aucun tir observé dans cet essai |
| `vf_bot_dust2` | Copie séparée, MP5 et munitions à l'apparition | Les deux bots utilisent le MP5 ; dégâts, frags et réapparitions | Rencontre initiale imposée aux deux premiers points d'apparition pour tester le combat ; couverture de carte non validée |
| `vf_bot_2fort` | Copie séparée, 32 apparitions TFC converties en HLDM, MP5 et munitions | Les deux bots se déplacent, tirent, infligent des dégâts et rechargent | Rencontre initiale imposée ; aucun drapeau, aucune classe TFC ni couverture complète validés |

Un vrai client a aussi rejoint le serveur : rendu natif des personnages modulaires,
armes portées visibles, fusil en première personne et captures du jeu. Le changement
de carte est vérifié séparément avec conservation de deux bots.

Les duels contrôlés vérifient le combat indépendamment de la couverture de navigation.
Ils ne démontrent pas que les bots savent rejoindre seuls tous les lieux d'une carte.
Les 41 cartes du projet ont été **inventoriées**, pas toutes jouées avec des bots.
Les mesures sont résumées dans `vector-fields/bots/jk-botti-verification.json` ;
les échantillons et journaux détaillés sont sous `runtime/jk-botti-research`.

## Cartes et préparation à prévoir

### Half-Life

Le paquet fournit des parcours pour douze cartes HLDM installées : **boot_camp,
bounce, crossfire, datacore, frenzy, gasworks, lambda_bunker, rapidcore, snark_pit,
stalkyard, subtransit, undertow**. Crossfire a été essayée ici. Les onze autres ont
leurs fichiers de navigation, mais n'ont pas fait l'objet de cet essai en jeu.
Le paquet fournit aussi quinze parcours Opposing Force ; ce mod n'a pas été testé.

Pour une autre carte HLDM : ajouter ou préparer un parcours `.wpt`. Pour une carte
de campagne : prévoir en plus apparitions multiples, équipement et éventuelle
adaptation des portes, scripts ou transitions. jk_botti n'est pas une IA de
progression dans la campagne.

### Counter-Strike 1.6

Les 25 copies locales sont des BSP GoldSrc v30 et possèdent déjà des apparitions
`info_player_deathmatch`. Elles n'ont aucun parcours jk_botti fourni dans ce paquet.
Pour le deathmatch Vector Fields : distribuer l'équipement de notre jeu, préparer
les chemins puis vérifier portes, échelles, sauts, passages étroits et apparitions.
Les apparitions actuelles viennent du camp terroriste ; il est préférable de
redistribuer les positions sur toute la carte et de récupérer aussi celles de
l'autre camp pour éviter de concentrer les joueurs.

Les objectifs bombe/otages et les règles CS ne sont pas ajoutés par ce prototype.
Les fichiers de navigation d'autres bots ont leur propre format : une reprise
éventuelle doit vérifier le format, les liens et les actions, pas seulement renommer
le fichier.

### Team Fortress Classic, TF2 et Day of Defeat

Nos **15 cartes Team Fortress sont celles de TFC**. Quatorze n'ont aucun point HLDM ;
`cz2` utilise l'alias TFC `i_p_t` pour ses seize apparitions et `well` possède deux
points HLDM. Pour du deathmatch : convertir ou ajouter des apparitions, distribuer
l'équipement et préparer les parcours. Les apparitions conditionnelles de cartes
comme Dustbowl, Avanti ou Warpath demandent une sélection adaptée au mode de jeu ;
une conversion globale sans examen pourrait ouvrir des zones normalement fermées.

Les cartes TF2 originales sont des cartes **Source**, avec un format distinct :
elles exigeraient d'abord un port vers les formats et ressources de notre moteur.
Le [format BSP Source défini par Valve](https://github.com/ValveSoftware/source-sdk-2013/blob/master/src/public/bspfile.h)
utilise notamment une signature VBSP et des structures distinctes des BSP GoldSrc.
Un fichier de navigation de bot ne remplace pas ce travail. Si une carte TF2 a déjà
été portée en GoldSrc, elle peut être évaluée comme les autres BSP GoldSrc.

Pour des cartes du **Day of Defeat original sur GoldSrc**, la piste serait similaire :
adapter apparitions, équipement et parcours, puis tester les entités particulières.
Ce n'est pas encore testé. Les objectifs de capture DoD exigeraient des règles et
une logique d'objectifs supplémentaires. Day of Defeat: Source exige aussi un port.

### Créer un parcours

Dans cette configuration, `autowaypoint 1` est activé. Le bot crée quelques points
à partir des armes et objets, puis en ajoute en observant les **vrais joueurs**.
Il faut parcourir les zones, échelles et passages utiles ; les liens sont calculés
au rechargement de la carte. Les bots seuls ne cartographient pas complètement
une carte. Le laboratoire démontre cette distinction : deux points d'objets au
premier lancement, puis dix-sept points après un parcours humain.

Le fichier appris est sauvegardé sous
`valve/addons/jk_botti/waypoints/<carte>.wpt`, avec une matrice `.matrix` calculée.
Une nouvelle carte ou une modification de géométrie demande une vérification du
parcours. Un nom de carte différent exige aussi un nom cohérent dans l'en-tête du
`.wpt` : changer uniquement le nom du fichier peut ne pas suffire.

La navigation fournit des types de points pour accroupissement, saut, échelle,
porte et ascenseur. Notre futur franchissement devra avoir ses actions et liens
adaptés. Il faut également vérifier les ressources accessibles aux bots, les
positions dangereuses et les situations où ils restent bloqués.

## Intégration et provenance

- [jk_botti 1.62 officiel](https://github.com/Bots-United/jk_botti/releases/tag/v1.62),
  source `b7e94c9c2f578672ebad9237b67fd849761f3702` ; binaire Windows x86, variante
  AVX2/FMA choisie par son chargeur sur cette machine. Code non modifié.
- [Metamod FWGS](https://github.com/FWGS/metamod-fwgs), version observée
  `1.0.0.222+m`, source `c0ad71a24f88d73d10dfeb4c3d4beb8c04c81689`.
- Archives, sources, crédits et empreintes : `runtime/jk-botti-research/downloads`,
  `source` et `download-manifest.json`. Les conditions de réutilisation sont celles
  des composants concernés ; leurs notices originales sont conservées.
- `jk_botti_probe.cpp` est un observateur de test séparé. Il mesure les positions,
  événements de tir, chargeurs, santé, morts et frags ; il fournit le placement
  contrôlé utilisé pour les duels. Il ne change pas les décisions de jk_botti.
- Les distances sont exprimées en unités du moteur, avec téléportations de placement
  exclues. Les remontées de chargeur peuvent inclure une réapparition ; la preuve de
  recharge utilise aussi des bots qui ne sont pas morts pendant l'essai.

Le binaire amont construit ses chemins de configuration sous `valve` ou `gearbox`
(`UTIL_BuildFileName_N`, `util.cpp`, ligne 1196). Le runtime de recherche utilise donc
son propre dossier `valve` et notre DLL. Pour une intégration permanente sous
`vf_visual`, il faudra adapter ces chemins dans le code de jk_botti et le recompiler,
ou mettre en place une autre configuration explicite. Ce prototype valide la base
technique ; il n'installe pas les bots dans le lancement courant de Vector Fields.

## Inventaire local des cartes

Inventaire statique ; seuls les essais nommés plus haut ont été joués avec les bots.

| Carte | Apparitions HLDM | Apparitions TFC | Parcours fourni |
| --- | ---: | ---: | --- |
| `vf_cs_as_oilrig` | 21 | 0 | Non |
| `vf_cs_cs_747` | 13 | 0 | Non |
| `vf_cs_cs_assault` | 10 | 0 | Non |
| `vf_cs_cs_backalley` | 10 | 0 | Non |
| `vf_cs_cs_estate` | 10 | 0 | Non |
| `vf_cs_cs_havana` | 16 | 0 | Non |
| `vf_cs_cs_italy` | 10 | 0 | Non |
| `vf_cs_cs_militia` | 10 | 0 | Non |
| `vf_cs_cs_office` | 10 | 0 | Non |
| `vf_cs_cs_siege` | 10 | 0 | Non |
| `vf_cs_de_airstrip` | 16 | 0 | Non |
| `vf_cs_de_aztec` | 18 | 0 | Non |
| `vf_cs_de_cbble` | 16 | 0 | Non |
| `vf_cs_de_chateau` | 17 | 0 | Non |
| `vf_cs_de_dust` | 16 | 0 | Non |
| `vf_cs_de_dust2` | 20 | 0 | Non |
| `vf_cs_de_inferno` | 16 | 0 | Non |
| `vf_cs_de_nuke` | 10 | 0 | Non |
| `vf_cs_de_piranesi` | 16 | 0 | Non |
| `vf_cs_de_prodigy` | 10 | 0 | Non |
| `vf_cs_de_storm` | 16 | 0 | Non |
| `vf_cs_de_survivor` | 10 | 0 | Non |
| `vf_cs_de_torn` | 16 | 0 | Non |
| `vf_cs_de_train` | 12 | 0 | Non |
| `vf_cs_de_vertigo` | 16 | 0 | Non |
| `vf_range` | 8 | 0 | Non |
| `vf_tfc_2fort` | 0 | 32 | Non |
| `vf_tfc_avanti` | 0 | 143 | Non |
| `vf_tfc_badlands` | 0 | 32 | Non |
| `vf_tfc_casbah` | 0 | 32 | Non |
| `vf_tfc_crossover2` | 0 | 32 | Non |
| `vf_tfc_cz2` | 0 | 16 | Non |
| `vf_tfc_dustbowl` | 0 | 96 | Non |
| `vf_tfc_epicenter` | 0 | 28 | Non |
| `vf_tfc_flagrun` | 0 | 32 | Non |
| `vf_tfc_hunted` | 0 | 54 | Non |
| `vf_tfc_push` | 0 | 64 | Non |
| `vf_tfc_ravelin` | 0 | 28 | Non |
| `vf_tfc_rock2` | 0 | 20 | Non |
| `vf_tfc_warpath` | 0 | 144 | Non |
| `vf_tfc_well` | 2 | 24 | Non |
