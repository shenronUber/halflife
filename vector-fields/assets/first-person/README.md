# Essais de textures de première personne

Ces trois atlas sont des **essais HD archivés**, non utilisés par le jeu.
Le rendu actuel utilise uniquement les textures existantes de `assets/personas`,
avec un dépliage adapté par `build_first_person.py`. La géométrie actuelle
conserve les volumes du modèle précédent ; les références CS sont archivées
dans `build/first-person-experiments`.

Les trois images ont été générées avec **built-in image_gen**, puis sauvegardées
sans nouvelle peinture. Les prompts exacts et les fichiers sont conservés ici :

| Essai | Atlas enregistré | Prompt exact |
|---|---|---|
| GIGN | [texture-atlas.png](gign/texture-atlas.png) | [prompt.txt](gign/prompt.txt) |
| Rome / Inventeur | [texture-atlas.png](roman-inventor/texture-atlas.png) | [prompt.txt](roman-inventor/prompt.txt) |
| Dieselpunk | [texture-atlas.png](dieselpunk/texture-atlas.png) | [prompt.txt](dieselpunk/prompt.txt) |

Leur layout expérimental était destiné au prototype de mains CS abandonné.
Il ne correspond pas au dépliage actuel et aucun atlas de ce dossier n’est
chargé par le build, le déploiement ou le moteur.
