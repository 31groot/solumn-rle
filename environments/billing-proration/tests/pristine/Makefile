PYTHON ?= python3

.PHONY: ci lint test

ci: lint test

lint:
	$(PYTHON) -m compileall -q plans.py calendar_utils.py proration.py invoice.py

test:
	$(PYTHON) -m pytest -q tests_visible
