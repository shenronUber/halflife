# Cinq univers assortis : personnages GIGN et Relais R-01

Cinq nouveaux ensembles, ajoutés aux six précédents sans les remplacer.
Chaque ensemble comprend un atlas de personnage et une banque de seize matières
pour les pièces d'arme. Génération par l'outil **ImageGen intégré**, sans CLI API.

| Univers | Personnage | Arme | ID personnage | Finition R1 |
| --- | --- | --- | --- | --- |
| Première Guerre mondiale | [Sentinelle des tranchées](personas/ww1-trench/texture-atlas.png), laine bleu horizon et cuir | [Grande Guerre](r01/variants/ww1-trench/texture-atlas.png), noyer, acier bleui et laiton | 183 | 7 |
| Mineur / Bedrock | [Mineur des profondeurs](personas/bedrock-miner/texture-atlas.png), toile ocre et protection charbon | [Bedrock](r01/variants/bedrock-miner/texture-atlas.png), basalte, acier et verre ambré | 184 | 8 |
| New York noir | [Détective de minuit](personas/new-york-noir/texture-atlas.png), tweed, gabardine et écharpe | [New York noir](r01/variants/new-york-noir/texture-atlas.png), métal noir, nickel et cuir bordeaux | 185 | 9 |
| Naufragé | [Naufragé des rivages](personas/castaway/texture-atlas.png), fibres, toile récupérée et pagne de feuilles sur jambes couvertes | [Bois de naufrage](r01/variants/castaway/texture-atlas.png), bois flotté, silex, coquillages et corde | 186 | 10 |
| Plongée | [Plongeur des abysses](personas/abyss-diver/texture-atlas.png), néoprène pétrole, joints noirs et coutures jaunes | [Abysses](r01/variants/abyss-diver/texture-atlas.png), acier marin, laiton et verre aqua | 187 | 11 |

## Essayer

À la racine du projet, lancer **Jouer - Vector Fields.cmd**.
Le lanceur équipe la sentinelle et son R1 Grande Guerre, puis ouvre la deuxième
page du filtre GIGN, où les cinq nouvelles tenues sont regroupées.

- Personnage : choisir une tenue, « Appliquer aux 5 zones », puis « Appliquer ».
- Arme : F11, choisir « Toute l'arme », parcourir FINITION, puis « Appliquer ».
- Les cinq zones de personnage et les douze emplacements d'arme restent
  sélectionnables séparément pour créer des mélanges.
- Les anciens lanceurs restent utilisables ; redémarrer une session pour
  charger les modèles et catalogues mis à jour.

Pour ouvrir directement un autre ensemble :

```powershell
python vector-fields/play_expeditions.py --theme bedrock-miner
python vector-fields/play_expeditions.py --theme new-york-noir
python vector-fields/play_expeditions.py --theme castaway
python vector-fields/play_expeditions.py --theme abyss-diver
```

## Couverture et direction artistique

Les cinq nouvelles tenues couvrent les mains, les pieds, les bras, les jambes,
le torse, le cou et la tête. Seules les ouvertures des yeux révèlent le visage.
Les lunettes du soldat, du mineur et du plongeur montrent les yeux à travers
un verre clair peint. Le détective conserve un masque et une écharpe ; sa
petite zone de nuque découverte dans le premier jet a été recouverte par une
seconde édition ImageGen. Le naufragé porte des enveloppes opaques sous le
pagne pour respecter la même règle.

Cette règle s'applique aux cinq nouveaux personnages ; les anciennes tenues
et les personnages de référence sont conservés. Les mains en vue subjective
restent celles du modèle d'arme, avec ses propres gants et manches.

Le lanceur et F11 conservent maintenant le mode libre du personnage.
Changer une finition du R1 ne remplace donc plus la tenue choisie.
Une sélection d’arme confirmée remplace seulement les essais locaux d’armes.

## Modèles communs et limites

Le corps GIGN conserve ses 740 triangles, cinq zones et raccords ajustés.
Il contient maintenant douze familles de texture : original, six précédentes
et cinq nouvelles. Le R1 conserve ses 26 pièces et trois rigs, avec douze
finitions natives par pièce. Aucune nouvelle copie de maillage n'est créée
pour chaque texture. Le module le plus chargé utilise 72 textures, sous la
limite de 100 de StudioMDL.

Les atlas sources restent en 1254 × 1254. Le personnage est compilé à
512 × 512 ; chaque case d'arme à 256 × 256, palette de 256 couleurs.
Les longues surfaces du R1 gardent le mapping répété à échelle isotrope.
La culasse n'a ni texte ni flèche qui rendrait la répétition gênante.

Les casques, cordages, valves, verres et plaques sont des motifs peints sur
les formes existantes. Une nouvelle silhouette de casque, un manteau long,
des bouteilles de plongée ou des branches saillantes nécessiteraient de
nouvelles pièces géométriques. Les fonctions de l'arme restent celles du R1.
Son modèle porté en troisième personne reste le modèle stock.

## Sources, prompts et reconstruction

Chaque atlas se trouve dans son dossier lié dans le tableau, avec son
`prompt.txt` exact. Le détective possède aussi
[coverage-fix-prompt.txt](personas/new-york-noir/coverage-fix-prompt.txt).
Le [manifeste du pack](expeditions-01.json) et la
[provenance ImageGen](expeditions-01-generation.json) conservent les liens
entre les dix livrables et leurs fichiers générés. Aucun asset du jeu ne
dépend uniquement du cache ImageGen : tous sont copiés dans ce projet.

```powershell
python vector-fields/build_r01_texture_variants.py
./vector-fields/build.ps1
python vector-fields/play.py --visual-lab --deploy-only
python vector-fields/play_expeditions.py --deploy-only
python vector-fields/tests/personas_engine_test.py
python vector-fields/tests/r01_styles_engine_test.py
python vector-fields/tests/expeditions_pack_test.py
```

## Aperçus et contrôles

- [Planche compacte des cinq ensembles](../build/expeditions-five-sets.jpg)
- [Les cinq ensembles dans le moteur](../build/expeditions-five-pairs-in-game.jpg)
- [Les cinq personnages](../build/expeditions-five-characters-in-game.jpg)
- [Détail des masques dans les atlas](../build/expeditions-face-coverage.jpg)
- [Contrôles GIGN](../build/personas-verification.json)
- [Contrôles R1](../build/r01-styles-verification.json)
- [Contrôles du lanceur assorti](../build/expeditions-verification.json)

Les contrôles GIGN couvrent toutes les familles sur les cinq zones, les
raccords compilés et 18 poses issues de six animations. Les captures natives
montrent chaque thème de face et de dos. Les contrôles R1 comparent les
maillages entre finitions, parcourent les finitions par l'interface, montrent
la première personne et vérifient l'annulation et les sauvegardes.

Validation finale : 41 captures GIGN, 60 couples famille/zone, raccords sans
écart sur les 18 poses testées ; 29 captures R1, 312 couples pièce/finition.
Le contrôle UV sur les 24 formes historiques conserve un rapport d’échelle
de 1:1. Le nouveau lanceur est testé avec le personnage et le R1 ensemble,
y compris la réouverture de F11, le changement de finition et la sauvegarde.
