# Sources des seuils FODMAP — dattes, raisins secs, lactose

Relevé du 2026-11-03 pour `backend/engine/rule_engine/diet.py`
(`FODMAP_THRESHOLDS["dried_date"]`, `FODMAP_THRESHOLDS["raisin_sec"]`, exclusion du lactose).

**Limite :** l'appli Monash FODMAP (la référence, payante) n'a pas été consultée.
Les seuils viennent de sites qui la citent ; une seule source est un texte de Monash
(lactose). Les valeurs Monash changent quand le laboratoire refait ses analyses :
revérifier dans l'appli avant de s'y fier pour un usage médical.

Seuils du code : grammes **par portion**. « safe » = sans problème jusqu'à ce poids,
« medium » = modéré jusqu'à ce poids, élevé au-delà.

## Dattes (`date_with_skin_dried` → `dried_date`)

Seuil retenu : **safe 39 g, medium 59 g** ; catégories fructanes (F) + sorbitol (P).

| Source | Citation | Date |
|---|---|---|
| [George Eats — Low FODMAP fruits](https://georgeats.com/posts/resources/low-fodmap-fruits-recipes-that-use-them/) | « Common pitted are low FODMAP in serves of up to 45g per person. In 46g serves, they contain moderate amounts of sorbitol and fructans. » / « Medjool dates are low FODMAP in serves of up to 39g. In 40g serves, they contain moderate amounts of sorbitol and fructans. » | « accurate as of August 2026 » (page datée 12/08/2026) |
| [The IBS Dietitian — Are dates low FODMAP?](https://theibsdietitian.com/blog/are-dates-low-fodmap-dietitian-explains-includes-recipes) | « Classic dates are low FODMAP at 30g. » / « Medjool dates are low FODMAP at 20g. » — cite Monash ; relu par Kirsten Jackson, diététicienne (RD) | non datée (© 2026) — chiffres antérieurs à la révision |
| [Karlijn's Kitchen — Are dates low FODMAP?](https://www.karlijnskitchen.com/en/are-dates-low-fodmap/) | Medjool : 20 g (1 datte) faible ; 40 g modéré (sorbitol, fructanes) ; ~60 g sorbitol élevé | ancienne révision |

Choix : seuil « safe » = la valeur Medjool récente (39 g), la plus basse des deux
variétés puisque la recette ne précise pas laquelle. Aucune source ne donne le seuil
« élevé » des chiffres récents : 59 g reprend l'ancien relevé (~60 g élevé en sorbitol).

## Raisins secs (`grape_dried` → `raisin_sec`)

Seuil retenu : **safe 13 g, medium 20 g** ; catégorie fructanes (F).

| Source | Citation |
|---|---|
| [The IBS Dietitian — Are raisins low FODMAP?](https://theibsdietitian.com/blog/are-raisins-low-fodmap-covering-all-forms-of-raisins) | « classed as low FODMAP, though the serving size is quite small at 13 grams (about 1 tablespoon) » ; 1,5 cuillère à soupe = « moderately high in FODMAPs, an amber serve » ; fructanes ; cite monashfodmap.com |
| [Gluten Free Cuppa Tea — raisins](https://glutenfreecuppatea.co.uk/?p=11776) | 1 cuillère à soupe australienne ≈ 13 g faible ; fructanes concentrés au séchage |

1,5 cuillère à soupe ≈ 20 g : au-delà, compté élevé (aucun seuil « élevé » publié).
Sultanines (raisins blonds) : sources contradictoires (7 g, « 2 cuillères à café »,
30-40 g, « élevé à toute dose ») — aucune recette n'en contient, non traitées.

## Lactose — exclu du score FODMAP

| Source | Citation |
|---|---|
| [Monash FODMAP — Lactose and dairy products on a low FODMAP diet](https://www.monashfodmap.com/blog/lactose-and-dairy-products-on-low/) (Lyndal Collins, diététicienne-chercheuse Monash, 17/01/2017) | « Regular dairy products do contain a type of natural sugar called lactose, which yes, is also a type of FODMAP. » / « you only need to limit lactose if you suffer from lactose intolerance » / les personnes concernées « can still tolerate up to two cups (yes, 500ml!) of regular milk each day » |
| [Dr. Rachel Pauls — Low-FODMAP milk options](https://rachelpaulsfood.com/dr-rachels-fodmap-facts-low-fodmap-milk-options/) | seuil Monash du lactose : < 1 g par portion ; FODMAP Friendly : ≤ 4 g |

Lecture : le lactose est un FODMAP, mais Monash ne le fait restreindre qu'en cas
d'intolérance avérée. L'exclure du score général et le traiter à part (filtre
« Sans lactose ») est cohérent avec cette position.
