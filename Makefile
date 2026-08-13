.PHONY: install ingest label train calibrate economics serve test lint

install:
	pip install -r requirements.txt

ingest:
	python -m src.ingest

label:
	python -m src.labels

train:
	python -m src.models

calibrate:
	python -m src.calibrate

economics:
	python -m src.economics

serve:
	uvicorn api.main:app --reload --port 8000

test:
	pytest tests/ -v

lint:
	python -m py_compile src/*.py api/*.py
