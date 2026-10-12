# Poignées et finitions R1

La révision `finish-2026-10-11` reprend les quatre poignées arrière, ajoute une
seconde texture propre à chacun des onze châssis métalliques et affine l’A-47.
Les plaquettes sont galbées, avec une armature continue, des vis noyées, un
sabot emboîté et un talon biseauté. Les surfaces des crosses restent à leurs
positions natives. Les mains et les animations ne sont pas réexportées.

L’A-47 reprend les principes visuels de l’AK de **Modern Warfare 3 (2011)** :
tôle emboutie, rivets sobres et garde-main sombre nervuré. Il s’agit de notre
géométrie et de nos matériaux Blender, sans asset importé de Call of Duty.
Référence : [capture de recharge MW3](https://www.imfdb.org/wiki/File:MW3-AK-2.jpg).

Chaque châssis métallique propose sa finition originale et `medieval-forge`,
avec acier forgé, ferrures patinées, laiton et surfaces brunes. Ossuaire et
Roncier conservent leur atlas organique propre. Les quatre poignées gardent
deux finitions adaptées à leur crosse. Le catalogue comporte désormais
**72 formes et 130 variantes fixes**. Les anciennes finitions retirées sont
archivées dans l’atelier ; les objets sauvegardés encore présents gardent leur ID.
Une finition retirée utilise la migration existante vers le défaut de son slot.

Les quinze modèles révisés possèdent deux maps physiques de 512px pour GoldSrc,
issues de deux atlas Blender de 2048px. Les quatorze indices de skin historiques
restent valides : l’indice de la variante retenue désigne sa seconde map, les
autres désignent l’originale. Le gameplay expose uniquement les deux choix
validés. Les fichiers Blender conservent les deux sources procédurales éditables.

## Inspection et essais

`Revoir les poignées et finitions - Vector Fields.cmd` lance une session via
`native_workspace.py`, sans build des DLL et sans écrire dans le runtime partagé.
1–4 : Fonderie, A-47, Ossuaire, Roncier ; 5–6 : variantes médiévales Fonderie/A-47 ;
7–0 : les quatre poignées ; F11 : inventaire de l’arme.
À la fermeture, les captures et logs sont archivés dans `build/native-evidence`,
puis le moteur temporaire est supprimé. Les assets proviennent du cache immuable
et les quinze modèles révisés sont détachés avant tout remplacement.

Les sources et preuves sont dans `weapon-workshop/finish-2026-10-11` :
`review.html`, `grips.jpg`, `metal.jpg`, `hold-proof`, `native-captures` et leurs
rapports. Le serveur local d’inspection utilise le port 8769.

`tests/r01_finish_revision_test.py` contrôle les maps natives, les surfaces des
crosses, les 52 appuis poignée/châssis et les anneaux concentriques de l’A-47.
L’essai natif sélectionne les IDs de l’inventaire joueur, contrôle explicitement
leur application, effectue quatre tirs/recharges et audite les 2409 assemblages
simples ou par paire. Il ne représente pas une inspection visuelle de toutes les
931 627 008 armes combinatoires possibles.
