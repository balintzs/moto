SHELL := /bin/bash

init:
	@python setup.py develop
	@pip install -r requirements.txt

test:
	rm -f .coverage
	rm -rf cover
	@pip install -r requirements-dev.txt
	@nosetests -sv --with-coverage --cover-html ./tests/

publish:
	python setup.py sdist bdist_wheel upload
