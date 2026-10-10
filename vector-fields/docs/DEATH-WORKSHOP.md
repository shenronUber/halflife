# Aperçu 3D des morts hors jeu

Ouvrir **Atelier - Animations.cmd**, puis l’onglet **Morts et effets**.
L’aperçu fonctionne dans le navigateur, sans serveur, connexion internet ou partie lancée.

- **Personnage / voix** : Rocco, Lucien, Diego, Viktor, Otto ou Nikos.
- **État à la mort** : balle, huit éléments, huit mélanges ou cinq états tactiques.
- **Animation** : choix automatique selon l’atlas du jeu, ou l’un des 18 mouvements compilés. Une tête détachée sélectionne automatiquement le mouvement de tir à la tête pour une mort standard.
- **Autre variante** : alterne les mouvements disponibles pour cet état en mode automatique.
- **Membre détaché** : corps entier, tête, bras gauche ou droit, jambe gauche ou droite, ou tous les membres. Les groupes du corps et les surfaces de coupe reprennent le modèle compilé du jeu. Chaque membre émet ses quatre morceaux anatomiques, soit vingt morceaux quand tous les membres sont détachés.
- **Nouvelle projection** : change les trajectoires aléatoires des morceaux, du sang et des particules. Une même projection reste identique quand on revient en arrière avec le curseur.
- **Gants / tenue** : les 14 apparences ; la voix reste indépendante de la tenue.
- **Lire / Rejouer la mort** : animation, cri, son élémentaire et son d’arrachement démarrent ensemble. La mort ne boucle pas ; la pose finale reste affichée.
- **Pause, −1, +1, curseur et vitesse** : arrêt, examen image par image, déplacement dans la lecture ou ralenti.
- **Cri synchronisé / Son de l’élément / Son d’arrachement** : désactiver séparément les trois pistes et régler leurs volumes. Les valeurs initiales reprennent celles du jeu : 0,85 / 0,8 / 0,8.
- **Effet visible / Sang projeté / Traces au sol** : examiner séparément la signature élémentaire, les gouttes et les decals.
- **Suivre la chute** : garde le personnage au centre. Désactiver pour un cadrage fixe ; Maj + glisser libère aussi la caméra.
- Les lecteurs **Écouter le cri seul** et **Écouter les bruitages seuls** permettent de comparer les sons sans rejouer le mouvement.

Les 102 cris sont les WAV utilisés par le jeu : PCM mono, 11 025 Hz, 8 bits,
au maximum trois secondes. Les 33 bruitages supplémentaires sont également intégrés sans
transformation : 16 sons de mort élémentaire et 17 sons d’arrachement, PCM mono, 22 050 Hz,
16 bits. Le jeu les joue sur trois canaux distincts ; l’atelier conserve leur superposition.
L’arrachement émet une seule salve par mort, même avec plusieurs membres. Son pitch vaut
112 % pour la tête, 92 % pour une jambe seule et 100 % dans les autres cas.
Les états tactiques reprennent le cri standard et le son d’arrachement générique ;
ils ne déclenchent ni son ni signature de mort élémentaire.

Le sang utilise le sprite natif `sprites/blood.spr`, teinté rouge sombre et dessiné avec
transparence. Un gros morceau émet une gerbe de dix gouttes, puis des traînées indépendantes
de sa position courante. Les émissions continuent au maximum 2,2 secondes, avec un intervalle
minimal de 0,06 seconde, douze émetteurs par image et un pool partagé de 384 particules.
Les particules élémentaires gardent leurs propres couches et leur mélange additif.
Les six decals `{blood1` à `{blood6` viennent de `decals.wad` : la palette de gradient
fournit la couleur rouge et l’opacité. Ils apparaissent aux contacts des morceaux avec le sol,
avec un budget de cinq impacts et une trace supplémentaire à l’arrêt. Les morceaux restent
visibles douze secondes. Le curseur peut donc continuer après la fin du cri et de l’animation.

Les poses, surfaces de coupe et morceaux viennent de `generated/deaths/persona_death.mdl`
et `persona_death_gibs.mdl`. Le choix automatique et les centres d’effets viennent de
`assets/animations/death-atlas.json`. Les règles des émissions sont reprises de
`cl_dll/vf_death.cpp`, `cl_dll/vf_effects.cpp` et `dlls/vf_death.cpp`. Les trajectoires
élémentaires reprennent `cl_dll/vf_effect_math.h`, avec les sprites compilés du jeu et
le sprite natif d’éclair `sprites/lgtning.spr`.

L’atelier simule les rebonds sur un **sol plat** avec les valeurs de gravité et de friction
usuelles du jeu. Les collisions d’une carte, les réglages physiques du serveur et la
spatialisation sonore doivent être vérifiés dans le jeu. L’aperçu ne modifie pas le moteur.

Le lanceur réutilise la page quand ses sources n’ont pas changé. Un changement d’interface
actualise seulement le HTML ; des modèles ou sons modifiés régénèrent les données.
Les sources natives des émissions, la banque de bruitages, les sprites et les decals
participent aussi à cette vérification. Déposer une recette sur le lanceur conserve
la recompilation des essais R-01.

Liens directs sur la page HTML :
`?section=deaths&actor=otto&cause=hydro&motion=kaykit_b&region=left_arm`.
Les paramètres `actor`, `cause`, `motion` et `region` sont facultatifs.
Valeurs de `region` : `none`, `head`, `left_arm`, `right_arm`, `left_leg`, `right_leg`, `all`.

Validation : `tests/death_workshop_test.cjs` vérifie les 102 cris, les 16 associations,
les 18 mouvements, les états tactiques, la synchronisation et l’arrêt final.
`tests/death_emissions_workshop_test.cjs` vérifie les 33 WAV supplémentaires à l’octet près,
les sept choix de démembrement, les vingt maillages, le sang rouge, les decals, la limite de
384 particules, le retour en arrière et la lecture simultanée des trois pistes.
`tests/animation_workshop_test.cjs` vérifie les huit autres scènes de l’atelier.
Les rapports et captures sont dans `build/animation-workshop/deaths/`, avec les nouvelles
émissions dans le sous-dossier `emissions/`.
