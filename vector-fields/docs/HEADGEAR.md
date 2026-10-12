# Casques optionnels sur les cagoules

Le choix retenu est un **MDL d'accessoires sÃ©parÃ©, fusionnÃ© avec les os du
personnage au rendu**. Les vÃªtements continuent d'utiliser les 23 familles
existantes ; aucune texture de cagoule n'est repeinte pour porter un casque.

Le modÃ¨le `models/vf_headgear/headgear.mdl` contient six designs, dont cinq
avec deux positions de reference et une articulation continue. Son bodygroup contient douze choix, dont le
choix vide. Les cinq IDs existants restent identiques ; les nouvelles poses
et les deux accessoires supplÃ©mentaires sont ajoutÃ©s Ã  la fin.

| ID | PiÃ¨ce | Position |
| --- | --- | --- |
| 0 | Aucune | Cagoule seule |
| 1 | Anti-Ã©meute | VisiÃ¨re fermÃ©e |
| 2 | Spartiate | PortÃ© |
| 3 | Anti-Ã©meute | VisiÃ¨re relevÃ©e |
| 4 | Optique rouge | Devant les yeux |
| 5 | Optique verte | Devant les yeux |
| 6 | Optique rouge | Sur le front |
| 7 | Optique verte | Sur le front |
| 8 | Casque blindÃ© | Protection faciale fermÃ©e |
| 9 | Casque blindÃ© | Protection faciale relevÃ©e |
| 10 | Masque Ã  gaz | PortÃ© sur le visage |
| 11 | Masque Ã  gaz | RangÃ© au-dessus du crÃ¢ne |

Tous ses sommets appartiennent Ã 
`Bip01 Head`. Sa rÃ©fÃ©rence est exactement celle du GIGN ajustÃ©. Le moteur
associe les os par leur nom puis reprend leurs matrices animÃ©es pour dessiner
l'accessoire. Il utilise donc le mouvement rÃ©el de la tÃªte pendant la course,
l'accroupissement, la visÃ©e et les autres poses, y compris avec les trois
porteurs de l'arme R-01.

Ce principe est proche de la [fusion des os du SDK GoldSrc de Valve](https://github.com/ValveSoftware/halflife/blob/master/cl_dll/StudioModelRenderer.cpp).
Le projet dispose dÃ©jÃ  de son propre rendu d'assemblages dans
[`gl_vf.inc`](../engine/gl_vf.inc), avec les modes `VF_PART_MERGE` et
`VF_PART_SOCKET`. Pour ces piÃ¨ces rigides, une fixation Ã  un socket de tÃªte
serait Ã©galement possible ; la fusion permet ici de conserver directement les
coordonnÃ©es de la rÃ©fÃ©rence du personnage.

Un skin est une texture et ne peut pas crÃ©er le volume d'un casque. Un
bodygroup supplÃ©mentaire dans le modÃ¨le du personnage fonctionnerait aussi,
mais demanderait de recompiler et faire Ã©voluer ses modÃ¨les associÃ©s. Le MDL
sÃ©parÃ© convient au systÃ¨me modulaire existant et pourra accueillir d'autres
accessoires sans multiplier les apparences de cagoule.

La piÃ¨ce est dessinÃ©e dans l'assemblage existant. Aucune entitÃ© serveur, boÃ®te
de collision, hitbox de tÃªte ou donnÃ©e de protection n'est ajoutÃ©e. Son volume
visuel est inclus dans le cadrage du rendu, indÃ©pendamment de la collision.

## Essais disponibles

- Anti-Ã©meute : coque composite plus massive, facettes larges, plaques
  Ã©paisses, mentonniÃ¨re rigide, grosses charniÃ¨res et joint continu au front.
  La visiÃ¨re fermÃ©e rejoint la coque et les cÃ´tÃ©s. La version levÃ©e est
  la mÃªme piÃ¨ce tournÃ©e de 112 degrÃ©s autour de l'axe des charniÃ¨res.
  Le verre utilise le mode additif GoldSrc, comme approximation visuelle.
- Spartiate : calotte facettÃ©e plus large, bronze martelÃ© patinÃ©, plaques
  superposÃ©es aux tempes et aux joues, bande gravÃ©e, bossage du front,
  protÃ¨ge-nez, rivets et cimier bordeaux.
- Optique rouge : trois objectifs profonds en triangle, coque instrumentale
  rouge sombre, processeur latÃ©ral, cÃ¢blage et actionneur supÃ©rieur. Le bloc
  optique se replie de 80 degrÃ©s autour de son support frontal.
- Optique verte : deux grands objectifs dans des cages carrÃ©es, capteur
  dÃ©portÃ©, molettes, bras de maintien et cÃ¢blage. Les deux optiques utilisent
  une sangle autour de la tÃªte, une sangle de sommet et un boÃ®tier de batterie
  Ã  l'arriÃ¨re, sans calotte de casque sous les sangles.
  La variante verte possÃ¨de elle aussi une pose relevÃ©e sur le front ;
  batterie, sangles et supports restent Ã  leur place.
- Casque blindÃ© : d'aprÃ¨s la [rÃ©fÃ©rence fournie](../assets/headgear/references/ballistic-user.png),
  calotte noire profonde, protection des oreilles et de la nuque, protection
  intÃ©grale du visage avec une fenÃªtre horizontale Ã©troite et gros pivots
  mÃ©talliques. Toute la protection faciale se relÃ¨ve de 110 degrÃ©s ; la coque
  reste portÃ©e sur la cagoule.
- Masque Ã  gaz : d'aprÃ¨s la [rÃ©fÃ©rence fournie](../assets/headgear/references/gas-mask-user.png),
  visiÃ¨re panoramique, joint en caoutchouc continu, nez moulÃ©, valve frontale,
  filtre cylindrique inclinÃ© avec grille mÃ©tallique et harnais Ã  cinq points.
  Sa pose rangÃ©e place le mÃªme masque complet au-dessus du crÃ¢ne et adapte
  les attaches Ã  cette position. Il ne reste pas devant les yeux.

Les designs sont Ã©ditables dans [`headgear_designs.py`](../headgear_designs.py)
et [`headgear_extra_designs.py`](../headgear_extra_designs.py),
avec les primitives et matÃ©riaux de [`headgear_geometry.py`](../headgear_geometry.py),
compilÃ©s par [`build_headgear.py`](../build_headgear.py). Chaque version reste
sous 3 200 triangles. Les [sources des matÃ©riaux](../assets/headgear/README.md)
et les prompts imagegen sont conservÃ©s dans le projet ; leurs copies indexÃ©es
de 256 Ã— 256 pixels sont intÃ©grÃ©es au MDL. Les rÃ©fÃ©rences compilÃ©es SMD/QC et
le manifeste sont dans `generated/headgear/`. Les atlas et la gÃ©omÃ©trie des
personnages restent identiques.

AprÃ¨s compilation du client et des modÃ¨les, ouvrir l'essai isolÃ© :

```powershell
python play_headgear.py --helmet riot
python play_headgear.py --helmet riot-up
python play_headgear.py --helmet spartan
python play_headgear.py --helmet nvg-red
python play_headgear.py --helmet nvg-red-up
python play_headgear.py --helmet nvg-green
python play_headgear.py --helmet nvg-green-up
python play_headgear.py --helmet ballistic
python play_headgear.py --helmet ballistic-up
python play_headgear.py --helmet gas-mask
python play_headgear.py --helmet gas-mask-up
```

Dans la console du jeu :

```text
vf_headgear riot
vf_headgear riot-down
vf_headgear riot-up
vf_headgear spartan
vf_headgear nvg-red
vf_headgear nvg-red-up
vf_headgear nvg-green
vf_headgear nvg-green-up
vf_headgear ballistic
vf_headgear ballistic-up
vf_headgear gas-mask
vf_headgear gas-mask-up
vf_headgear none
```

Chaque pose portÃ©e accepte aussi le suffixe `-down` : `nvg-red-down`,
`nvg-green-down`, `ballistic-down`, `gas-mask-down`, comme `riot-down`.

La sÃ©lection concerne l'aperÃ§u du personnage, le joueur local et les cibles
dÃ©jÃ  prÃ©sentes dans le laboratoire. Elle est rÃ©initialisÃ©e au changement de
carte. Ces commandes historiques restent des essais locaux. Les cinq objets
de l'emplacement Casque, eux, sont sauvegardes et transmis aux autres clients. Les corps, fragments de mort et casques lÃ¢chÃ©s
restent hors du pÃ©rimÃ¨tre de ce prototype. Une intÃ©gration dÃ©finitive devra
lier le choix Ã  un objet sauvegardÃ© et Ã  l'Ã©tat rÃ©seau du personnage.

Les cinq paires de positions sont des rÃ©fÃ©rences 3D pour une future feature.
Aucune animation interactive de levÃ©e/descente, vision nocturne ni modification
de gameplay n'est ajoutÃ©e par cet essai.

## VÃ©rification

`tests/headgear_assets_test.py` vÃ©rifie les sommets compilÃ©s et le suivi de
1 848 poses issues des quatre porteurs rÃ©els. Il compare aussi la gÃ©omÃ©trie
compilÃ©e des fenÃªtres/objectifs dans les cinq paires et leur transformation
rigide. `tests/headgear_native_test.py` exerce les 48 assemblages (quatre porteurs,
douze choix), quatre angles de tÃªte, trois autres cagoules, la course,
l'accroupissement et les cibles existantes.
Il contrÃ´le Ã©galement le retrait du casque, la prÃ©servation d'une sÃ©lection
lors d'une commande invalide et les dimensions inchangÃ©es du joueur.

Le test utilise `native_workspace.py` : moteur temporaire par processus,
ressources immuables partagÃ©es par empreinte, DLL/configuration privÃ©es.
Les captures et logs sont archivÃ©s sous `build/native-evidence/` avant la
suppression de la session. Le runtime installÃ© ne reÃ§oit aucun fichier de test.
`--heads-only` permet une revue rapide des quatre angles avant le test complet.
Le lanceur `play_headgear.py` utilise la mÃªme prÃ©paration dans
`headgear_preview.py`. Il conserve sa session tant que la fenÃªtre de jeu est
ouverte, puis archive les preuves et la supprime Ã  la fermeture.

- [Les cinq paires portÃ©es/relevÃ©es](images/headgear-positions-in-game.jpg)
- [Les casques dÃ©taillÃ©s sous quatre angles](images/headgear-detail-in-game.jpg)
- [SystÃ¨mes optiques et sangles arriÃ¨re](images/headgear-optics-in-game.jpg)
- [Casque blindÃ© et masque Ã  gaz sous quatre angles](images/headgear-ballistic-gas-in-game.jpg)
- [Poses debout, course et accroupissement](images/headgear-animations-in-game.jpg)
- [Comparaison sur trois autres skins](images/headgear-skins-in-game.jpg)
- [Rapport de validation](validation/headgear.json)

## Skin DevTest

`Revoir la main DevTest.cmd`, ou `python vector-fields/play_headgear.py --devtest --helmet riot`,
ouvre une revue isolee avec les vrais maillages du personnage et des mains.
**H** declenche le geste, **F9** passe en troisieme personne et **F10** revient
en premiere personne. F2 / Casque permet de changer d'objet.

Les materiaux portent des mots, fleches et graduations : **PAUME / INT** en
orange, **DOS / EXT** en bleu, **POUCE** en jaune et **TRANCHE** en blanc.
Les reperes G/D, AVANT/ARRIERE/HAUT et les deux couleurs du bras permettent
de suivre les parties du maillage. Les deux rigs ont leur dos de main sur
l'axe local +Z et leur paume sur -Z ; le pouce et les doigts replies fournissent
le repere anatomique, independamment du motif d'un gant.

`headgear_devtest.py` attribue les materiaux depuis les faces et les os,
avec des UV de diagnostic propres a chaque face. Il verifie que les sommets,
normales, poids, os et octets d'animation restent identiques aux modeles
compiles. Les modeles DevTest sont dans `generated/headgear-devtest/` et sont
copies uniquement dans la session de revue. `tests/headgear_action_native_test.py
--quick --devtest` conserve les captures sous le prefixe `devtest-`.

- [Contact DevTest sous trois angles](images/devtest-hand-orientation.jpg)
- [Rotation du poignet et pouce cache de face](images/devtest-hand-rotation.jpg)
- [Levee de main DevTest en premiere personne](images/devtest-headgear-hand-sequence.jpg)
- [De la prise sur l'arme au retour](images/devtest-hand-weapon-transition.jpg)
- [Verification native DevTest](validation/headgear/devtest.json)
- [Empreintes et preservation des maillages](validation/headgear/devtest-models.json)

## Equipement et geste interactif

Dans F2 / Operateur, choisir **Casque**, puis l'un des cinq objets : anti-emeute,
balistique, optiques rouges, optiques vertes ou masque a gaz. Cliquer Equiper.
**H** appelle `vf_headgear_toggle`. La commande peut aussi etre liee a une autre
touche. Le casque spartiate conserve son essai statique et n'entre pas dans cette
premiere categorie, car il n'a pas de piece relevable.

Le geste dure 1,15 seconde : approche de la main gauche, mouvement de la protection,
puis retour a la prise sur l'arme. Le rendu superpose uniquement le bras gauche
en premiere et troisieme personne. La main droite et le socket de l'arme conservent
leurs matrices. Le tir/rechargement sont temporairement bloques ; une action deja
en cours, une recharge ou un franchissement empechent un nouveau geste.

Au contact, la paume est orientee vers l'equipement en troisieme personne.
En premiere personne, la main apparait sur la tranche cote pouce, les doigts courbes, puis monte
au-dessus du cadre pendant la manipulation. Elle redescend vers la prise sur
l'arme en fin de geste. La levee reste simple, depuis la pose equipee, sans
modifier la forme de la manche. [Sequence du geste](images/headgear-hand-sequence.jpg).
[Contact en troisieme personne sous trois angles](images/headgear-hand-contact.jpg).
En troisieme personne, le poignet tourne la paume vers le bord frontal du casque.
Le pouce reste ouvert mais passe derriere la main depuis la camera de face.
Le contact se fait pres du bord frontal du casque, plutot que sur sa tempe.
Les doigts inclinent legerement vers le front et le coude reste plus bas sur le
cote. La paume -Z regarde vers le casque ; le dos +Z reste vers l'exterieur.
La main droite garde sa pose ; les fichiers MDL/SMD de production, leurs
textures et les banques d'animation restent identiques.

Le serveur valide l'objet et conserve la position cible et l'heure de l'action.
`VFHeadgear` transmet l'index du joueur, la cible et l'age du geste, y compris
a l'arrivee d'un nouveau client. Le modele pivote sans changer brutalement de
bodygroup. La position equipee/relevee survit a save/load. L'emplacement est
optionnel, ajoute en index 21 pour garder tous les anciens indices d'arme.

L'API renderer 4 transporte explicitement le type et la phase du geste ; le
protocole equipement 5 ajoute le slot (VFBuild 66 octets, VFState 77). Il faut
compiler et livrer les deux DLL et le renderer ensemble.

`game_shared/vf_headgear.h`, `cl_dll/vf_headgear.inc`, `dlls/vf_headgear.inc`
et `engine/gl_vf_headgear.inc` isolent cette fonctionnalite. Aucun fichier SMD
des armes, du corps ou des animations de franchissement n'est modifie.

Pour compiler seulement les DLL sans regenerer les banques de l'autre atelier :
`powershell -File vector-fields/build_headgear_action.ps1`. Le dossier prive
`build/headgear-action/` contient les candidats. `tests/headgear_action_native_test.py`
controle les deux directions dans les deux vues, les matrices de la main droite
et de l'arme, le refus des demandes repetees et la sauvegarde.
La capture DevTest de face controle aussi que la zone de la main ne contient
aucun pixel jaune du pouce. Les faces partagees entre le pouce et la paume
gardent leur marquage de surface ; seules les faces entierement liees au pouce
sont jaunes.

Pour des revues de candidat plus rapides, `VF_HEADGEAR_READONLY_ASSETS=1`
lit les ressources Half-Life dans leur bibliotheque d'origine. Les fichiers
client/serveur, configurations, sauvegardes et modeles marques restent dans
une session isolee. Les groupes de modeles actuels et les anciens porteurs
a la racine sont copies ; les anciens modeles d'atelier inutilises sont omis.
Le mode normal conserve la copie complete des bibliotheques.

La compilation native reste parallele ; les tests internes du moteur sont
executes successivement. Les deux executables de test d'images utilisent les
memes fichiers `test_gen.*` et peuvent planter s'ils les ecrivent simultanement.


## Vision et audio des équipements

**H** relève ou abaisse la protection sélectionnée. Cinq textures RGBA peintes à l'avance représentent les deux visières, le masque à gaz et les optiques rouges/vertes. Le code charge les sprites natifs correspondants et module leur opacité selon la phase du geste. Les joints, les plaques opaques, les lentilles et les détails viennent des images ; le centre de visée reste transparent. Les overlays sont absents en troisième personne, en spectateur, après la mort et pendant la sélection d'équipement.

Les [sources PNG et les prompts](../assets/headgear/hud/README.md) sont conservés. `build_headgear_hud.py --ensure` utilise une compilation hors ligne et vérifie les sorties par leur contenu, suivant le procédé des effets de statut. Le lancement normal et les essais isolés déploient les cinq sprites. `vf_headgear_hud 0` désactive la présentation et les effets optiques locaux ; `vf_headgear_hud_info` donne le type, l'opacité et la texture chargée.

Les optiques rouges ajoutent un premier repérage infrarouge par contour chaud sur les opérateurs effectivement visibles ; ce prototype ne simule pas une caméra thermique complète ni une vision à travers les murs. Les optiques vertes ajoutent une lumière locale verte pour la faible luminosité. Ces traitements du monde sont séparés des textures du HUD.

Six sons réutilisables couvrent les deux directions des trois familles : charnière/loquet de visière, joint hermétique de masque et pose/activation électronique des lunettes. Le serveur émet un son positionnel par geste, sur le canal des objets ; `vf_headgear_sfx_volume` règle son volume. Les fichiers sont générés avant le lancement et ne nécessitent aucun service externe en jeu.

Les six acteurs existants disposent chacun de quatre nouvelles répliques : une générique et une propre à chaque famille. Au début de l’abaissement, avant que le visage soit couvert, le serveur choisit automatiquement entre la phrase générique et la phrase contextuelle, selon l'acteur, la famille, la priorité, les délais et la dernière phrase utilisée. Les répliques de blessure ou de mort gardent leur priorité. Les nouvelles phrases utilisent les mêmes identités vocales que les banques existantes.

Quand une visière encombrante ou le masque à gaz est fermé, les répliques du joueur utilisent des variantes filtrées des enregistrements existants. Aucune nouvelle interprétation n'est créée pour cet effet. Le filtre hors ligne réduit les aigus et conserve la durée. Dès que l'objet est relevé, les prochaines répliques reprennent leur fichier normal. Les lunettes ne modifient pas la voix. Le filtre couvre toutes les familles de dialogue : rechargement, taunt, réponse au taunt, états et combinaisons, douleur, santé basse, armure brisée, kill, arrivée et réapparition. Les cris de mort restent leurs fichiers originaux et les annonces d’activation sont toujours normales. Les répliques privées restent audibles uniquement par leur propriétaire.

`headgear_audio.py build` prépare les variantes filtrées et l'atelier d'écoute sans appel réseau. `headgear_audio.py generate` est réservé à la création initiale des nouveaux sons et des 24 répliques. [Atelier d'écoute](../generated/headgear-audio/listen.html). La commande développeur `cmd vf_headgear_voice_preview generic|visor|mask|goggles` permet de les auditionner.

`tests/headgear_feedback_test.py` vérifie les textures RGBA, la transparence, les formats audio et la conservation des performances. Son option `--native` contrôle en jeu les cinq overlays, leurs transitions, les sons, les six acteurs et les voix filtrées. Le test réseau contrôle la réception positionnelle de la réplique par les deux clients et l'absence de répétition à l'arrivée tardive d'un joueur.


À la mort, le modèle de cadavre conserve les cinq familles de textures, mais ne reprend pas le MDL optionnel de casque/masque : celui-ci disparaît. Aucun objet physique ne tombe au sol. Ce comportement est conservé volontairement.

La banque filtrée contient uniquement les répliques ordinaires des six acteurs : 227 variantes couvrant 30 événements. Les annonces d’activation et les 102 cris contextuels de mort ne sont ni filtrés, ni dupliqués. L’annonce commence au début du geste ; le loquet et les autres sons restent synchronisés au mouvement. Le rattrapage d’un tick tardif et l’absence de répétition introduits par l’audit sont conservés.

Les tests font partie des suites centrales `policy`, `assets`, `native` et `multiplayer`. Le test C++ `voice_filter` vérifie toute la banque, les exceptions et les transitions. Le test natif vérifie le choix des fichiers pour les 30 événements avec le masque porté puis relevé, ainsi que les cris de mort originaux. Les essais graphiques et réseau utilisent les binaires candidats dans des sessions privées, des ports locaux attribués par le système et l’archivage atomique de `native_workspace.py` ; ils ne modifient pas le runtime installé.

À la fin d'un franchissement ou d'une glissade, le client remet aussi à zéro l'état de franchissement porté par le modèle de vue réutilisé. Un ancien état non nul empêchait le renderer de composer le geste H malgré les sons et la phase de casque reçus. La validation du Relais R1 couvre H après glissade et après le parcours F4 (`map vf_range; exec vf_start.cfg`), avec le HUD actif, en 1920 × 1080 et avec l'horloge normale du jeu. `tests/headgear_f4_native_test.py` conserve ce dernier scénario dans la suite centrale. Les preuves figurent dans `docs/validation/first-person-motion/`.
