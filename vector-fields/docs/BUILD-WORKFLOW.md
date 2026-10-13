# Construction et intégration

Le profil principal est `vf_visual`. Il contient `vf_range` (combat et parcours), `vf_modular` (grille aléatoire), `vf_tiles` ([huit intérieurs jouables](TILE-LABORATORY.md)), et les cartes historiques de régression. F4 ouvre leur menu commun. `game_profiles.py` est le registre des cartes locales, du catalogue et des raccourcis. Une nouvelle carte exige sa recette, son enregistrement, un test natif de chargement/collision.

## Construire et publier

`python vector-fields/build_release.py` ou `vector-fields/build.ps1` prépare un candidat lorsque les sources ou le build installé ont changé. `--force` impose un nouveau candidat. Les deux DLL sont compilées dans un cache privé, puis copiées avec leurs sources dans un dossier immuable `build/releases/<id>`. Le jeu complet y est préparé, sans écrire dans le mod principal.

La publication exige les suites `unit`, `policy`, `assets` et `integration`. La dernière couvre mêlée, réseau, poses/hitboxes, wall run et regard libre, back jump, rechargement, dégâts, les cibles de tir, le parcours combiné, la grille modulaire et les sauvegardes. Les anciennes suites natives et multijoueurs restent accessibles pour élargir les contrôles.

Les empreintes des sources et du paquet sont revérifiées après les tests. Le même verrou protège construction, publication et démarrage. Le mod complet est remplacé par renommage ; les DLL canoniques et ressources moteur sont sauvegardées et restaurées en cas d'échec. L'ancien mod reste conservé sous `.vf_visual-before-*`. Les sauvegardes et préférences locales survivent. Fermer le jeu avant une publication qui remplace ses DLL.

Les résultats sont liés aux empreintes du paquet dans `vf/release-bundle.json`. Ne pas publier en copiant une DLL à la main, ni réutiliser une preuve provenant d'un ancien candidat.

L'empreinte des entrées inclut le protocole `network/delta.lst`, les patches moteur, les ressources et bibliothèques de compilation. Le contrôle du build installé compare aussi l'identité du moteur. Un fichier source retiré est également retiré du cache de compilation.

La rétention garde le candidat installé, un précédent candidat validé et un ancien mod pour retour arrière. Les autres candidats, y compris les compilations échouées, sont retirés sous le verrou de publication, après copie des rapports, sauvegardes et d'un échantillon de captures dans `build/retention`. Les ateliers, sources Blender et textures ne font pas partie des chemins nettoyés. `python vector-fields/release_retention.py` affiche le plan ; `--apply` l'applique et compacte les preuves de sessions retirées à 32 captures par cas. Les rapports et sauvegardes restent complets. Les séquences complètes publiées par les tests dans leurs dossiers de résultats restent disponibles. Les futures sessions retirées suivent cette même limite, sans recopier tous les fichiers avant de les réduire.

## Travailler en parallèle

Commencer depuis le checkpoint Git qui contient les sources actuelles. Créer une branche `codex/<fonctionnalite>` et un worktree par fonctionnalité. Le worktree a son propre `build`, son runtime et ses sessions de test ; aucun agent ne doit compiler ou publier dans le dossier d'un autre.

Git transporte le code, les données et les sources d'animation. Les compilateurs, donneurs installés et sorties générées sont des dépendances locales ignorées. Depuis le nouveau worktree :

```powershell
python devtools/bootstrap-worktree.py --seed "G:\Half life Project"
python vector-fields/build_release.py
```

La préparation copie le build validé et les dépendances nécessaires. Les médias sont liés à un cache indépendant identifié par contenu ; les fichiers modifiables restent privés. Les sauvegardes du joueur, anciennes expériences et sessions de validation ne sont pas copiées. Half-Life installé et Visual Studio C++ doivent être disponibles sur la machine.

Fusionner ou cherry-picker les commits de code, données et recettes, puis reconstruire et valider le résultat intégré. Les DLL, BSP et caches locaux ne servent pas de mécanisme de fusion. Une source modifiée pendant la compilation ou les tests fait refuser la publication.


## Modifier le moteur

Le cache serveur de poses contient au plus 32 joueurs et compare les entrées exactes : temps, modèle, entité, orientation, animation, transitions, posture, points d'appui et geste du casque. Il est vidé avec les caches Studio au changement de carte. `vf_sv_pose_cache 0` permet une comparaison directe, `vf_sv_pose_info` donne les compteurs et `vf_sv_pose_bench 2048` mesure les requêtes répétées sur les joueurs présents avec `sv_cheats 1`. Cette mesure isole l'évaluation des poses ; elle ne remplace pas une mesure de FPS ni un test de charge réseau.

`vector-fields/build-engine.ps1` compile les extensions et leurs tests dans `build/engine-candidate`. Sa compilation contrôle que les sources ne changent pas. Lancer ensuite `build_release.py` pour tester le moteur avec les DLL, animations et cartes avant publication. Une modification des sources moteur sans candidat correspondant bloque la publication suivante ; les anciens fichiers installés sont conservés.

## Atmosphère de la grille modulaire

La TriangleAPI de cette version du moteur ignore l'opacité des sommets dans certains chemins. Le compilateur produit donc huit niveaux d'opacité pour les nuages, en conservant leurs couleurs et en multipliant uniquement leur alpha original. La nappe encode son raccord radial dans l'alpha de sa texture. Le rendu trie les bancs par profondeur et sélectionne ces images précompilées ; aucune modification du moteur n'est nécessaire.

`assets/atmosphere` conserve les quatre peintures originales et les prompts ImageGen. `build_atmosphere.py` compile six faces TGA de 2048 pixels pour `vf_storm`, à partir d'un panorama et de vues dédiées au zénith et au nadir. Un même champ directionnel assure les raccords des faces. La résolution des images originales et le rééchantillonnage sont consignés dans le manifeste ; les exports compilés restent dans `generated/atmosphere`.

`vf_atmosphere.cpp` dessine une nappe sous les plateformes, deux courants de nuages à des profondeurs distinctes, des bancs supérieurs, un tourbillon lointain et des éclairs intermittents. Il utilise la TriangleAPI et les sprites RGBA natifs du moteur Xash installé. Le relief est simulé par des couches et des particules ; il n'y a pas de raymarching volumétrique. Ces décors n'ajoutent aucune collision ni entité serveur. La portée visuelle de `vf_modular` passe à 16384 pour accueillir le décor extérieur, sans changer ses limites physiques ou la récupération après chute.

La publication inclut automatiquement ciel, sprites et manifeste. Les suites obligatoires vérifient les douze arêtes du cube, ses huit coins, l'alpha des nuages, les quatre rebords, le mouvement à caméra fixe, les éclairs, les perspectives, sauvegarde/rechargement, retour de carte et isolation dans `vf_range`. Les tests existants contrôlent toujours les 102 candidats de géométrie, les douze jonctions, les déplacements et le multijoueur. `vf_atmosphere 0` retire l'animation ; `vf_atmosphere_quality 1` réduit les couches ; les valeurs normales sont 1 et 2. `vf_atmosphere_time -1` garde le temps du jeu ; une valeur positive fige uniquement le décor pour les captures. `vf_atmosphere_info` et `vf_atmosphere_bench` servent au diagnostic.

## Ambiance sonore de la grille

`build_modular_ambience.py` compile cinq longues boucles WAV PCM mono 16 bits à 22050 Hz, avec un marqueur RIFF cue natif. Les sources Half-Life copiées depuis l’installation locale et leur provenance sont dans `assets/audio/modular-ambience`. Le vent et le vortex mélangent du souffle filtré ; trois arrangements métalliques utilisent des extraits ralentis avec résonances graves, deux événements courts par cycle et de longs silences. Les périodes sont différentes.

La recette BSP place deux `ambient_generic` globaux doux et trois sources métalliques locales sans collision. Les sons n’ajoutent aucun code moteur ni changement de déplacement. Ciel et audio sont déployés ensemble dans les tests isolés. Le paquet principal inclut automatiquement les cinq WAV et leur manifeste ; les tests obligatoires vérifient marqueurs de boucle, niveaux, silence, entités du BSP, chargement natif, sauvegarde et retour de carte.
