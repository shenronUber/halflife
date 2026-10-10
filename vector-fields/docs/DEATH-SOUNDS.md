# Sons de mort et de demembrement

Le jeu superpose trois sons natifs independants : le cri de la victime, la signature de sa mort elementaire et, si une zone est retiree, le bruit de l arrachement. La banque generee contient **16 signatures de mort** et **17 signatures d arrachement**, dont une neutre. Chaque fichier est une generation ElevenLabs distincte, avec son prompt, sa reponse et ses empreintes conserves dans `assets/audio/death-sfx/shots`.

## Essayer et ecouter

Lancer `Jouer - Vector Fields.cmd`, puis **F4** et **F8**. Dans Atlas, choisir un element ou une reaction, puis Corps entier pour entendre cri + cause, ou une zone pour ajouter l arrachement. La tete utilise un timbre plus aigu, les jambes un timbre plus grave et les bras le timbre de reference. Si plusieurs zones sont retirees simultanement, une seule salve d arrachement accompagne les morceaux, pour ne pas empiler le meme son vingt fois.

`Atelier - Sons de mort.cmd` ouvre `generated/death-sfx/listen.html` : chaque ligne propose les deux signatures seules et un mix d ecoute avec le cri de Rocco. Ces mixes mono ne sont que des exemples d ecoute ; le jeu joue les fichiers separement, avec leur position et attenuation natives.

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

`data/death_sounds.json` est la source des signatures. `build_death_sounds.py --generate` contacte le fournisseur explicitement ; le build normal et `--ensure` sont hors ligne et utilisent les fichiers deja generes. La banque de jeu occupe environ **2 Mo**, en WAV mono PCM 22050 Hz / 16 bits. Le manifeste nomme chaque fichier requis ; une livraison manquante ou ancienne est rejetee.

Le serveur choisit la meme cause que le cri, avant l effacement des statuts. Une reaction active a priorite sur un element simple ; les statuts expires et les cues tactiques ne produisent pas de signature elementaire. La mort est capturee une fois par vie, y compris quand les voix sont coupees. Les bots suivent le meme chemin que les joueurs. Les cibles de la salle utilisent le meme choix. Une mort avec explosion integrale conserve egalement la cause et le son d arrachement.

Le cri utilise `CHAN_VOICE` sur la victime, la cause `CHAN_BODY` sur la victime et l arrachement `CHAN_ITEM` sur le cadavre (ou sur la victime en cas de gib integral). L evenement d arrachement accompagne la creation des fragments. La synchronisation d un cadavre ou l arrivee tardive d un observateur ne rejoue pas ces sons. Le message `VFDeathSfx` est un diagnostic ; sa reception ne declenche aucune seconde lecture. Le moteur assure la spatialisation et la diffusion reseau des sons natifs.

Volumes serveur independants : `vf_death_sfx_volume 0.8` et `vf_dismember_sfx_volume 0.8`. Mettre l un a zero coupe cette seule couche ; `vf_voices 0` coupe les voix. Les WAV gardent une marge de volume pour le melange des trois couches. Le reglage general du volume du jeu continue de s appliquer.

## Sang

L ancienne gerbe verticale `BloodStream` a ete retiree pour les coupes. Chaque membre entier nouvellement projete genere dix gouttes aux positions, vitesses et tailles variees ; les morceaux mobiles laissent ensuite des gouttes plus petites. Elles suivent des trajectoires balistiques avec gravite, dans le meme pool borne de 384 particules. Leur teinte rouge sombre explicite et leur transparence classique restent distinctes des particules elementaires lumineuses. Les decals au contact des morceaux avec le sol sont conserves. Un observateur tardif ne rejoue pas l ancienne gerbe.

## Verification

`tests/death_sounds_test.py --mode assets` verifie les 33 sources distinctes, les empreintes, le format PCM, l attaque audible, les fondus et la marge de niveau. `--mode native` couvre les 16 statuts, les cinq zones, l absence de demembrement, les volumes independants, la priorite des reactions, les effets expires et les morts reelles du joueur. Pour les cibles, il lit les listes de sons actifs exportees par le moteur dans les sauvegardes : ce sont les canaux du mixeur client reel, et pas seulement les intentions du serveur. Les captures `s_show` documentent aussi les trois sons actifs.

`tests/death_visual_multiplayer_test.py --effect corrosion` verifie deux joueurs connectes au moment de la mort et un troisieme qui rejoint ensuite. `tests/death_blood_native_test.py` produit des captures de dispersion neutre et elementaire, verifie les couleurs, les trajectoires dispersees et la limite du pool. Les rapports sont dans `build/death-audio` et `docs/validation/death-audio`.

L identification artistique des signatures reste ajustable a l ecoute en situation. Les seuils de degats par zone restent a definir, comme convenu ; ce travail se branche sur les morts et demembrements deja disponibles.
