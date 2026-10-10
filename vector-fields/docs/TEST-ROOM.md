# Salle de test GIGN et dÃ©clenchements Ã©lÃ©mentaires

La carte `vf_range` comporte quatre cibles GIGN utilisant les quatorze tenues du jeu. Leurs tenues initiales sont diffÃ©rentes et leur voix est tirÃ©e dans la banque des six opÃ©rateurs existants. Le dÃ©cor, les Ã©clairages et les animations de base sont conservÃ©s. Ces cibles restent sur place ; elles servent aux tests de tir et de dialogue.

## Essayer

Relancer **Jouer - Vector Fields.cmd**, puis **F4** pour revenir dans la salle. Choisir un vecteur dans **F3 > Weapon FX / R1**, fermer le panneau et tirer avec le R1. **J** provoque les personnages proches : la cible vivante la plus proche qui entend le joueur lui rÃ©pond aprÃ¨s sa rÃ©plique. Le son est positionnel. Pour afficher aussi les sous-titres des cibles, saisir `vf_voice_subtitles 2` ; `1` conserve les seuls sous-titres du joueur, `0` les masque.

Au-dessus de chaque cible figurent son numÃ©ro, sa voix, sa santÃ© et la progression vers le dÃ©clenchement. Une fois l'Ã©tat actif, un halo, des particules et un compte Ã  rebours le montrent sur son corps. Les huit Ã©tats sont Hydro, Electro, Cryo, Thermal, Toxic, Corrosion, Sonic et Kinetic.

Chaque cible possÃ¨de **300 points de vie**. Elle disparaÃ®t Ã  sa mort et revient **2 secondes** plus tard avec sa santÃ© restaurÃ©e, ses Ã©tats effacÃ©s et une nouvelle tenue/voix. Aucune entitÃ© HEV n'est crÃ©Ã©e.

## RÃ¨gle de dÃ©clenchement

- **6 impacts de balles du mÃªme Ã©lÃ©ment, sur la mÃªme victime, dans une fenÃªtre glissante de 3 secondes.** Un impact de plus de 3 secondes est retirÃ© individuellement ; un impact exactement Ã  la limite reste admissible.
- Le sixiÃ¨me impact consomme les six compteurs et active un Ã©tat pour **6 secondes**. Six nouveaux impacts rafraÃ®chissent cette durÃ©e. Le nombre de dÃ©gÃ¢ts d'un impact ne multiplie pas son compteur.
- Les huit Ã©lÃ©ments ont des compteurs indÃ©pendants. Changer de victime ne transfÃ¨re aucune progression. Plusieurs tireurs peuvent contribuer Ã  la mÃªme victime.
- Les tirs dÃ©clenchent uniquement les **huit Ã©tats primaires**. Ils ne produisent aucune rÃ©action couplÃ©e automatique. L'atelier manuel de rÃ©actions reste disponible sÃ©parÃ©ment.
- Sur le R1, le profil de test validÃ© par le serveur fournit l'Ã©lÃ©ment. Par dÃ©faut, les balles natives sont **Kinetic**. Les tenues, finitions et familles d'objets ne choisissent pas d'Ã©lÃ©ment. La mÃªlÃ©e, les grenades et les dÃ©gÃ¢ts sans contexte de balle n'ajoutent pas de compteur.

La rÃ¨gle est cÃ´tÃ© serveur, pour les cibles et les joueurs/bots vivants autorisÃ©s Ã  subir ces tirs. Pour les joueurs, les vÃ©rifications d'Ã©quipe et de godmode restent applicables. Les impacts, les Ã©tats, la durÃ©e et la santÃ© des cibles sont rÃ©pliquÃ©s aux clients ; un nouvel arrivant reÃ§oit leur Ã©tat courant.

**Cette Ã©tape ajoute le dÃ©clenchement, le rendu et les rÃ©actions vocales.** Elle conserve les dÃ©gÃ¢ts balistiques et l'armure existants. Elle ne calibre pas encore les dÃ©gÃ¢ts pÃ©riodiques, les ralentissements ni la protection des matÃ©riaux. La nature physique du projectile et le statut de test restent deux informations distinctes, voir [les matÃ©riaux](COMBAT-MATERIALS.md).

## ImplÃ©mentation et diagnostic

`game_shared/vf_proc_policy.h` contient la fenÃªtre, le seuil et la durÃ©e. `vfs::ApplyPrimary` applique un Ã©tat sans chercher de partenaire. `VF_ProjectileTraceScope` transporte l'Ã©lÃ©ment du tir rÃ©el ; il conserve la restitution du contexte Ã  la fin de chaque impact.

`dlls/vf_range.cpp` expose `vf_range_target`, avec le squelette de collision GIGN `persona_rig.mdl`. Le renderer assemble `persona_scout.mdl`, corps complet et tenue choisie, sur ce squelette. Les volumes anatomiques du modÃ¨le serveur suivent sa pose de base ; aucune correction visuelle locale ne sert Ã  compter les contacts. Les limites de correspondance des poses en dÃ©placement restent celles documentÃ©es dans [COMBAT-MATERIALS.md](COMBAT-MATERIALS.md).

`VFTarget` transmet une version, l'entitÃ©, l'emplacement, la tenue, la voix, la santÃ© et les huit durÃ©es/compteurs. `VFRangeVoice` accompagne les sons positionnels pour les sous-titres. Les files vocales partagent les rÃ¨gles existantes de prioritÃ©, cooldown et choix sans rÃ©pÃ©tition immÃ©diate.

`build_test_room.py` modifie seulement les entitÃ©s du BSP. Les lumps de gÃ©omÃ©trie et de lumiÃ¨re sont conservÃ©s ; la transformation est idempotente. `play.py` applique la nouvelle salle et installe ses modÃ¨les lors des dÃ©ploiements natifs.

Commandes de diagnostic :

```text
cmd vf_range_info
vf_range_client
vf_shotfx hydro
vf_shotfx auto
```

En solo ou avec les cheats, uniquement dans `vf_range` :

```text
cmd vf_range_aim 0
cmd vf_range_reset 0
cmd vf_range_fire 0 6
```

Les numÃ©ros de console vont de 0 Ã  3. `fire` utilise la vÃ©ritable primitive serveur `FireBulletsPlayer`, avec une ligne de tir contrÃ´lÃ©e, sans consommer le chargeur ; c'est un outil de vÃ©rification. Les tirs normaux sont vÃ©rifiÃ©s sÃ©parÃ©ment.

## VÃ©rifications

`tests/proc_policy_test.cpp` vÃ©rifie le seuil, la fenÃªtre glissante, la limite exacte, l'expiration, les victimes/Ã©lÃ©ments indÃ©pendants et l'absence de rÃ©actions couplÃ©es. Les tests des rÃ¨gles de voix et du calcul historique des dÃ©gÃ¢ts passent Ã©galement.

`tests/test_room_native_test.py` lance un essai court dans un runtime isolÃ© : quatre tenues GIGN, cinq impacts sans Ã©tat puis le sixiÃ¨me pour les huit Ã©lÃ©ments, rÃ©ception client, tir normal, huit rÃ©actions vocales, expiration, rÃ©ponse Ã  une provocation, mort et retour d'une cible. Les captures sont contrÃ´lÃ©es pour l'habillage et les effets. Le renderer accepte les assemblages.

Le contrÃ´le natif des matÃ©riaux utilise aussi la nouvelle DLL serveur : sept rÃ©gions anatomiques, dÃ©gÃ¢ts et armure historiques, contexte de projectile et hitboxes du rechargement.

Rapports et captures conservÃ©s dans [validation/test-room](validation/test-room/native-verification.json). L'essai des quatre cibles est local Ã  un client ; une session multijoueur avec plusieurs clients n'a pas Ã©tÃ© rejouÃ©e pour cette salle.

## Cris de mort contextuels

Les cibles utilisent maintenant les 102 cris brefs des six voix, sans mots ni sous-titres. Un Ã©tat Ã©lÃ©mentaire actif au moment de la mort choisit le cri correspondant ; un mÃ©lange actif a prioritÃ© sur un Ã©lÃ©ment simple. Les cinq Ã©tats tactiques gardent le cri standard. L'Ã©tat est lu avant sa remise Ã  zÃ©ro, et le cri coupe les dialogues en cours.

Pour comparer : `cmd vf_range_voice 0 rocco`, `cmd vf_range_effect 0 steam_veil`, puis `cmd vf_range_kill 0`. `cmd vf_range_reset 0` restaure immÃ©diatement la cible. Ces commandes sont rÃ©servÃ©es au solo ou aux cheats, dans cette salle. Voir [DEATH-VOICES.md](DEATH-VOICES.md).

## Génération et validation depuis 0.20.7

La source est `weapon-lab/build_range.py`, qui construit la géométrie depuis ses définitions Python et les textures Half-Life installées. Son cache vérifie le code, le WAD, les quatre compilateurs et les sorties. `build_test_room.py --ensure` transforme ce BSP de base, conserve ses quatorze lumps de monde et ajoute les quatre cibles. Aucun BSP du runtime installé ne sert de source.

`build.ps1`, `play.py` et le staging des essais natifs utilisent ce même résultat. Le contrat de déploiement vérifie `vf_range.bsp` et `vf_fx_range.bsp` par SHA-256. La validation centrale inclut le test natif de la salle et la matrice des cris de mort contextuels, avec les DLL courantes.
