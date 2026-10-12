# Frappe au canon du Relais R1

`V` / `vf_melee` déclenche une frappe descendante de 1,1 seconde. La main gauche
lâche son appui et reste ouverte en bas du cadre. La droite conserve sa prise,
relève l'avant du canon, frappe vers le bas et accompagne la descente, puis les
mains retrouvent leur pose normale. Le canon mène le contact ; la crosse reste
derrière la main. Le serveur applique au plus un contact, à
13/30 seconde : portée 40 unités, dégâts de base 35 (`DMG_CLUB`), sans munition.
Les multiplicateurs de zone et les protections du jeu restent applicables.

La première personne couvre les chargeurs inférieur, latéral et supérieur,
avec ou sans poignée avant. La troisième personne propose les poses debout et
accroupies et transmet le même geste aux autres joueurs. Cette première
intégration cible le R1 et les opérateurs ajustés au squelette `persona_rig`.
Les anciens modèles donneurs et les autres armes ne déclenchent pas ce geste.

Le rechargement, le casque, les menus et la traversée gardent leur priorité.
Le coup remplace une inspection. Le changement d'arme, la mort ou le chargement
d'une sauvegarde interrompent le coup ; il ne peut pas redémarrer à chaque
répétition de touche. Les attaques sont verrouillées pour sa durée.

## Source Blender

`vector-fields/melee-workshop/Frappe-au-canon-R1.blend` contient deux scènes,
douze actions de squelette, et huit poses de contrôle explicites par montage.
Les contrôles `Gestuelle / …` conservent les poses conçues pour la position,
la rotation, le dégagement de la main gauche et la rotation du torse. Les
actions de squelette sont ensuite cuites et éditables dans l'Action Editor ;
les contrôles servent à la génération et ne pilotent pas les poses cuites en direct.
Les repères de timeline
identifient lâcher, armement, impact, suivi et reprise. Les géométries et
textures réellement installées sont embarquées pour la revue.

Le geste suit la référence de six poses fournie le 12 octobre. En vue
subjective, l'arc est légèrement oblique pour dégager le centre du cadre et
garder la main gauche visible. Accroupi, l'inclinaison de la pose de repos est
compensée pendant le coup : le canon monte réellement avant de redescendre,
puis la pose de départ est retrouvée sans modifier les animations ordinaires.
Le précédent fichier `Coup-de-crosse-R1.blend` reste disponible comme archive.

`author_melee.py` crée ces poses manuellement, résout les bras sans changer leur
longueur, puis exporte les matrices évaluées dans Blender. Le compilateur ajoute
une séquence première personne et deux séquences troisième personne à des
copies des porteurs. Chaque ancienne séquence, chaque blend et les événements
existants sont conservés et vérifiés. Les modèles d'origine restent inchangés.
Le jeu utilise uniquement le dossier dédié `models/vf_melee` pendant le coup.

## Construction et validation

```
python vector-fields/build_weapon_melee_assets.py
python vector-fields/build_weapon_melee.py
python vector-fields/tests/weapon_melee_geometry_test.py
python vector-fields/tests/weapon_melee_native_test.py
python vector-fields/tests/weapon_melee_network_test.py
python vector-fields/publish_weapon_melee.py
```

Le build habituel utilise `--source-generated --ensure` après les porteurs
troisième personne. Il réutilise les assets quand leurs entrées sont identiques.
La release inclut les onze fichiers dédiés et la touche V. Les essais utilisent
`native_workspace` et des moteurs temporaires, avec des ports de boucle locale.
Le lanceur `play_weapon_melee.py` ouvre aussi une session temporaire de la
version installée.

Les preuves et captures sont dans `vector-fields/build/weapon-melee` :
`geometry.json`, `native.json`, `network.json`, `installed.json`, et les GIF.
La publication refuse un changement de sources, de modèles, du renderer ou une
publication concurrente des DLL depuis la revue. Elle ne déploie aucun moteur
et ne remplace aucun modèle de skins ou aucune banque d'animations existante.

La révision de frappe au canon est vérifiée contre les DLL et le moteur
actuellement installés, dans `vector-fields/build/barrel-strike`. Pour la
reproduire sur cette compilation réunie :

```
python vector-fields/build_weapon_melee_assets.py
python vector-fields/prepare_barrel_strike.py
python vector-fields/tests/weapon_melee_geometry_test.py --output vector-fields/build/barrel-strike
python vector-fields/tests/integration_native_test.py melee --bundle vector-fields/build/barrel-strike/candidate --output vector-fields/build/barrel-strike/native
python vector-fields/tests/integration_native_test.py melee_network --bundle vector-fields/build/barrel-strike/candidate --output vector-fields/build/barrel-strike/native
python vector-fields/tests/integration_native_test.py pose_strike --bundle vector-fields/build/barrel-strike/candidate --output vector-fields/build/barrel-strike/native
python vector-fields/tests/integration_native_test.py melee_integration --bundle vector-fields/build/barrel-strike/candidate --output vector-fields/build/barrel-strike/native
python vector-fields/tests/integration_native_test.py gesture_status --bundle vector-fields/build/barrel-strike/candidate --output vector-fields/build/barrel-strike/native
python vector-fields/install_barrel_strike.py
```

Les contrôles supplémentaires mesurent le canon en montée, en contact et en
suivi, ainsi que les vingt hitboxes sur les trois montages debout et accroupi.
La publication vérifie les empreintes des fichiers testés, sauvegarde les
porteurs remplacés et conserve les DLL intégrées. Le rapport est dans
`docs/validation/barrel-strike-2026-10-12.json`.
