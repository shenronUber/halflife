# Franchissement de Brutal Half-Life V3

Analyse du 9 octobre 2026, à partir du fichier fourni :
C:/Users/Mathieu/Downloads/bhl_v3.zip.

## Résultat

**La mécanique est localisée dans le code compilé de dlls/hl.dll.** L'archive
ne fournit pas le code source C/C++ ni les symboles PDB. Elle fournit aussi
des animations de franchissement dans les modèles d'armes à la première personne.

L'identification repose sur la combinaison de trois indices : bouton IN_USE,
trois appels au test de collision du moteur, puis déclenchement d'une impulsion
verticale et d'animations propres à l'arme. Les adresses et constantes ont été
vérifiées directement dans les octets de la DLL, avec un second désassembleur.

Il s'agit d'une reconstruction par analyse statique. Aucun lancement du mod
n'a été effectué et aucun fichier du gameplay Vector Fields n'a été modifié.
La fidélité du ressenti reste à confirmer par un essai en jeu.

## Archive et base de code

- 1 400 fichiers ; 630 836 592 octets décompressés.
- Taille du ZIP : 331 654 642 octets.
- MD5 : 9b8fe2dc10f933ca2619d5fcc4cb74b7, identique à la fiche officielle relevée.
- SHA-256 du ZIP : 29759d1c91fbe00b42e56df2f277663ef89eab8a715542a4722884558bb80cac.
- SHA-256 de dlls/hl.dll : 4bbfddc1e81e8b366f5488268a33707ff132d8b020577331a2fb1ef3673e53ad.
- Aucun fichier .c, .cpp, .cc, .cxx, .h, .hpp ou .pdb.
- Readme.txt crédite SamVanheer / Half-Life Updated comme base de code.
- config.cfg associe E à +use et Espace à +jump.
- liblist.gam déclare dlls/hl.dll comme DLL du jeu et singleplayer_only.

Les fichiers utiles sont extraits dans runtime/brutal-half-life-research/v3.
Le ZIP original dans Téléchargements est conservé.

## Localisation technique

Adresses virtuelles pour cette DLL précise, avec ImageBase 0x10000000.
Les noms des fonctions non exportées sont reconstruits à partir de l'ABI
et de l'ordre des appels du SDK ; ils ne proviennent pas de symboles de débogage.

| Élément | Adresse / preuve |
| --- | --- |
| Fonction identifiée comme CBasePlayer::PlayerUse | 0x101565B0 ; lecture des boutons courant, pressé et relâché, masque IN_USE 0x20 |
| Appel depuis le traitement des impulsions | 0x1016100E appelle 0x101565B0 avant le traitement de pev->impulse |
| Début de la branche de franchissement | 0x1015946F ; nouveau test du bouton Utiliser |
| Tests de collision | 0x1015954B, 0x10159610, 0x1015967F |
| Pointeur moteur utilisé | 0x1023FAD4 : pfnTraceLine, identifié par la table enginefuncs_t |
| Sélection de l'impulsion verticale | 0x10159829 à 0x1015983B |
| Déclenchement différé | Champ joueur +0x98C, traité à partir de 0x10163715 |
| Fin de la branche / retour au son de Use | 0x1015B40C |

Le désassemblage montre une branche située après le traitement des entités
utilisables. Le mouvement et les animations sont intégrés à la logique du joueur,
pas à un simple alias de configuration ni à une entité spéciale de carte.

## Principe observé

1. Vérifier l'action Utiliser.
2. Effectuer une trace basse vers l'avant.
3. Effectuer une trace haute vers l'avant.
4. Effectuer une trace descendante depuis la zone haute pour examiner la surface.
5. Comparer les résultats : obstacle en bas, espace dégagé en haut et différence
   de hauteur suffisante entre les points touchés.
6. Vérifier l'état du joueur, choisir une classe de franchissement, programmer
   l'impulsion et déclencher la présentation correspondant à l'arme.
7. Appliquer l'impulsion immédiatement dans un cas de chute, ou après un délai
   dans le parcours différé observé.

Des contrôles portent notamment sur FL_ONGROUND, FL_DUCKING, MOVETYPE_FLY,
la vitesse verticale et plusieurs états / délais du joueur. La sémantique
de tous les champs ajoutés n'a pas été reconstruite.

| Constante lue dans la DLL | Valeur | Interprétation |
| --- | --- | --- |
| Portée de la trace basse | 70 | Unités moteur |
| Portée de la trace haute | 54 | Unités moteur |
| Décalage vertical de la trace haute | +62 | Depuis l'origine du joueur, avant la contribution de la direction de visée |
| Longueur descendante | 80 | Unités moteur |
| Seuils de classification | 26 et 46 | Comparaisons avec l'origine du joueur |
| Différence verticale entre points touchés | >12 | Condition relevée |
| Valeurs d'impulsion verticale | 280 ou 360 | Unités par seconde |
| Délai avant l'impulsion différée | 0,2 s | Échéance stockée dans le joueur |
| Verrou partagé d'action | 1,2 s | Champ également utilisé par d'autres interactions |

Ces valeurs ne définissent pas à elles seules une hauteur maximale de
franchissement : origine du joueur, posture, direction de visée et résultats
des traces interviennent. Les deux impulsions ne doivent pas être renommées
arbitrairement petit/grand sans vérifier toutes les branches.

Dans le parcours différé, le code relève l'origine de 4 unités puis écrit une
vitesse (0, 0, impulsion). Il ne s'agit donc pas, dans ce bloc, d'une interpolation
complète du joueur jusqu'à un point d'arrivée. L'avance du joueur et les
collisions durant le geste restent à observer en jeu.

## Animations trouvées

26 modèles d'armes à la première personne contiennent des séquences de la
famille LITTLEJUMP, MIDJUMP, BIGJUMP et SETJUMP, avec des variantes selon l'arme.

Exemples :
- models/v_9mmAR.mdl : MP5_LITTLEJUMP, MP5_MIDJUMP, MP5_BIGJUMP, MP5_SETJUMP.
- models/v_shotgun.mdl : SHOTGUN_LITTLEJUMP, SHOTGUN_MIDJUMP,
  SHOTGUN_BIGJUMP, SHOTGUN_SETJUMP.
- models/v_m4a1.mdl : familles M4A1 et USAS12.

La branche de déclenchement contient un choix d'animation selon l'arme.
Les séquences et leurs indices sont conservés dans le relevé JSON.
La présence d'une animation ne remplace pas la logique de mouvement.

## Extraction et réutilisation des animations

Contrôle complémentaire : les animations MP40 ont été décompilées avec le
mdldec Xash3D déjà utilisé par le projet. Les fichiers SMD éditables et le QC
sont dans runtime/brutal-half-life-research/animations-mp40.

Les quatre séquences simples LITTLEJUMP / MIDJUMP / BIGJUMP / SETJUMP ont
respectivement 19 / 19 / 19 / 26 frames. La lecture de leurs poses confirme
des changements réels sur plusieurs os : ce ne sont pas des noms vides.
Les variantes dual sont également extraites.

Le modèle BHL MP40 possède 24 os ; le r01_rig.mdl actuel en possède 43.
Neuf noms d'os sont communs, avec des différences de hiérarchie. Le fait que
notre rig soit aussi issu d'un MP40 ne garantit donc pas la compatibilité.
Le transfert des gestes nécessite une adaptation de squelette et un contrôle
visuel ; il n'a pas encore été validé.

Approche proposée : réutiliser un geste extrait comme donneur, adapter ses
poses au rig R-01, puis raccorder une seule variante de mouvement sur Espace.
La logique à écrire s'appuie sur les traces et valeurs déjà identifiées dans
le binaire. Les animations n'ont pas besoin d'être inventées, mais leur raccord
à notre arme et leur synchronisation avec le déplacement restent du travail.

Relevé : runtime/brutal-half-life-research/animation-reuse-assessment.json.

## Choix retenu pour Vector Fields

Exigence utilisateur : **Espace déclenche le franchissement lorsqu'un obstacle
adapté est devant le joueur ; sinon Espace conserve le saut. E reste Utiliser.**

Schéma proposé pour notre implémentation, non encore réalisée :

- Sur un nouvel appui d'Espace, tenter la détection d'un obstacle franchissable.
- Si la détection et la place libre pour le volume du joueur sont valides,
  commencer le franchissement et consommer ce saut.
- Sinon, laisser le saut habituel se produire.
- Rendre les portées, hauteurs et durées ajustables pour les itérations.
- Partager la logique de mouvement entre client et serveur ; adapter les gestes
  à notre arme R-01 et vérifier les plafonds, coins et obstacles mobiles.

Ce schéma est une proposition pour Vector Fields. Il n'est pas présenté comme
le code source original de Brutal Half-Life. La vérification du volume complet
du joueur et le déclenchement sur nouvel appui sont des choix proposés pour
notre version ; les trois traces BHL examinées sont des TraceLine.

## Relevés reproductibles

- runtime/brutal-half-life-research/v3-archive-inventory.json : inventaire et empreintes.
- runtime/brutal-half-life-research/v3-vaulting-evidence.json : adresses, constantes,
  contrôles et séquences des modèles.
- runtime/brutal-half-life-research/inspect_v3.py : relecture statique du ZIP.
- runtime/brutal-half-life-research/v3/detection_and_trigger.asm : branche principale.
- runtime/brutal-half-life-research/v3/delayed_motion.asm : application différée.
- runtime/brutal-half-life-research/v3/hl-disasm.txt : désassemblage complet local.

Les contrôles statiques confirment le bouton, les trois appels TraceLine, les
deux impulsions et l'absence de sources/PDB. Ils ne constituent pas un test
de gameplay ni une validation réseau.

