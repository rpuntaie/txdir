.PHONY: man test up check

test:
	py.test -vv --doctest-modules --cov=txdir --cov-report term-missing

man:
	pandoc README.rst -s -t man -o txdir.1

up:
	sudo python setup.py bdist_wheel
	twine upload ./dist/*.whl

check:
	restview --long-description --strict

