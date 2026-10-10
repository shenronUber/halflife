# Poignée avant et animations R-01 — 2026-10-09

La poignée inclinée (`r01_underbarrel_a`) sélectionne une prise dédiée à la
première personne, quelle que soit sa finition. Les trois alimentations sont
prises en charge. Le tube auxiliaire, le stabilisateur replié et le garde-main
conservent l’appui standard. Les animations de déplacement et les prises de
troisième personne restent celles retenues précédemment.

La main gauche tient la poignée pendant le maintien, le tir et la sortie de
l’arme. Pendant la recharge, elle rejoint le chargeur puis revient sur la
poignée. Les doigts ont une fermeture propre au diamètre de cette poignée.
La recette est `assets/animations/r01-first-person-foregrip.json` ; le générateur
est `build_foregrip.py`. Les réglages portent sur le bras gauche et ses doigts.
Les pistes de l’arme, du chargeur, de la culasse et du bras droit sont conservées.
L’avant-bras de la recharge supérieure utilise une rotation sans retournement ;
la position et l’orientation de sa paume sur le chargeur restent identiques.

Les six porteurs conservent les neuf séquences MP5 et leurs événements sonores.
Le geste de recharge est accéléré de 2,78 s à 1,5 s pour terminer avant que le
serveur rende l’arme disponible. Le délai gameplay reste inchangé.

Dans **Atelier - Animations.cmd**, choisir une vue première personne puis
**Appui avant**. Le maintien, le tir et la recharge utilisent les mêmes poses
compilées que le jeu. Quatre chargeurs et quatorze finitions restent disponibles.
La case de posture expérimentale a été retirée du parcours courant.

Vérifications :

- `tests/foregrip_assets_test.py` : 1 110 poses compilées, contact sur la poignée,
  contrôle des sommets du gant autour de son cylindre, raccords avec la prise du
  chargeur, conservation des pistes et des longueurs de bras, durée de 1,5 s.
- `tests/animation_workshop_test.cjs --media` : huit scènes WebGL, quatre appuis
  avant, chargeurs, recharges, déplacements natifs et éditeur des bras.
- `tests/foregrip_native_test.py` : une session courte, trois alimentations,
  tir/recharge/retour, remplacement de la poignée et changement de finition.
  `--verify` permet de relire ses traces sans relancer le jeu.
- Contrôles existants des mains, de l’index sur les chargeurs et des prises en
  troisième personne conservés. Aucun changement de locomotion ajouté.

Rapports sous `build/foregrip/`, images de l’atelier sous
`build/animation-workshop/`. Les contrôles géométriques complètent la lecture
visuelle ; ils ne constituent pas un solveur de collision de tous les triangles.
