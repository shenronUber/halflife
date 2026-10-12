# Construction et intégration

Le profil principal est `vf_visual`. Il contient `vf_range` (combat et parcours), `vf_modular` (grille aléatoire), et les cartes historiques de régression. `game_profiles.py` est le registre des cartes locales. Une nouvelle carte exige sa recette, son enregistrement, un test natif de chargement/collision.

## Construire et publier

`python vector-fields/build_release.py` ou `vector-fields/build.ps1` prépare un candidat lorsque les sources ou le build installé ont changé. `--force` impose un nouveau candidat. Les deux DLL sont compilées dans un cache privé, puis copiées avec leurs sources dans un dossier immuable `build/releases/<id>`. Le jeu complet y est préparé, sans écrire dans le mod principal.

La publication exige les suites `unit`, `policy`, `assets` et `integration`. La dernière couvre mêlée, réseau, poses/hitboxes, wall run et regard libre, back jump, rechargement, dégâts, les cibles de tir, le parcours combiné, la grille modulaire et les sauvegardes. Les anciennes suites natives et multijoueurs restent accessibles pour élargir les contrôles.

Les empreintes des sources et du paquet sont revérifiées après les tests. Le même verrou protège construction, publication et démarrage. Le mod complet est remplacé par renommage ; les DLL canoniques et ressources moteur sont sauvegardées et restaurées en cas d'échec. L'ancien mod reste conservé sous `.vf_visual-before-*`. Les sauvegardes et préférences locales survivent. Fermer le jeu avant une publication qui remplace ses DLL.

Les résultats sont liés aux empreintes du paquet dans `vf/release-bundle.json`. Ne pas publier en copiant une DLL à la main, ni réutiliser une preuve provenant d'un ancien candidat.

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

`vector-fields/build-engine.ps1` compile les extensions et leurs tests dans `build/engine-candidate`. Sa compilation contrôle que les sources ne changent pas. Lancer ensuite `build_release.py` pour tester le moteur avec les DLL, animations et cartes avant publication. Une modification des sources moteur sans candidat correspondant bloque la publication suivante ; les anciens fichiers installés sont conservés.
