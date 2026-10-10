# 0.20.5 — Lecture des effets reçus

Les états du joueur reçus par VFStatus déclenchent maintenant deux couches :
une signature animée aux bords de l’écran et un halo sur les gants/manches
R1 réellement équipés. Un badge anglais affiche le nom et la durée restante.
Les huit éléments, huit réactions et cinq états tactiques sont couverts.

Chaque élément a sa forme : gouttes, arcs, cristaux, flammes, spores, liquide
corrosif, ondes ou éclats d’impact. Une réaction combine ses deux signatures ;
Steam Veil utilise une vapeur claire. Le centre de la vue reste libre. Les
informations de santé et de munitions sont dessinées devant les bordures.

Les bras conservent leur texture et leur animation ; seule une couche de halo
est ajoutée. Les pièces de l’arme ne reçoivent pas ce halo. Les couleurs des
réactions évoluent doucement entre leurs composantes. L’effet dominant est
la réaction active la plus récente, puis le dernier état reçu.

Le lanceur classique installe le moteur vérifié avant de copier le nouveau
client. Une partie ouverte conserve ses DLL jusqu’à sa fermeture. Aucun
nouveau lanceur de build n’est ajouté.

Voir [les essais et règles de lecture](STATUS-FEEDBACK.md).
