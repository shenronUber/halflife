# Donneurs de mouvements de mort

Exports originaux Quaternius et KayKit, récupérés le 10 octobre 2026.
Les URLs des auteurs, miroirs, objets Git et empreintes SHA-256 sont dans
[sources.json](sources.json). Ces exports sont conservés sans modification.

- Quaternius Universal Animation Library Standard : fichier de 46 clips ;
  `Death01` et `A_TPose` sont utilisés par le transfert.
- KayKit Character Animations 1.1, Rig Medium General : fichier de 15 clips ;
  `Death_A`, `Death_B` et `T-Pose` sont utilisés par le transfert.

`../../../external_death_animations.py` transfère les rotations sur les os
GIGN, conserve leurs longueurs et ajuste le contact au sol. `build_deaths.py`
compile les trois séquences après l’animation électrique. Aucun modèle ou
matériau donneur n’entre dans le jeu. Les pistes restantes peuvent être
évaluées séparément pour d’autres mouvements.

Auteurs : [Quaternius](https://quaternius.itch.io/universal-animation-library),
[Kay Lousberg](https://kaylousberg.itch.io/kaykit-character-animations).
