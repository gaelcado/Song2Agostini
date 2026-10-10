# Installation et exécution

`bootstrap.py` installe les environnements isolés et vérifie versions, commits, poids et imports. Les fichiers `*_worker.py` et `estimate_grid.py` exécutent les moteurs séparés. `platform_smoke.py` et `model_smoke.py` vérifient la chaîne sur des données synthétiques, sans démontrer la fidélité musicale.

Les scripts qui manipulent les références sont dans `../lab/scripts/`. Le détail des moteurs et expériences est dans `../docs/`. Les anciens locks à la racine de configs sont des traces historiques ; l’installation portable utilise exclusivement `configs/install/`.
