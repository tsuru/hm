.PHONY: test test_deps

test: test_deps
	@python -m unittest discover tests
	@flake8 --max-line-length=110 .

test_deps:
	pip install -e .[tests]

coverage: test_deps
	rm -f .coverage
	coverage run --source=. -m unittest discover
	coverage report -m --omit=test\*,run\*.py
