# -*- coding: utf-8 -*-
"""Installer for the imio.transmogrifier.cardimporter package."""

from setuptools import find_packages
from setuptools import setup


long_description = (
    open('README.rst').read()
    + '\n' +
    'Contributors\n'
    '============\n'
    + '\n' +
    open('CONTRIBUTORS.rst').read()
    + '\n' +
    open('CHANGES.rst').read()
    + '\n')


setup(
    name='imio.transmogrifier.cardimporter',
    version='0.4.dev0',
    description="Pipeline to convert and import Shop or association into collective.directory.card.",
    long_description=long_description,
    # Get more from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        "Environment :: Web Environment",
        "Framework :: Plone",
        "Framework :: Plone :: 4.3",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
    ],
    keywords='Shop, association, collective.directory.card, transmogrifier, pipeline',
    author='C. Boulanger',
    author_email='christophe.boulanger@imio.be',
    url='http://pypi.python.org/pypi/imio.transmogrifier.cardimporter',
    license='GPL',
    packages=find_packages('src', exclude=['ez_setup']),
    namespace_packages=['imio', 'imio.transmogrifier'],
    package_dir={'': 'src'},
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'five.grok',
        'plone.api',
        'setuptools',
        'collective.geo.behaviour',
        'collective.transmogrifier>=1.4',
        'plone.app.transmogrifier>=1.2',
        'collective.directory>= 0.2.10',
    ],
    extras_require={
        'test': [
            'ecreall.helpers.testing',
            'plone.app.testing',
            'plone.app.robotframework',
        ],
    },
    entry_points="""
    [z3c.autoinclude.plugin]
    target = plone
    """,
)
