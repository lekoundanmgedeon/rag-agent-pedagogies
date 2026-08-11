# Fait de `tests/` un vrai paquet. Sans ce fichier, pytest n'insère que
# `tests/` dans sys.path (et non la racine du projet) : `tests.api.test_chat`
# devient introuvable dès que la suite est lancée via la commande `pytest`
# plutôt que `python -m pytest` — c'est exactement ce qui cassait la CI.
