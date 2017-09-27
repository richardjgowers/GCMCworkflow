init:
	pip install -U -r requirements.txt .

test:
	pytest

.PHONY: init test
