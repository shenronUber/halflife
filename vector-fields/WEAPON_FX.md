# Effets de tir R1

Le R1 dispose de huit présentations de tir : Hydro, Electro, Cryo, Thermal,
Toxic, Corrosion, Sonic et Kinetic. Les noms correspondent aux huit vecteurs
du laboratoire des effets. Kinetic est le profil normal. Les collections de
skins et les six familles du lootpool restent indépendantes de ces effets.
Ces profils produisent les effets et sons du tir existant. Dans la salle GIGN,
ils choisissent également le statut primaire de test : six impacts du même
vecteur en trois secondes déclenchent six secondes d'état visible. Les dégâts,
la dispersion et les munitions restent conservés. Les tirs ne créent aucune
réaction couplée automatique. Voir [la salle et ses règles](docs/TEST-ROOM.md).

## Essayer en jeu

Lancer `Jouer - Vector Fields.cmd`, puis **F3 > Weapon FX / R1**.
**Open FX test range** ouvre `vf_fx_range`. Choisir un profil et une cible
(concrete, metal, wood, flesh, sky ou moving brush), puis **Close and test**.
La cible flesh est un mannequin 3D. Les cinq couches peuvent être activées
séparément : muzzle, trails, particles, decals et sound.
**Return to gameplay / Kinetic** remet le profil normal.

L'atelier et la sélection des profils de test sont autorisés en solo ou
avec `sv_cheats 1`. Le serveur valide et réplique le profil ; un joueur qui
rejoint reçoit aussi les choix déjà actifs. Une fois `sv_cheats` désactivé,
une nouvelle demande de profil ou un tir remet l'override à zéro.

Commandes de console :

```text
vf_shotfx_lab
vf_shotfx hydro
vf_shotfx auto
vf_shotfx_layers 1 1 1 1 1
vf_shotfx_clear
vf_shotfx_audit
vf_shotfx_stats
vf_shotfx_debug 1
```

`clear` retire les effets transitoires et les huit types de marques R1,
ainsi que les compteurs de diagnostic. Il ne recharge pas la carte.

## Flash, traces et impacts

Le tireur voit une **étoile frontale dédiée**, centrée sur la bouche et placée
dans un plan perpendiculaire au canon. Ce sprite vient d'un atlas frontal
séparé : il n'est pas fabriqué à partir du jet de profil. Chaque vecteur a
sa propre forme radiale. Aucun plan axial n'est dessiné pour le viewmodel.
Depuis la version 0.20.4, l'étoile est deux fois plus grande au tir, plus
lumineuse et légèrement avancée devant la bouche pour mieux voir ses branches.

Depuis l'extérieur, le jet de profil utilise trois plans axiaux croisés.
Le rendu passe progressivement de ce jet à l'étoile lorsque la caméra
se rapproche de l'axe du canon. Les événements Studio 5001/5011/5021/5031
sont filtrés uniquement sur les modèles R1, pour éviter qu'un flash historique
Half-Life ne se superpose au profil choisi. Les autres modèles gardent leur
traitement existant.

Le moteur calcule le socket à l'extrémité réelle de la bouche R1 équipée,
y compris ses variantes. Les attachments 0, 1 et 3 fournissent respectivement
la position, l'axe et le haut ; l'attachment 2 de la culasse est conservé.
Le fallback avant la première image utilise l'orientation de l'événement de tir.

Chaque balle conserve la trace hitbox du MP5. Une trace visuelle brève relie
la bouche au contact ; Electro utilise un arc segmenté et Sonic une onde.
Les surfaces dures reçoivent une petite marque découpée par le moteur sur
la géométrie, y compris les brush entities mobiles. Les tailles des marques
sont de **4 à 7 unités de monde** : elles représentent une seule balle.
Le contact ajoute un petit éclat et quelques débris. Les surfaces métal,
bois et chair ont des réponses sonores distinctes. Les modèles 3D ne reçoivent
pas de decal plaqué ; le ciel ne reçoit ni marque ni son d'impact.

Le client borne les effets à 512 particules, 64 flashes et 64 traces.
Les textures sont préchargées hors de la mesure du coût de rendu.
`vf_shotfx_stats` affiche les contacts, sons déclenchés, particules actives,
maximum atteint et durée CPU moyenne du passage de rendu. Cette mesure
n'est pas une mesure complète des FPS ou du coût GPU.

## Assets et génération

- `data/weapon_fx.json` : profils, couleurs, dimensions, durées et prompts audio.
- `assets/weapon-fx/source-atlas.png` : atlas original, quatre colonnes et huit lignes.
- `assets/weapon-fx/source-muzzle-frontal.png` : huit étoiles vues de face,
  atlas 4 × 2 original ImageGen, centres d’émission alignés au socket.
- `assets/weapon-fx/source-muzzle-cones-mask.png` : jets axiaux sur fond noir,
  convertis en masques d'émission ; source active des textures de flanc.
- `assets/weapon-fx/*provenance.json` : prompts et provenance des images originales.
- `assets/weapon-fx/audio/shots` : 16 générations ElevenLabs, masters PCM et provenance.
- `build_weapon_fx.py` : 40 sprites natifs, 40 WAV, huit decals et catalogue C++.
- `build_weapon_fx_range.py` : petite carte de contrôle des matériaux.

Les images ont été créées avec ImageGen ; les sprites de Counter-Strike
inspectés comme références restent dans le dossier de build ignoré et ne
sont pas incorporés à ces assets. L'ancien essai `source-muzzle-cones.png`
est conservé pour comparaison mais n'est pas utilisé par le builder.

Chaque profil possède cinq sprites : jet axial, cœur frontal, impact,
particule et fumée. Les sprites utilisent le format GoldSrc index-alpha,
128 × 128 pixels, quatre frames (une pour les particules). Les huit decals
64 × 64 sont ajoutés au WAD local en conservant ses 222 entrées existantes.
Le WAD généré n'est pas un asset original à redistribuer indépendamment.

Chaque profil possède un son de départ et quatre sons de contact. Les 16
masters ElevenLabs sont conservés ; les variantes hard, metal, wood et flesh
ajoutent un bref transitoire matériel. L'export de jeu est mono PCM **11 025 Hz,
8 bits**, filtré et légèrement compressé pour une couleur sonore rétro.
Il s'agit d'un choix artistique pour ce build. Les masters restent disponibles
pour un export de meilleure fidélité. L'écoute des masters se fait dans
`assets/weapon-fx/audio/listen.html`.

Le build et le lancement ordinaires fonctionnent hors ligne avec ces sources.
La génération ElevenLabs ne se fait qu'en appelant explicitement
`python vector-fields/build_weapon_fx.py --generate-audio` ; elle réutilise
les clips présents. La clé locale chiffrée n'entre dans aucun asset généré.

## Vérification

```powershell
python vector-fields/build_weapon_fx_range.py
python vector-fields/build_weapon_fx.py
python vector-fields/tests/weapon_fx_test.py --mode assets
python vector-fields/tests/weapon_fx_test.py --mode native
python vector-fields/tests/weapon_fx_multiplayer_test.py
```

Les tests natifs utilisent des runtimes isolés et les DLL dans
`build/weaponfx-client` et `build/weaponfx-server`. Ils ne ferment pas la partie
normale. Compiler ces DLL avec des dossiers intermédiaires séparés lorsqu'un
autre atelier utilise déjà `build/obj-client` ou `build/obj-server`.

Le test des assets contrôle les formats binaires, palettes, frames, empreintes,
40 WAV et quatre variantes matérielles par profil. Le test solo effectue de
vrais tirs prédits pour les huit profils, vérifie les cinq cibles, les limites
du pool, le retour à zéro, la sauvegarde/recharge et le rejet d'un profil invalide.
Le test réseau emploie un serveur dédié loopback et deux clients : arrivée
tardive, effets distants, retrait des cheats et captures depuis le côté.
Les rapports sont dans `build/weapon-fx-*-verification.json`.

Les captures permettent un contrôle artistique, et les compteurs vérifient
les déclenchements audio ; ils ne remplacent pas l'écoute. Le réseau Internet,
les sessions prolongées et l'équilibrage des futurs effets restent à tester.

## Références vérifiées

Les quatre `cstrike/sprites/muzzleflash*.spr` de l'installation locale ont
été inspectés : sprites de type 2 (face caméra), tailles 48, 64, 72 et
48 pixels, respectivement une, trois, trois et une frames. Le moteur
[choisit son sprite par type de flash](https://github.com/FWGS/xash3d-fwgs/blob/9137964147d8f749dbeddf1cb5482c3d16f86e4a/engine/client/cl_tent.c),
puis varie frame et rotation ; cette fonction ne sélectionne pas la texture
selon l'angle de vue. Le SDK Valve
[déclenche le flash du viewmodel via EF_MUZZLEFLASH](https://github.com/ValveSoftware/halflife/blob/master/cl_dll/ev_common.cpp).
Ces références motivent l'assemblage axial dédié du R1 ; elles ne prétendent
pas décrire toutes les versions de Counter-Strike.
