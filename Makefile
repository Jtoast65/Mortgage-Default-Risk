.PHONY: install ingest label features plots train calibrate economics experiments serve test lint

install:
	pip install -r requirements.txt

ingest:
	python -m src.ingest

label:
	python -m src.labels

features:
	python -m src.features

plots:
	python -m src.evaluate

train:
	python -m src.models

calibrate:
	python -m src.calibrate

economics:
	python -m src.economics

# Full model pipeline for both experiments (A = modern, B = crisis) + the regime comparison.
experiments:
	python -m src.evaluate            # vintage default-rate plot
	python -m src.models A && python -m src.models B
	python -m src.calibrate A && python -m src.calibrate B
	python -m src.economics A && python -m src.economics B
	python -m src.evaluate compare
	python -m src.serving             # persist the deployed calibrated-logistic for /score

serve:
	uvicorn api.main:app --reload --port 8000

test:
	pytest tests/ -v

lint:
	python -m py_compile src/*.py api/*.py
