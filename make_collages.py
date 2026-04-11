"""
Thin entry point — lets you run the tool without installing it:

    python make_collages.py --input ./photos --output ./collages

For an installed command ('make-collages ...') see pyproject.toml.
"""
from collage.cli import main

if __name__ == "__main__":
    main()
