# Vector Fields — laboratoire des armes

La bibliothèque collectée est maintenant intégrée au prototype 0.10 : lancer
`Jouer - Vector Fields.cmd`, puis F7 / Arsenal. Voir [le guide actuel](../vector-fields/README.md).
Les instructions ci-dessous décrivent le premier laboratoire, conservé pour référence.

Prototype local utilisant les DLL client et serveur du SDK officiel Half-Life,
compilées sans modification du code de jeu, et Xash3D FWGS en 32 bits.

## Jouer

Fermer la session de jeu avant de changer d'arme, puis double-cliquer sur
`Jouer - Xash3D.cmd` à la racine du projet. Choisir un numéro ; Entrée sélectionne
le numéro 14, l'hybride HK416 + chargeurs LR-300.

Le lancement lit les ressources de l'installation Half-Life existante dans
`F:/SteamLibrary/steamapps/common/Half-Life`. Les fichiers du laboratoire sont
dans `runtime/xash3d/vf_lab`.

| Commande | Action |
| --- | --- |
| ZQSD (AZERTY) | Déplacement |
| Souris / clic gauche | Viser / tirer |
| Clic droit | Lance-grenades |
| R | Recharger après avoir tiré |
| Espace / Ctrl | Sauter / s'accroupir |
| 1 / 3 | Pied-de-biche / fusil |
| F4 | Recommencer la salle |
| F6 | Ajouter des munitions |
| F8 | Capture du jeu |
| F10 | Console |

Ces raccourcis sont appliqués par le lanceur. Pour les modifier durablement,
adapter `play.py`, qui régénère `lab_controls.cfg` au lancement.
La souris est configurée en visée libre permanente (`+mlook`) sans déplacement
du joueur. Les noms `w` et `a` dans la configuration désignent les positions
physiques des touches **Z** et **Q** d'un clavier AZERTY dans Xash3D.

`Jouer - Half-Life.cmd` prépare le même laboratoire dans l'installation Steam
pour une comparaison avec GoldSrc. Ce second parcours n'a pas été testé en jeu.

## Armes disponibles

Les dix téléchargements GameBanana fournissent treize choix d'origine :

| Numéro | Modèle |
| --- | --- |
| 1–4 | Colt M4A1, M16A2, M16A3, M727 |
| 5 | HK416 |
| 6 | LR-300 |
| 7 | Morita 9mm |
| 8 | AK-47 |
| 9 | AKS-74U + Tishina |
| 10 | M4A1 avec chargeur tambour |
| 11 | M4 avec viseur et lance-grenades |
| 12 | Tigg M4, modèle beaucoup plus détaillé |
| 13 | Colt 727 basse définition |
| 14 | Hybride HK416 + chargeurs LR-300 |

Les sources, crédits et conditions des auteurs sont conservés dans
`catalog/selection.json`. `catalog/library.json` contient les chemins et les
caractéristiques des modèles. Les quatorze fichiers ont un en-tête GoldSrc
IDST v10 valide et les séquences attendues par le fusil Half-Life ; seul le
numéro 14 a été confirmé en jeu. Les autres choix restent à essayer.

## Ce qui a été vérifié le 7 octobre 2026

- La salle de test et l'arme s'affichent dans Xash3D ; Mathieu confirme que le
  déplacement, le tir et le rechargement fonctionnent.
- Le fichier déployé est identique à l'hybride compilé. Sa géométrie inclut le
  sous-modèle `LR300_magazine` actif par défaut ; sa texture `lr300_mag.bmp`
  remplace `mag.bmp`. Détails dans `catalog/hybrid-verification.json`.
- L'assemblage retire 1 228 triangles du HK416 et ajoute 552 triangles issus
  du LR-300. Les mains et les neuf séquences d'animation du HK416 sont conservées.
- Les DLL client et serveur déployées sont identiques à celles du test de
  compilation du SDK. Aucun portage du code de jeu n'a été nécessaire ici.

L'hybride concerne la vue à la première personne. Les modèles au sol et portés
par un autre joueur restent ceux du HK416. La capacité, les dégâts et les
autres règles restent ceux de l'arme Half-Life. Il n'y a pas encore de système
de combinaison en cours de partie ni de test multijoueur. Cet essai ne prouve
pas une identité parfaite de comportement entre Xash3D et GoldSrc.

## Sources et reproduction

Le moteur et son code source proviennent de
[FWGS/xash3d-fwgs](https://github.com/FWGS/xash3d-fwgs), révision
`9137964147d8f749dbeddf1cb5482c3d16f86e4a`. Le code, avec ses sous-modules,
est dans `runtime/engine-source`. Le moteur exécuté est le binaire officiel
Windows i386 ; le moteur lui-même n'a pas été recompilé ou modifié.

Scripts : `fetch_catalog.py` pour les métadonnées, `download_assets.py` pour
les archives, `mix_models.py` pour l'assemblage des SMD décompilés et
`build_range.py` pour la carte. `play.py` déploie et lance le laboratoire.
La fabrication emploie le décompilateur officiel Xash3D, le StudioMDL Valve
compilé localement et les compilateurs SDHLT. Aucun fichier de moteur issu
d'une fuite n'a été utilisé.

Les téléchargements, modèles dérivés, binaires et ressources Valve sont
exclus de Git. Cet essai est local : les conditions des modèles téléchargés
demandent une autorisation avant redistribution de versions modifiées.
L'accès au code Xash3D ne change pas les licences du SDK et des ressources.


## Bibliothèque d’armes et d’accessoires — 8 octobre 2026

Cette section complète le premier laboratoire décrit plus haut. Le projet principal
et son moteur modifié sont documentés dans `../vector-fields/README.md`.

Ouvrir **[catalogue.html](catalogue.html)** dans un navigateur : recherche et tri
par votes, filtres GoldSrc/Source, aperçus des armes et vue 3D des pièces isolées.
Glisser sur la pièce pour tourner ; utiliser la molette pour zoomer.

### Collection ajoutée

- 30 nouveaux packs GameBanana, 344 179 027 octets d’archives (environ 344 Mo).
  24 packs GoldSrc et 6 packs Source. Sélection : popularité, diversité de
  silhouettes et présence d’accessoires, pas seulement le nombre de likes.
- 595 fichiers `.mdl` : 504 modèles IDST v10, 24 groupes d’animations IDSQ v10,
  67 modèles Source v44/v48. 545 empreintes distinctes. Ce décompte inclut les
  variantes, mains, vues joueur et modèles au sol ; il ne compte pas les armes.
- Le premier fichier courant de chaque fiche a été choisi. Les archives de
  variantes et les fichiers sources supplémentaires restent listés, sans être
  tous téléchargés. Aucun exécutable des packs n’a été lancé.
- Kenney Blaster Kit 2.1, sous CC0, téléchargé séparément : 40 modèles,
  dont trois lunettes, deux silencieux et deux chargeurs. Son style est plus cartoon.
- Le pack modulaire gratuit de sschocolate a été repéré mais son téléchargement
  n’a pas abouti (HTTP 403 et navigateur intégré indisponible). Aucun contenu payant
  n’a été acheté. Les autres pistes se trouvent dans l’onglet bibliothèques.

### Test de démontage réellement effectué

12 pièces sont dans `generated/accessories/`, chacune avec OBJ/MTL/PNG,
SMD/QC/BMP, MDL recompilé et `provenance.json` :

- ACOG du MP5, Aimpoint du M4, holographiques AUG/HK416/SCAR et compact UTS15 ;
- deux crosses, deux silencieux, une poignée verticale et un chargeur.

Les six entrées de visée sont des variantes : AUG/HK416/SCAR ont une géométrie
très proche. L’UTS15 est plus grossier et doit rester secondaire. L’Aimpoint
(2 974 triangles) et le chargeur M4 (2 076) gagneraient à être allégés avant
l’assemblage de nombreuses pièces. Ces nombres ne constituent pas un benchmark.

L’ACOG est extrait comme sous-modèle complet ; les autres pièces utilisent des
triangles entiers sélectionnés par leurs matériaux d’origine. Aucun découpage
au plan n’a été nécessaire. Leurs UV et textures sont conservés. Le repère est
recentré pour inspection : ce n’est pas encore un point de fixation standardisé.

Vérification : 12 compilations StudioMDL réussies, relecture IDST v10, nombre de
triangles conservé, racine identité et limites géométriques à 0,011 unité près
(arrondi du compilateur au centième). Planche de rendu inspectée dans
`generated/accessories/contact-sheet.png`. Catalogue vérifié dans Edge headless
avec capture 1920 × 1080 : chargement des 12 pièces WebGL, recherche, filtres,
changement d’onglet et zoom. Résultats : `catalogue-verification.json` dans ce
même dossier.

**Limites :** ces nouveaux modèles sont préparés dans la bibliothèque ; ils ne
sont pas encore montés sur les armes du jeu. Les verres utilisent ici leurs
textures opaques : transparence, chrome et effets spécifiques restent à traiter.
Les bases de fixation, les axes, l’échelle, les animations et les vues à la
troisième personne doivent être contrôlés pour chaque intégration. Pas de nouveau
benchmark en jeu pendant cette collecte. Aucun fichier du jeu en cours n’a été remplacé.

### Direction proposée

Partir de quelques corps d’armes cohérents (AR/M4, AK, MP5 et une famille
industrielle TFC). Ajouter des attaches nommées pour optique, bouche, crosse,
poignée et alimentation. Classer les pièces par type de fixation et fixer une
échelle commune. Construire ensuite les adaptateurs, recolorer avec une palette
commune et prévoir des versions allégées. Cela évite de cisailler arbitrairement
les armes complètes et préserve mieux leurs silhouettes et leurs animations.

Les MDL Source ne sont pas compris nativement comme des MDL GoldSrc. Les six
packs Source sont seulement archivés : leur conversion par Crowbar, récupération
des textures et recompilation n’a pas été testée dans cette étape. Les fichiers
FBX/OBJ de créateurs rétro se prêtent à un travail de préparation dans Blender,
puis à un export et une compilation pour le moteur ; ils ne sont pas des imports
directs non plus. Blender n’a pas été nécessaire au test de démontage GoldSrc.

### Traçabilité et reproduction

- `catalog/expansion/collection.json` : fiches, votes datés, crédits, licences,
  archive choisie et SHA-256.
- `catalog/expansion/inventory.json` : chemins, versions, matériaux et variantes.
- `generated/accessories/manifest.json` : sélection exacte de chaque pièce,
  géométrie, provenance et contrôles de compilation.
- `expand_library.py` : retéléchargement/extraction des fiches mises en cache.
- `inspect_accessories.py` : inventaire, extraction et recompilation.
- `render_accessories.py`, `render_donors.py`, `build_catalogue.py` : aperçus et catalogue.

Les créations et dérivés GameBanana restent locaux. Plusieurs licences affichées
interdisent de diffuser une version modifiée ; la gratuité du projet ne supprime
pas ces conditions. Vérifier les autorisations de chaque créateur avant de partager
les ressources dérivées. Kenney CC0 et les packs avec une licence autorisant les
adaptations sont les bases les plus simples pour un contenu redistribuable.
