#!/usr/bin/make
#
all: run
VERSION=`cat version.txt`
#BUILD_NUMBER := debug1

bootstrap.py:
	wget http://downloads.buildout.org/2/bootstrap.py

buildout.cfg:
	ln -fs dev.cfg buildout.cfg
	#ln -fs prod.cfg buildout.cfg

bin/python:
	virtualenv-2.7 --no-site-packages .

bin/buildout: bin/python buildout.cfg bootstrap.py
	./bin/python bootstrap.py

.PHONY: buildout
buildout: bin/buildout
	bin/buildout -t 7

.PHONY: run
run: buildout
	bin/instance fg

.PHONY: cleanall
cleanall:
	rm -fr develop-eggs downloads eggs parts .installed.cfg lib include bin .mr.developer.cfg
