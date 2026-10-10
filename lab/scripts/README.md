# Scripts privés de comparaison

`prepare_inputs.py` prépare les copies privées et manifestes. `import_benchmark.py` importe un corpus autorisé. `render_review.py` et `render_corpus_review.py` préparent les vues des références ; `render_output_review.py` et `sync_output_review.py` ajoutent les PDF des runs figés.

Exécuter depuis la racine avec un environnement de recherche contenant les dépendances nécessaires. Exemple : `.venv/bin/python lab/scripts/import_benchmark.py --config configs/corpus-oga-v1.json`. Les rendus nécessitent notamment Verovio/Pillow/Poppler ; ce ne sont pas les dépendances de l’application musicale.

Ces outils accèdent aux références. Ils sont réservés au vérificateur et ne doivent pas servir de prétraitement au moteur. Leur sortie est privée sous `work/verification/`. Appliquer ../../docs/separation.md.
