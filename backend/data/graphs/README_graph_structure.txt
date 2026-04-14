Culinary Knowledge Graph

nodes:
 ingredient
 recipe
 cuisine
 technique

edges:
 uses (recipe->ingredient)
 flavor_pair (ingredient->ingredient)
 substitute (ingredient->ingredient)
 belongs_to (recipe->cuisine)
 technique (recipe->technique)
