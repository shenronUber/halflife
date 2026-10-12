# Inspection de l’arme

**I** présente l’arme assemblée : premier côté, courte pause, second côté,
puis retour à la prise normale. Le geste dure 4,5 secondes et les appuis sur I
pendant le mouvement ne le relancent pas.
Le départ rejoint directement le premier côté en 0,8 seconde, sans arrêt
dans une position intermédiaire. Les pauses sur les deux côtés restent lisibles.

Le tir, la recharge, le rangement de l’arme, l’ouverture du menu, un geste de
casque ou un franchissement reprennent la priorité. L’inspection concerne le
R1 en première personne ; elle ne change ni la caméra, ni les munitions,
ni l’équipement. La commande console est `vf_inspect`.

Six porteurs dédiés dans `models/vf_inspect` présentent l’arme et ses pièces.
La main gauche ouvre ses doigts et lâche complètement l’arme, puis reprend
sa prise à la fin. La main droite conserve la poignée.
Le détour de la main suit la normale de sa paume pour chaque prise ; avec une
poignée avant, la main se dégage d’abord vers l’avant du col du chargeur.
Le bord du gant et le bout de la manche gauche suivent le poignet pour éviter
les étirements lors du lâcher et de la reprise.
L’arme est relevée vers le plafond et avancée pendant les deux présentations,
pour écarter la
crosse du corps pendant la rotation. Les coudes restent reliés aux épaules par
une résolution à deux segments, sans allonger les bras. Une main droite
complète et une manche droite sont dérivées de la géométrie MP40 existante,
uniquement pendant l’inspection. Elles conservent les indices de textures du
personnage équipé. Les chargeurs, sockets et finitions restent associés à
leur assemblage. Les banques d’animation et les modèles FPS existants sont
préservés. Le code est isolé dans
`cl_dll/vf_weapon_inspect.inc` et `game_shared/vf_weapon_inspect.h`.

Compilation privée : `python vector-fields/build_weapon_inspect.py`.
Validation en moteur temporaire :
`python vector-fields/tests/weapon_inspect_native_test.py`.
Cette validation filme les six configurations (chargeur inférieur, latéral ou
supérieur, avec ou sans poignée avant) avec le chargeur le plus volumineux.
Elle contrôle aussi les quatre formes de chargeur sur chaque trajectoire,
via `weapon_inspect_clearance_test.py`, en autorisant le contact de prise
initial. Les films et les planches de contrôle sont conservés dans le dossier
de validation. La publication exige ces six essais et des modèles identiques
à ceux du contrôle de dégagement.
Le dossier `build/weapon-inspect` conserve les captures et les rapports ;
le runtime natif est supprimé à la fermeture. La publication vérifie que les
sources compilées et les DLL utilisées par les essais sont encore actuelles.
Elle ajoute seulement les huit modèles d’inspection et le client compilé.
Elle ne publie ni serveur, ni moteur de rendu, ni modèles de personnages.

Pour une correction limitée aux modèles, `publish_weapon_inspect.py --models-only`
conserve aussi les deux DLL client et les contrôles. Ce mode exige que le client
installé soit exactement celui des essais natifs, et revérifie les modèles et
leurs sources avant installation. Les autres sources client peuvent évoluer
pendant ce temps : elles ne sont ni compilées ni publiées par cette opération.

`Inspecter l'arme - Vector Fields.cmd` ouvre une session temporaire avec les
ressources installées et la touche I. F11 permet de changer l’assemblage.
