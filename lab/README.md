# Laboratoire technique

Cet espace est destiné aux développeurs et aux vérificateurs. Le parcours musicien est décrit à la racine ; l’application n’expose pas le laboratoire.

- [Instructions expérimentales](AGENTS.md) : métriques, budgets d’essais, traçabilité et contrôle indépendant.
- [Scripts de recherche et vérification](scripts/README.md).
- [Ancienne vue de comparaison privée](web/README.md).
- [Documents techniques](../docs/README.md) et [état détaillé](../docs/STATUS.md).

Les données restent dans `data/raw/` et `data/reference/`, les calculs dans `work/`, les livraisons dans `outputs/`. Ces emplacements sont exclus de Git. Les identifiants internes ne remplacent jamais les vrais titres dans le produit.

Le moteur reçoit uniquement l’audio. Un vérificateur en contexte isolé reçoit les sorties figées et les références. Les retours à la recherche sont agrégés, sans notes attendues. Cette séparation est procédurale, pas une protection OS du disque partagé.
