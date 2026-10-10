# 0.20.6 — Maintenance de la génération et des contrats

Cette maintenance part de la 0.20.5 et conserve ses équipements, textures,
animations, effets et voix. Les corrections portent sur les quatre dettes
concrètes de l’audit.

- **Génération fiable et ciblée.** Les fichiers donneurs, recettes, auxiliaires,
  textures et le compilateur participent aux empreintes. Les sorties sont
  vérifiées par SHA-256. Les pièces/textures et les six rigs R-01 ont deux
  caches distincts : une retouche de recette ou de script de geste dédié ne reconstruit pas les 61 pièces.
  Les quatre générateurs savent éviter la compilation quand leurs entrées et
  sorties sont inchangées. Un format partagé du catalogue des finitions évite
  les reconstructions causées par les réécritures de deux scripts.
- **Caractéristiques de modèles partagées.** `data/model_contract.json` définit
  les montages des châssis, les prises des accessoires, les neuf porteurs et
  les sockets. Python et l’en-tête C++ généré utilisent ce contrat. Les 182
  variantes des châssis et accessoires concernés héritent de leur géométrie.
  Les correspondances des joints sources sont vérifiées avant retargeting.
- **Validation cohérente avec le jeu actuel.** `validate.py` regroupe les suites
  unitaires, assets, solo et multijoueur. Les anciens sélecteurs de plateformes
  sont remplacés dans les essais par des objets nommés. Les scénarios utilisent
  les DLL de release, y compris les tests d’animations et de voix. Le test
  voix/états attend maintenant la connexion réelle avant ses commandes.
  Le lancement et son test partagent aussi le chargement de la politique vocale.
- **Livraison et documentation vérifiables.** Les empreintes installées couvrent
  les DLL, catalogues, effets, bras, personnages, pièces et trois porteurs
  tiers-personne. Les modèles requis sont explicites, même si un glob est vide.
  Les tables des contrats moteur/réseau sont générées depuis les déclarations
  C++ et leur dérive fait échouer la validation. Les documents courants sont
  actualisés ; les problèmes d’encodage des deux documents principaux sont corrigés.

Les identifiants d’objets, le protocole 4, les formats de sauvegarde et le rendu
restent compatibles. Les 74 modèles compilés et les deux catalogues comparés
sont identiques, octet pour octet, à la référence locale 0.20.5.

## Vérifications

37 tests unitaires Python couvrent les caches, la reconstruction partielle,
les erreurs de compilation, les traits de modèles, les sorties manquantes ou
corrompues, la livraison, le démarrage et la documentation. Les tests C++
valident les budgets, migrations, finitions, sélecteurs, effets et règles de
combat/voix ; 2 486 vérifications concernent l’architecture et la persistance.

Les dix contrôles d’assets comprennent les neuf porteurs compilés, les 196
paires gants/manches, 1 110 poses de poignée avant et 1 677 poses tiers-personne.
Les cinq scénarios solo exercent lancement, inventaire, sauvegardes et gestes.
L’audit natif accepte 1 753 assemblages et les 1 113 objets du catalogue.
Quatre scénarios à deux clients couvrent les rechargements distants, arrivées
tardives, finitions indépendantes, tirs, réactions et voix de mort/élimination.

Les résultats datés et les empreintes des DLL sont conservés dans
[le rapport de maintenance](validation/maintenance-0.20.6.json).
Ces essais contrôlent le comportement ; l’esthétique de toutes les combinaisons
reste à apprécier en jeu. Les essais réseau utilisent une boucle locale.

## Relancer les contrôles

```powershell
powershell -ExecutionPolicy Bypass -File vector-fields/build.ps1
python vector-fields/play.py --visual-lab --deploy-only
python vector-fields/validate.py --suite native
python vector-fields/validate.py --suite multiplayer
```

Le build compile les tests C++ et exécute déjà les suites Python `unit` et
`assets`. `validate.py --suite all` enchaîne les quatre suites après compilation
et déploiement ; `--list` montre leurs scénarios. Les assets donneurs locaux
requis restent ceux du projet existant.


## Decals HUD des états

Les huit éléments et les huit réactions possèdent chacun un décor original,
soit 64 images peintes animées par fondu. Les réactions intègrent leurs deux
matières dans des textures dédiées. Les marges et profondeurs sont normalisées
sur les quatre frames ensemble : ancrage commun aux coins, enveloppe de 14 %,
centre transparent. Les sprites RGBA conservent couleurs et transparence,
avec une opacité commune de 72 %. Aucun traitement particulier des emplacements
actuels du HUD. Les badges anglais, la durée serveur, les effets sur les bras
et les cinq états tactiques existants sont conservés.

**Jouer - Vector Fields.cmd**, puis **F3 > Test joueur / voix > Sur moi**.
Les combinaisons peuvent être déclenchées avec **Combiner**. Les ressources
sont embarquées ; le lancement reste hors ligne et en version **0.20.6**.

Sources et prompts imagegen : `assets/status-feedback/decals/generation.json`.
Planche : `assets/status-feedback/decals/contact-sheet.png`.
Conversion : `build_status_decals.py --ensure`, avec empreintes des entrées et
sorties vérifiées. Voir `docs/STATUS-FEEDBACK.md` pour les contrôles et tests.
