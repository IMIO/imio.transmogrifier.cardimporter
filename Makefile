#!/usr/bin/make
#

.PHONY: test instance cleanall portals

all: test docs

bin/python:
	virtualenv-2.7 .

develop-eggs: bin/python bootstrap.py
	./bin/python bootstrap.py

bin/buildout: develop-eggs

bin/test: versions.cfg buildout.cfg bin/buildout setup.py
	./bin/buildout -Nvt 5
	touch $@

bin/instance: versions.cfg buildout.cfg bin/buildout setup.py
	./bin/buildout -Nvt 5 install instance
	touch $@

instance: bin/instance
	bin/instance fg

test: bin/test
	bin/test

cleanall:
	rm -fr bin develop-eggs downloads eggs parts .installed.cfg devel
