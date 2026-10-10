# Impacts, zones du corps et matériaux

Cette étape identifie les impacts côté serveur. Elle conserve les dégâts, les coefficients `gSkillData` et l'absorption d'armure Half-Life. Aucun matériau ne réduit ou n'augmente les dégâts.

## Animation et collision

Les modèles serveur `persona_rig.mdl` et `r01_tp{,_side,_top}.mdl` possèdent maintenant 20 volumes anatomiques, attachés aux os, répartis en sept groupes : tête, torse, abdomen, bras gauche/droit et jambe gauche/droite. Le volume de bouclier du donneur Counter-Strike (groupe 8, main gauche), sans géométrie de bouclier affichée, a été retiré. Les autres volumes, la géométrie, les textures et tous les canaux d'animation sont identiques aux modèles précédents.

Dans Xash3D, `SV_HullForStudioModel` transmet la séquence, la frame et les paramètres de pose à `Mod_HullForStudio`. Les plans de chaque boîte sont construits à partir de la matrice de son os. Une animation **du modèle serveur** déplace donc les volumes de dégâts. Modifier uniquement un viewmodel à la première personne ou une pose dans l'atelier HTML ne déplace pas ces volumes.

La boîte de déplacement du joueur reste distincte : debout, `mins=-16,-16,-36` et `maxs=16,16,36`. Elle n'a pas été modifiée. La configuration testée utilise `sv_clienttrace=1` ; une valeur de zéro désactive les hitboxes individuelles pour les traces joueur. La valeur positive ajoute la tolérance de trace historique du moteur.

**Limite de correspondance visuelle :** le moteur serveur conserve son calcul de pose historique. Le renderer applique en plus la démarche et une correction de rotation du torse (`R_VFPlayerTorsoYaw`). Ces corrections ne sont pas entièrement reproduites dans la collision serveur. Les nouvelles poses de bras et le rechargement sont bien dans le modèle serveur ; une égalité précise avec le corps affiché pendant tous les déplacements nécessite encore de partager le calcul complet de pose entre serveur et renderer. `GET_BONE_POSITION` sert au diagnostic ; les traces réelles restent l'autorité pour les dégâts, avec leurs propres paramètres de mélange.

## Dégâts conservés

Le branchement se trouve dans `CBasePlayer::TraceAttack`. La nouvelle fonction retourne exactement `dégât brut × coefficient du groupe`, puis les appels historiques à `SpawnBlood`, `TraceBleed`, `AddMultiDamage` et `TakeDamage` continuent normalement.

Dans la configuration native chargée lors du test : tête **×3**, torse/abdomen/bras/jambes **×1**. Ces valeurs restent celles des cvars de difficulté ; elles ne sont pas figées dans le nouveau catalogue. Les groupes générique et inconnu conservent ×1.

L'armure Half-Life reste dans `TakeDamage`, après le regroupement des impacts. Pour une balle et suffisamment d'armure, le joueur reçoit 20 % du dégât et consomme 0,5 point d'armure par point absorbé. Le traitement des explosions et l'arrondi des dégâts de santé restent également ceux du SDK.

## Catalogue physique

Source : `vector-fields/data/combat-materials.json`. Générateur : `build_materials.py`. Le build régénère `game_shared/vf_material_catalog.h` avant de compiler la DLL serveur. Le catalogue est embarqué dans cette DLL ; éditer le JSON demande une reconstruction. Son SHA-256 est affiché par `vf_materials_info` pour identifier la version réellement chargée.

Les 14 entrées couvrent notamment chair, textile, cuir, caoutchouc, acier, verre, béton, bois, sol, céramique, eau, composite, neige et matériau inconnu. Chaque entrée possède une famille, une densité en kg/m³, une résistance balistique en J/mm et un indicateur de calibration. Les profils d'équipement permettent jusqu'à quatre couches, chacune avec son épaisseur en mm ; le tissu biologique est ajouté après les couches extérieures.

**Les densités renseignées sont des paramètres provisoires de jeu.** Elles ne constituent pas une mesure des objets affichés. Toutes les résistances et épaisseurs sont encore `null`, et toutes les entrées restent non calibrées. `null` devient `-1` dans la structure compilée et le diagnostic, afin de distinguer « inconnu » de zéro. Une épaisseur réelle, une composition et des essais devront être fournis avant tout calcul de protection.

`slot_profiles` utilise les noms réels des 21 emplacements d'équipement, avec un ordre généré depuis `vf::SlotKeys`. `item_overrides` pourra associer un objet précis ou sa géométrie à un profil différent. L'identité exacte de l'objet a priorité sur son profil de géométrie. Une finition ou un effet visuel n'infère aucune propriété physique.

L'identification actuelle de la tenue est **une approximation par groupe anatomique** : tête → équipement de tête ; torse/abdomen/bras → vêtement du torse ; jambes → pantalon. Les profils de gants et de chaussures sont préparés et consultables, mais les groupes bras/jambes ne permettent pas encore de décider si une balle a touché précisément une main, une chaussure ou une plaque. Aucun bouclier invisible n'est ajouté comme couche. Une précision future exige un indice de hitbox/os et une couverture spatiale des pièces, éventuellement avec plusieurs intersections ordonnées.

Les surfaces du décor utilisent le classement historique des textures Half-Life. Les objets `func_breakable`/`func_pushable` utilisent leur matériau déclaré, et les entités biologiques ou mécaniques leur classification serveur. Ce classement reste grossier et ne mesure ni l'épaisseur du mur ni sa composition réelle.

## Contexte de chaque impact

`VF_ProjectileTraceScope` encadre chaque impact réel de `FireBullets` et `FireBulletsPlayer`. Le contexte est restauré à la fin du bloc, afin qu'un coup de mêlée ultérieur ou une arrivée asynchrone ne récupère pas les pièces de l'arme active précédente.

L'enregistrement retient l'attaquant, la victime, le point, la normale, la direction, le groupe anatomique, les bits de dégâts, le type natif de projectile, le dégât brut, son coefficient et son résultat avant armure. Pour un tir MP5 instantané, il retient aussi l'identité des objets de munition et de projectile équipés. La distance est en unités du moteur. Les masses (kg) et vitesses (m/s) sont préparées mais inconnues, donc aucune énergie fictive n'est calculée.

La nature physique vient du type de projectile réel ou des bits de dégâts : cinétique, contondant, thermique, explosif, chimique ou électrique. Les effets visuels ne la changent pas. Un effet laser sur le MP5 ne transforme donc pas automatiquement ses dégâts en dégâts thermiques.

Le contexte porte aussi un élément de statut pour le prototype de déclenchement : six impacts du même élément en trois secondes activent six secondes d'état primaire. Le profil R1 de test fournit cette valeur distincte ; il ne modifie ni la nature physique enregistrée, ni les dégâts, ni les propriétés des matériaux. Voir [TEST-ROOM.md](TEST-ROOM.md).

Les attaques directes à `TraceAttack` sans contexte de tir sont identifiées à partir de leurs bits de dégâts, avec type/arme/objets de projectile inconnus. Les dégâts directs sans trace (`TakeDamage`, notamment certains effets de zone ou dégâts périodiques) n'ont pas encore de contact localisé dans ce système. Pour les projectiles à temps de vol, un futur contexte devra être transporté par l'entité du projectile depuis son lancement.

## Diagnostic et validation

Commandes console transmises au serveur :

```text
cmd vf_materials_info
cmd vf_hitbox_info
cmd vf_impact_info
cmd vf_impact_info incoming
vf_impact_debug 1
```

Le diagnostic des impacts est désactivé par défaut. `vf_hitbox_probe` effectue une trace de diagnostic sur la main gauche et demande un accès développeur. `vf_combat_selftest` demande en plus `sv_cheats 1` et un joueur vivant ; il teste les sept groupes et l'armure, puis restaure santé, armure, mouvement et états de dégâts. Il peut émettre du sang et des sons pendant cette vérification et sert aux sessions isolées.

Validation : `tests/combat_policy_test.cpp`, `tests/combat_native_test.py`, `tests/operator_rig_test.py` et `tests/third_person_assets_test.py`. Rapports dans `build/combat/` :

- `native-verification.json` : sept vrais groupes tracés, dégâts et armure conservés, absence de fuite du contexte, équipement/munition identifiés, matériau béton identifié, traces et centres de hitbox déplacés pendant un vrai rechargement sans déplacement du bassin.
- `model-verification.json` : suppression exclusive du groupe 8 dans les quatre modèles ; aucune modification des autres hitboxes, textures, maillages ou canaux d'animation.
- `deployment.json` : empreintes des fichiers vérifiés puis installés.

Le futur calcul pourra utiliser `membre + couches traversées + projectile`. Ce socle prépare ces données ; il n'implémente pas encore la pénétration, l'énergie résiduelle, la couverture précise des armures ou une simulation exacte des tissus.


## Charte des huit éléments et huit matières

La [proposition v0.3](../design/element-material-balance.json) fixe huit matières : chair, textile, cuir, bois, élastomère, métal, céramique et minéral. Les cinq niveaux de dégâts reçus sont résistance forte ×0,50, résistance légère ×0,75, normal ×1, faiblesse légère ×1,25 et faiblesse forte ×1,50. Chaque matière et chaque élément possèdent une réponse à chacun des quatre niveaux non neutres et quatre normales. Toutes les moyennes de lignes et colonnes valent exactement ×1 à répartition uniforme.

La [balance sheet v0.3](../../outputs/01a1204a-28b0-7251-8917-08dde45856c6/Charte-elements-matieres-v0.3.xlsx) reprend les huit vecteurs et huit couplages nommés des fichiers existants. Les couplages additionnent les intensités signées (-2, -1, 0, +1, +2), avec une borne de -2 à +2 : coefficient = 1 + 0,25 × score. Exemple : Electro ×1,50 et Hydro ×0,75 sur Métal donnent ArcChain ×1,25. Deux intensités opposées égales donnent normal. Un élément répété reste simple. Les vingt autres paires ne constituent pas des types couplés autorisés par cette proposition.

Les huit couplages nommés ont eux aussi une moyenne exacte ×1 sur les huit matières ; chaque matière garde une moyenne ×1 face à ces huit couplages. Aucun bonus de dégâts ne s’ajoute au budget. Conditions et effets tactiques restent à tester. Les poids cibles mesurent une distribution réelle inégale ; ils ne la normalisent pas artificiellement. La v0.3 remplace la v0.2 et conserve les quatre intensités dans l’interface joueur.

Les quatorze identifiants du catalogue physique restent conservés pour identifier surfaces et couches existantes. physical_catalog_mapping les raccorde aux huit matières. Eau, neige et sol restent des milieux du décor ; un composite est décomposé en couches. Le classement de verre ou béton dans Minéral n’autorise pas l’héritage automatique d’un profil de pierre. Matière, construction, couverture et intégrité restent distinctes.

Normal signifie absence de modificateur dans la charte, pas absence d’autres propriétés physiques. Toxic vise l’exposition du vivant et Corrosion l’usure de la protection. Les profils et justifications du classeur précisent les hypothèses : textile absorbant, bois sec, céramique microporeuse et minéral siliceux. Ni les sprites ni une finition artistique ne définissent les dégâts. Les coefficients restent des conventions de gameplay, sans calibration physique ; ils ne garantissent pas la même utilité tactique, portée, cadence ou disponibilité.

Cette charte n’est pas chargée par build_materials.py et ne modifie pas LegacyTraceDamage. Épaisseurs et résistance J/mm inconnues restent indéfinies. Le futur raccordement devra éviter le cumul automatique avec l’absorption Half-Life historique ou un coefficient de Chair supplémentaire après une protection déjà résolue. Les modifications manuelles du classeur doivent être reportées dans le JSON avant implémentation ; aucune synchronisation automatique n’est active.
