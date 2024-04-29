.PHONY: test
test:
	py.test -vv --doctest-modules --cov=txdir --cov-report term-missing

.PHONY: man
man:
	pandoc README.rst -s -t man -o txdir.1

.PHONY: check
check:
	restview --long-description --strict

.PHONY: lint
lint:
	ruff check .

.PHONY: dist
dist: man lint
	sudo python setup.py bdist_wheel

.PHONY: up
up:
	twine upload dist/`ls dist -rt | tail -1` -u__token__ -p`pass show pypi.org/txdir_api_token`

.PHONY: tag
tag: dist
	$(eval TAGMSG="v$(shell python ./txdir.py -v | cut -d ' ' -f 2)")
	echo $(TAGMSG)
	git tag -s $(TAGMSG) -m"$(TAGMSG)"
	git verify-tag $(TAGMSG)
	git push origin $(TAGMSG) --follow-tags

