# -*- coding: utf-8 -*-
"""Setup/installation tests for this package."""

from imio.transmogrifier.cardimporter.testing import IntegrationTestCase
from plone import api


class TestInstall(IntegrationTestCase):
    """Test installation of imio.transmogrifier.cardimporter into Plone."""

    def setUp(self):
        """Custom shared utility setup for tests."""
        self.portal = self.layer['portal']
        self.installer = api.portal.get_tool('portal_quickinstaller')

    def test_product_installed(self):
        """Test if imio.transmogrifier.cardimporter is installed with portal_quickinstaller."""
        self.assertTrue(self.installer.isProductInstalled('imio.transmogrifier.cardimporter'))

    def test_uninstall(self):
        """Test if imio.transmogrifier.cardimporter is cleanly uninstalled."""
        self.installer.uninstallProducts(['imio.transmogrifier.cardimporter'])
        self.assertFalse(self.installer.isProductInstalled('imio.transmogrifier.cardimporter'))

    # browserlayer.xml
    def test_browserlayer(self):
        """Test that IImioTransmogrifierCardimporterLayer is registered."""
        from imio.transmogrifier.cardimporter.interfaces import IImioTransmogrifierCardimporterLayer
        from plone.browserlayer import utils
        self.assertIn(IImioTransmogrifierCardimporterLayer, utils.registered_layers())
