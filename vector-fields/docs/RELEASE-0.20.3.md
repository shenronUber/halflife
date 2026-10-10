# 0.20.3 — Flashes frontaux R1

La texture de profil ne sert plus au rendu du tireur. Huit sprites radiaux
originaux, générés avec ImageGen, fournissent une étoile vue de face pour
chaque vecteur. L'émission est centrée sur le socket réel du canon.
Le jet axial reste réservé aux vues extérieures, avec transition selon l'angle.

Les événements Studio 5001, 5011, 5021 et 5031 des modèles R1 ne déclenchent
plus le flash historique de Half-Life en parallèle. Les autres modèles
conservent leurs événements et leurs sons.

Le test natif contrôle les huit tirs : rendu frontal présent, zéro frame
axiale pour le tireur, événement historique filtré. Le test à deux clients
contrôle le jet extérieur depuis une caméra réellement placée de profil.
Les ressources restent 40 sprites et 40 WAV ; les impacts et le gameplay
ne changent pas.

Lancer `Jouer - Vector Fields.cmd`, puis F3 > Weapon FX / R1. Une partie
déjà ouverte doit être relancée pour charger le nouveau client.
Voir [la documentation](../WEAPON_FX.md).
