# Feedback des états en première personne — 0.20.6

## Essayer

Lancer **Jouer - Vector Fields.cmd**, puis **F3 > Test joueur / voix**.
Activer le test développeur, choisir un vecteur, une réaction ou un état,
puis **Sur moi**. Les réactions disposent aussi du bouton **Combiner**.
**Retirer mes effets** efface les couches visuelles. Les triggers de dégâts
existants utilisent le même état serveur.

## Decals originaux

Huit éléments et huit réactions disposent chacun de quatre images originales
sur fond transparent. Une réaction possède son propre décor, avec les deux
matières intégrées : eau chargée d’électricité, glace parcourue d’arcs,
acide et spores, flammes toxiques ou vapeur et condensation.

Les marges et la profondeur réelle des matières sont mesurées sur les quatre
images ensemble. Chaque bordure est ensuite ajustée à la même enveloppe :
coins ancrés au bord de l’écran, profondeur de 14 %, disparition progressive
à partir de 9 %. Les frames gardent ce placement commun pour éviter les sauts
pendant l’animation. Les quatre bandes se partagent les coins sans superposition.

Les sprites RGBA natifs du moteur Xash conservent exactement les couleurs et
la transparence des PNG compilés. L’opacité commune est de 72 %, sans éclairage
additif qui blanchirait différemment l’eau, la glace ou les réactions. Deux
images voisines sont fondues en continu ; les vitesses adaptées aux matières
vont de 2,4 à 5,6 images sources par seconde. Il n’y a aucun traitement particulier
des emplacements actuels du HUD. Le centre reste entièrement dégagé.

Sources, prompts imagegen et planche de comparaison :
`assets/status-feedback/decals/`. Les sources originales restent disponibles ;
les PNG ajustés se trouvent dans `frames/`, les seize sprites dans
`generated/status-decals/`. Le build et le lancement sont hors ligne.
`build_status_decals.py --ensure` vérifie les empreintes des entrées et sorties.
Les cinq états tactiques conservent leurs signatures géométriques existantes.

## Règles de lecture et cycle de vie

- Nom anglais, icône, compteur en secondes et barre de durée réelle.
- Jusqu’à quatre états affichés : priorité aux réactions, puis aux derniers
  états reçus. Les bordures se répartissent entre les quatre côtés. Un compteur
  indique les états supplémentaires, qui restent actifs côté serveur.
- Les réactions consomment leurs parents ; le badge montre le résultat et sa recette.
- Centre protégé : x 16–84 %, y 16–80 %.
- Apparition de 0,16 s et atténuation sur les dernières 0,35 s ; aucune secousse
  de caméra ni clignotement intégral de l’écran.
- Le halo suit les vrais gants et manches R1, la prise et la recharge.
- Les bordures montrent uniquement l’état du joueur local vivant, jamais celui
  d’un adversaire ou d’un spectateur.

Les couches suivent VFStatus et sa durée autoritative. Rafraîchir un état ne
redémarre pas l’animation ; retrait, expiration, mort, changement de carte et
révocation du mode de test enlèvent le feedback. Les voix existantes, les dégâts
et les propriétés d’équilibrage des effets sont conservés.

## Vérification

```powershell
python vector-fields/tests/status_decals_assets_test.py
python vector-fields/tests/status_feedback_test.py --mode all
python vector-fields/validate.py --suite unit
```

Le test des ressources vérifie les seize sprites RGBA, les 64 frames distinctes,
les quatre côtés, la transparence centrale et l’identité des couleurs/alphas avec
les PNG. Le test natif applique les 21 états, une paire atomique, quatre états
simultanés, une brûlure réelle, une recharge et les différents retraits. Les
pixels de la bordure animée et du centre sont comparés sur fonds clair et sombre.
Deux clients vérifient l’indépendance des états locaux et distants. Les suites
utilisent les DLL de la version actuelle dans des runtimes isolés.

Diagnostic : `vf_status_decal_audit`, `vf_status_visual_stats`.
Isolation des couches : `vf_status_visual_layers 1 0` (écran), `0 1` (bras),
`1 1` (les deux). Ces options ne retirent aucun état serveur.
