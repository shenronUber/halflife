# Textures des zones de démembrement

Cinq matériaux dédiés ferment le cou, les deux bras et les deux cuisses. Trois
sources originales fournissent les familles cou, bras et cuisse : chair bordeaux
mate, fibres discrètes, os beige grisé. Les côtés possèdent des matériaux et des
UV distincts ; ils partagent la source anatomique de leur famille.

## Dimensions et UV

Mesures calculées sur les frontières réelles du GIGN, dans sa pose de référence.
Les largeurs/hauteurs sont les étendues projetées sur les deux axes principaux
(PCA), en **unités du modèle GoldSource**, et non des centimètres anatomiques.
La profondeur indique l'écart perpendiculaire au plan de projection ; la surface
est la somme des triangles de fermeture, en unités au carré.

| Zone | Étendue projetée (unités) | Profondeur | Surface | Texture dans le MDL |
| --- | --- | --- | --- | --- |
| Cou | 9.384424 × 8.707979 | 1.538412 | 71.406164 | 152 × 139 |
| Bras gauche | 7.394862 × 6.464045 | 0.000009 | 35.563223 | 120 × 105 |
| Bras droit | 7.354983 × 6.348279 | 0.000007 | 35.874389 | 120 × 103 |
| Cuisse gauche | 9.657077 × 8.773835 | 0.000000 | 56.989267 | 156 × 141 |
| Cuisse droite | 9.657422 × 8.932203 | 0.000000 | 57.530626 | 156 × 143 |

Chaque BMP source comporte **256 × 256 pixels**, indexés sur 256 couleurs, pour
un canevas physique de **16 × 16 unités**, soit **16 pixels par unité**.
Le compilateur élimine les marges inutilisées et ajuste les coordonnées ; les
petites dimensions finales du tableau correspondent à ce recadrage. Les UV
utilisent une projection continue pour toute la section, avec l'arrondi au pixel
propre au format MDL. Chaque triangle dispose d'une surface UV non nulle.

[Planche UV](validation/wound-textures/uv-mesures.png) ·
[Mesures complètes, axes, empreintes et coupes des fragments](validation/wound-textures/measurements.json)

## Géométrie et éclairage

Les bras sont coupés à 1,9 unité du début de l'humérus, avec un plan perpendiculaire
à l'axe du bras dans la pose de référence. Les cuisses sont coupées à **z = 30**,
sous la bifurcation du pantalon. Un moignon subsiste : le bassin est conservé,
ainsi que l'étui de cuisse séparé (28 faces), auquel aucune chair n'est appliquée.
Le cou reprend le contour légèrement irrégulier du col existant.

Les sommets du contour et du bouchon partagent l'os de la coupe. Ils restent donc
jointifs quand le bras, la jambe ou le cou tourne. La subdivision du modèle de
cadavre passe de 740 à 828 triangles extérieurs ; les UV des sommets originaux
sont préservés et l'écart de surface après compilation reste inférieur à 0,01 %.
Les modèles des personnages vivants et leurs 77 animations restent inchangés.
Les quinze fragments reçoivent aussi les matériaux de leur région.

Seules les plaies utilisent le drapeau GoldSource **FLATSHADE**. Le moteur leur
applique la lumière ambiante et 80 % de la lumière de modelé de l'entité : les
faces orientées vers le sol restent lisibles. Elles sont opaques, sans addition
lumineuse ni émission. Les vêtements conservent leur éclairage habituel.

## Essai et validation

Relancer **Jouer - Vector Fields.cmd**, ouvrir **F4**, puis **F8**. Choisir le
membre et la mort classique ou électrique. Les textures sont indépendantes de
l’effet et des quatorze finitions de vêtements. Les seuils de dégâts demeurent
reportés, comme prévu dans le prototype.

```text
python vector-fields/tests/wound_textures_test.py --assets
python vector-fields/tests/wound_textures_test.py
python vector-fields/tests/death_visual_native_test.py
python vector-fields/tests/death_visual_multiplayer_test.py
python vector-fields/tests/death_ui_native_test.py
```

Les gros plans natifs ont été revus pour les cinq plaies ; le clic F8 déclenche
une vraie mort avec tête explosée et effet électrique. Le contrôle des os et UV
couvre les poses de repos, les chutes, le headshot et la contraction électrique,
les 32 masques de perte, les 14 finitions et les 15 variantes de fragments.
[Captures du moteur](validation/wound-textures/apercu-plaies.jpg).

Pour la revue de près, la commande de développement
`cmd vf_death_inspect left_arm` déplace le dernier cadavre concerné dans l'allée,
fige sa pose et cadre la coupe. Elle est limitée à `vf_range` et aux développeurs.
Utiliser `noclip` pour la caméra sous les moignons. Ces poses figées servent
uniquement à l'inspection ; les morts ordinaires conservent leur chute.

## Sources graphiques

Les sources PNG ont été générées avec **image_gen intégré**, puis réduites et
converties en BMP8 par le pipeline. Aucune bibliothèque graphique tierce n'est
intégrée. Les prompts effectivement utilisés et la date sont conservés dans
[assets/deaths/prompts.json](../assets/deaths/prompts.json), et les PNG maîtres
[du cou](../assets/deaths/neck-source.png), [du bras](../assets/deaths/arm-source.png)
et [de la cuisse](../assets/deaths/thigh-source.png) sont reproductibles comme
entrées du build. Les prompts précèdent la correction des sections planes ; les
mesures finales font foi dans le tableau et le JSON de validation.
