.PHONY: install ui run help

help:
	@echo "make install   — create venv and install all dependencies"
	@echo "make ui        — launch the Gradio browser UI"
	@echo "make run       — example CLI run (edit paths as needed)"

install:
	python3 -m venv env
	env/bin/pip install -e ".[heic,ui]"

ui:
	env/bin/python app.py

run:
	env/bin/make-collages --input ./images --output ./collages
