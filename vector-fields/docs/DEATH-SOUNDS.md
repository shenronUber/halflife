# Sons de mort et de demembrement

Le jeu superpose trois sons natifs independants : le cri de la victime, la signature de sa mort elementaire et, si une zone est retiree, le bruit de l arrachement. La banque generee contient **16 signatures de mort**, **17 signatures d arrachement** et **17 explosions de tete**, dont les variantes neutres. Les sons conservent leur vitesse et leur duree naturelles, entre **1,06 et 2,08 secondes** au timbre de reference. Les 33 prises courtes de mort et d arrachement sont reprises depuis les sources initiales ; les 17 explosions de tete sont generees directement pour deux secondes. Une tete retiree joue sa seule explosion humide, facon citrouille, avec la signature de son element : le cri et la signature de mort supplementaire sont supprimes. Chaque fichier est une generation ElevenLabs distincte, avec son prompt, sa reponse et ses empreintes conserves dans `assets/audio/death-sfx/shots` et `assets/audio/death-sfx/natural-heads/shots`.

## Essayer et ecouter

Lancer `Jouer - Vector Fields.cmd`, puis **F4** et **F8**. Dans Atlas, choisir un element ou une reaction, puis Corps entier pour entendre cri + cause, ou une zone pour ajouter l arrachement. La tete utilise son propre son d explosion a un timbre legerement plus aigu (104 %), les jambes un timbre legerement plus grave (96 %) et les bras le timbre de reference. Si plusieurs zones sont retirees simultanement, une seule salve d arrachement accompagne les morceaux, pour ne pas empiler le meme son sur chaque membre.

`Atelier - Sons de mort.cmd` ouvre `generated/death-sfx/listen.html` : chaque ligne propose les signatures de mort, d arrachement et de tete seules et un mix d ecoute avec le cri de Rocco. Ces mixes mono ne sont que des exemples d ecoute ; le jeu joue les fichiers separement, avec leur position et attenuation natives.

| Cause | Signature de mort | Arrachement |
|---|---|---|
| Hydro | Affaissement liquide et bouillon grave | Rupture imbibee, jet bref |
| Electro | Cinq impulsions electriques, extinction | Craquement et claquement electrique |
| Cryo | Fissures fines, tintement froid | Cassure gelee compacte |
| Thermal | Souffle de flamme et braises | Rupture brulante et souffle sec |
| Toxic | Bouffee de spores et flutter creux | Dechirure molle et spores |
| Corrosion | Bulles irregulieres et dissolution | Dechirure liquide et gresillement |
| Sonic | Trois pulsations et anneau descendant | Rupture seche et anneau court |
| Kinetic | Impact grave unique et debris | Craquement lourd et fibres |
| ArcChain | Trois relais electriques dans l eau | Rupture mouillee et trois arcs |
| Superconduction | Sifflement glace, cristal et etincelles | Cassure cristalline, chirp electrique |
| Shatter | Fracas glace et cascade d eclats | Cassure violente et eclats courts |
| ResonantImpact | Choc puis deux rebonds metalliques | Claquement osseux et double resonance |
| Cavitation | Implosion de bulles et pop creux | Rupture humide sous pression |
| CausticContagion | Deux pustules acides et spores | Rupture visqueuse, bulles et spores |
| ToxicIgnition | Allumage de gaz sourd et flamme | Claquement humide et inflammation |
| SteamVeil | Decompression et gouttelettes | Rupture saturee, jet de vapeur |
| Neutre | Cri habituel seul | Rupture fibreuse et gouttes |

## Integration

`data/death_sounds.json` est la source des signatures. `build_death_sounds.py --generate` contacte le fournisseur explicitement ; le build normal et `--ensure` sont hors ligne et utilisent les fichiers deja generes. La banque de jeu occupe environ **3,6 Mo**, en WAV mono PCM 22050 Hz / 16 bits. Le manifeste nomme chaque fichier requis ; une livraison manquante ou ancienne est rejetee.

Le serveur choisit la meme cause que le cri, avant l effacement des statuts. Une reaction active a priorite sur un element simple ; les statuts expires et les cues tactiques ne produisent pas de signature elementaire. La mort est capturee une fois par vie, y compris quand les voix sont coupees. Les bots suivent le meme chemin que les joueurs. Les cibles de la salle utilisent le meme choix. Une perte de toutes les zones forcee par les outils developpeur conserve egalement la cause et le son d arrachement. Un overkill non localise ne contourne pas les conditions anatomiques.

Le cri utilise `CHAN_VOICE` sur la victime, la cause `CHAN_BODY` sur la victime et l arrachement `CHAN_ITEM` sur le cadavre. L evenement d arrachement accompagne la creation des fragments. La synchronisation d un cadavre ou l arrivee tardive d un observateur ne rejoue pas ces sons. Le message `VFDeathSfx` est un diagnostic ; sa reception ne declenche aucune seconde lecture. Le moteur assure la spatialisation et la diffusion reseau des sons natifs.

Volumes serveur independants : `vf_death_sfx_volume 1` et `vf_dismember_sfx_volume 1`. Mettre l un a zero coupe cette seule couche ; `vf_voices 0` coupe les voix. Les signatures ont un niveau moyen plus present, avec compression douce et limitation progressive des pointes. Les cris existants gardent leurs fichiers et leur volume original de 0,85. Seuls les effets autour sont remasterises. Les banques actuelles gardent une marge pour le melange des trois couches. Le nombre d echantillons de chaque source reste identique apres traitement de niveau : aucun etirement, aucune boucle et aucun ajout de silence pour atteindre une duree imposee. Le reglage general du volume du jeu continue de s appliquer.

## Sang

L ancienne gerbe verticale `BloodStream` a ete retiree pour les coupes. Chaque membre entier nouvellement projete genere dix gouttes aux positions, vitesses et tailles variees ; les morceaux mobiles laissent ensuite des gouttes plus petites. Elles suivent des trajectoires balistiques avec gravite, dans le meme pool borne de 384 particules. Leur teinte rouge sombre explicite et leur transparence classique restent distinctes des particules elementaires lumineuses. Les decals au contact des morceaux avec le sol sont conserves. Un observateur tardif ne rejoue pas l ancienne gerbe.

## Verification

`tests/death_sounds_test.py --mode assets` verifie les 50 sources distinctes, les durees naturelles et la conservation exacte du nombre d echantillons des sources, les empreintes, le format PCM, l attaque audible, les fondus et la marge de niveau. `--mode native` couvre les 16 statuts, les cinq zones, l absence de demembrement, les volumes independants, la priorite des reactions, les effets expires et les morts reelles du joueur. Pour les cibles, il lit les listes de sons actifs exportees par le moteur dans les sauvegardes : ce sont les canaux du mixeur client reel, et pas seulement les intentions du serveur. Les captures `s_show` documentent aussi les sons actifs. Une sauvegarde plus tardive verifie que les effets courts sont termines.

`tests/death_visual_multiplayer_test.py --effect corrosion` verifie deux joueurs connectes au moment de la mort et un troisieme qui rejoint ensuite. `tests/death_blood_native_test.py` produit des captures de dispersion neutre et elementaire, verifie les couleurs, les trajectoires dispersees et la limite du pool. Les rapports sont dans `build/death-audio` et `docs/validation/death-audio`.

Le dÃ©membrement se produit uniquement Ã  la mort, avec deux conditions : la tÃªte ou le membre a cumulÃ© **strictement plus de 50 % de la vie maximale** en dÃ©gÃ¢ts de santÃ© aprÃ¨s l'armure, et le **coup fatal touche cette mÃªme rÃ©gion**. Les compteurs sont indÃ©pendants, conservÃ©s dans save/load et remis Ã  zÃ©ro Ã  la rÃ©apparition. Ils ne diminuent pas lorsqu'on soigne le personnage. Une mort au torse, une chute ou un dÃ©cÃ¨s sans impact localisÃ© ne sÃ©lectionne aucun membre, mÃªme si une rÃ©gion avait dÃ©jÃ  franchi le seuil. L'overkill historique des opÃ©rateurs compatibles ne contourne pas cette rÃ¨gle par une explosion intÃ©grale automatique. Les commandes du laboratoire gardent leur masque explicitement imposÃ©.

Chaque perte projette **un membre principal et trois petits dÃ©bris physiques**, habillÃ©s avec les finitions de la victime, avec des trajectoires et rotations indÃ©pendantes. Une seule salve sonore accompagne la gerbe. Les budgets de fragments et de particules restent bornÃ©s. Les dÃ©gÃ¢ts de chute conservent leur montant et la rÃ©action de douleur, mais n'appliquent plus l'Ã©tat Kinetic ni l'Ã©lÃ©ment de l'arme Ã©quipÃ©e.

`death_automatic_native_test.py` vÃ©rifie les vraies morts de cibles par balles. `combat_regression_native_test.py` contrÃ´le les cinq seuils exacts et dÃ©passÃ©s, les coups fatals sur une autre rÃ©gion, l'accumulation, l'armure, save/load, l'invulnÃ©rabilitÃ©, les quatre fragments et huit vraies chutes avec diffÃ©rents profils de tir.
