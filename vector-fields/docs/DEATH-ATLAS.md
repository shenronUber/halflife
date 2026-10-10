# Atlas des morts et fragments elementaires

Le jeu contient dix animations de mort importees : trois Quaternius/KayKit et sept Mixamo, plus les sept morts historiques et la contraction electrique personnalisee. L atlas couvre les huit elements et les huit reactions. Une meme gestuelle peut servir a plusieurs reactions ; leurs particules donnent la signature de la combinaison.

## Choix et essai en jeu

Lancer `Jouer - Vector Fields.cmd`, puis **F4** pour la salle et **F8** pour les morts. L onglet **Atlas** propose les elements puis les reactions. Choisir un effet et une zone a droite provoque une mort avec le mouvement automatique correspondant. **Catalogue** contient trois pages de mouvements a imposer manuellement.

| Effet | Gestuelle automatique | Particules des morceaux |
|---|---|---|
| hydro | Perte d equilibre (impact_right, kaykit_b) | Gouttes bleues et rides |
| electro | Contractions (electric) | Arcs et etincelles ambre |
| cryo | Effondrement raide (kaykit_a) | Eclats cyan et brume froide |
| thermal | Douleur et recul (recoil_back) | Flammes et braises orange |
| toxic | Agonie lente (agony) | Spores violettes |
| corrosion | Douleur et chute (recoil_right, collapse) | Gouttes et bulles acides vert jaune |
| sonic | Chute laterale (collapse_left) | Ondes roses |
| kinetic | Recul violent (impact_front) | Traits d impact et etincelles |
| arc_chain | Contractions et gouttes (electric) | Gouttes bleues et arcs ambre |
| superconduction | Contractions et givre (electric) | Cristaux bleus et arcs blancs |
| shatter | Rupture et chute raide (kaykit_a) | Eclats et gerbe blanche |
| resonant_impact | Impact avec rotation (spin, impact_front) | Ondes roses et eclats couleur metal |
| cavitation | Douleur et chute laterale (recoil_right) | Bulles acides, ondes et gouttes |
| caustic_contagion | Agonie corrosive (agony) | Brume verte, gouttes et spores violettes |
| toxic_ignition | Douleur et combustion (recoil_back) | Brume et flammes |
| steam_veil | Recul dans la vapeur (recoil_back) | Vapeur blanche et gouttes bleues |

## Inventaire verifie

[Mixamo](https://www.mixamo.com/) fournit les mouvements ; le [miroir GLB inspecte](https://github.com/MisterYI/deevid-mixamo-assets) contient 886 animations. Les 24 candidats ci-dessous ont ete telecharges et leurs courbes mesurees, puis sept ont ete adaptes au GIGN. Les noms ne garantissent pas le contenu : plusieurs fichiers inspectes se terminent debout et sont ecartes. La liste integrale des 886 fichiers et les empreintes sont dans `assets/animations/death-inventory.json`.

[Quaternius](https://quaternius.itch.io/universal-animation-library) et [KayKit](https://kaylousberg.itch.io/kaykit-character-animations) complètent cet inventaire avec les trois morts deja transferees. Leurs catalogues locaux sont egalement recenses dans le JSON.

| Candidat Mixamo | Duree | Decision | Motif |
|---|---:|---|---|
| Crouch_Death | 2.33 s | reserve | Depart accroupi : a conditionner a la posture du joueur. |
| Death | 3.0 s | integrated | Mixamo : chute au sol |
| Death_Crouching_Headshot_Front | 2.5 s | excluded | Ce fichier se termine debout dans le miroir inspecte ; le nom ne suffit pas. |
| Death_From_Right | 3.29 s | integrated | Mixamo : impact lateral |
| Death_From_The_Front | 3.42 s | integrated | Mixamo : recul frontal |
| Dying | 5.75 s | integrated | Mixamo : agonie lente |
| Falling_Down | 2.25 s | reserve | Chute exploitable, reserve aux pertes d equilibre. |
| Falling_Flat_Impact | 1.54 s | reserve | Commence deja en l air ; convient a une chute depuis une hauteur. |
| Flying_Back_Death | 2.33 s | excluded | Le fichier inspecte se releve et se termine debout. |
| Hit_Reaction | 2.71 s | excluded | Reaction a un coup suivie de recuperation, pas une mort complete. |
| Injured_Hurting_Idle | 2.25 s | excluded | Boucle de blessure sans chute finale ; derive horizontale. |
| Injured_Stumble_Idle | 5.04 s | excluded | Titubement puis recuperation, utilisable comme amorce future. |
| Livershot_Knockdown | 9.17 s | excluded | La cible se releve ; 9.17 s, ne pas figer en cadavre. |
| Mutant_Dying | 4.58 s | reserve | Chute complete mais gestuelle de creature a reserver aux ennemis appropries. |
| Rifle_Run_To_Dying | 2.46 s | reserve | Mort en course avec 4 m de translation source ; contexte locomotion requis. |
| Standing_Death_Backward_01 | 3.33 s | excluded | Le fichier du miroir se termine debout ; ecarte apres mesure. |
| Standing_Death_Left_01 | 2.25 s | integrated | Mixamo : chute laterale |
| Standing_React_Death_Backward | 3.62 s | integrated | Mixamo : douleur puis recul |
| Standing_React_Death_Right | 3.5 s | integrated | Mixamo : douleur puis chute |
| Sword_And_Shield_Death | 2.29 s | reserve | Chute complete, pose des mains associee a une arme et un bouclier. |
| Two_Handed_Sword_Death | 2.38 s | reserve | Chute complete, pose des mains associee a une arme a deux mains. |
| Walking_To_Dying | 4.04 s | excluded | Pas de chute finale dans ce fichier inspecte. |
| Zombie_Death | 2.96 s | reserve | Chute complete avec posture de zombie. |
| Zombie_Dying | 3.33 s | reserve | Chute complete avec posture de zombie. |

## Membres et presentation

Chaque zone retiree genere une piece anatomique reconnaissable et trois petits fragments, habilles selon le theme de la victime. Ce sont des entites Studio propulsees, soumises a la gravite et aux collisions du decor. Elles ne se bloquent pas entre elles ni contre les personnages. Au repos, la piece entiere est orientee et posee au sol selon les dimensions mesurees de son maillage. Les coupes utilisent les textures de plaies existantes.

Pendant les 2,2 premieres secondes de mouvement, les morceaux emettent du sang et les couches visuelles de leur effet. Les particules conservent leur position dans le monde, leur vitesse et leur duree : la trainee reste derriere le membre. Une reaction conserve toutes ses couches (deux ou trois). Le cadavre porte sa propre signature pendant la duree indiquee dans l atlas, jusqu a 6,2 secondes pour l agonie.

Le serveur diffuse l effet, l age, le modele de fragment et un identifiant de generation. Les nouveaux observateurs recuperent l age reel ; ils ne rejouent pas une explosion ancienne. Les morceaux expirent a 12 secondes et le cadavre a 15 secondes. Limites : 12 cadavres, 72 entites de fragments, 384 particules elementaires simultanees et 12 emissions par image.

Les mouvements sont transferes sur les 28 os GIGN ; les longueurs des membres sont conservees. Les poses sont ajustees au maillage decoupe reel pour eviter les contacts sous le sol et garder le torse au sol en fin de chute. Les 77 sequences historiques et les indices des trois imports precedents sont conserves. Les quatre attaches du modele restent inchangees.

Ces gestuelles representent les effets par interpretation artistique ; les banques ne proposent pas toutes une mort acide ou electrique nommee comme telle. Les seuils de degats par zone restent a definir, comme convenu. Les commandes de test restent `vf_range_death <0..3> <zone> <effet> [mouvement]` et `vf_death_test <zone> <effet> [mouvement]`.

## Validation

Les rapports et captures natifs sont dans `docs/validation/death-atlas/`. Les suites verifient les 16 associations automatiques, les cinq zones anatomiques, les trajectoires et particules, le choix par F8, la sauvegarde du cadavre, les budgets et la synchronisation reseau.
