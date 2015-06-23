from zope.interface import classProvides, implements

from collective.transmogrifier.interfaces import ISection, ISectionBlueprint
from collective.geo.behaviour.interfaces import ICoordinates
from plone import api
from lxml import objectify
import logging
logger = logging.getLogger('collective.directory.migrate')

MIGRATE_CONTAINER_CARTES = 'directory-cartes'


class TTGoogleMapMarkerToCardSection(object):
    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        # utf-8 system
        import sys
        stdin, stdout = sys.stdin, sys.stdout
        reload(sys)
        sys.stdin, sys.stdout = stdin, stdout
        sys.setdefaultencoding('utf-8')
        self.previous = previous
        self.context = transmogrifier.context
        self.portal = self.context
        # is portal_quickinstaller installed? If not, install it!
        qi_tool = api.portal.get_tool(name='portal_quickinstaller')
        pid = 'collective.directory'
        installed = [p['id'] for p in qi_tool.listInstalledProducts()]
        if pid not in installed:
            setup = api.portal.get_tool(name='portal_setup')
            setup.runAllImportStepsFromProfile('profile-collective.directory:default')
        # Create collective.directory.directory to stock google maps categories
        if MIGRATE_CONTAINER_CARTES not in self.portal.keys():
            self.migrate_container_cartes = api.content.create(
                type='collective.directory.directory',
                title=MIGRATE_CONTAINER_CARTES,
                container=self.portal
            )

    def __iter__(self):
        # cross the transmogrify structure
        for item in self.previous:
            # we continue to execute loop except as we got a shop or a contact or an association type.
            if '_type' not in item or (not item['_type'] == 'TTGoogleMapMarker'):
                if '_name' not in item:
                    yield item
                    continue
            # we find a TTGoogleMapMarker
            else:
                if item['_type'] == 'TTGoogleMapMarker':
                    # First, get a collective.directory.category from the path string.
                    categoryContainer = self.getCategory(item['_path'])
                    # We try to create the collective.directory.card in the category
                    try:
                        strData = item['_files']['marshall']['data']
                        # get a simple object representation of the xml string.
                        objData = objectify.fromstring(strData)
                        currMapMarker = self.createTTGoogleMapMarker(objData, categoryContainer)
                        # we create the card.
                        self.createCardFromTTGoogleMapMarker(currMapMarker)
                    except Exception:
                        pass
            yield item

    # Thans to path we get the collective.directory.Category to stock the card.
    # if the collective.directory.Category not exist, we create it.
    def getCategory(self, path):
        splitPath = path.split('/')
        idCategory = splitPath[len(splitPath) - 2]
        category = None
        if idCategory not in self.migrate_container_cartes.keys():
            category = api.content.create(
                type='collective.directory.category',
                title=idCategory,
                id=idCategory,
                container=self.migrate_container_cartes
            )
        else:
            category = self.getCategoryWrapperFromCatalog(idCategory)
        return category

    # Get Category from catalog.
    def getCategoryWrapperFromCatalog(self, currCategory):
        catalog = api.portal.get_tool(name="portal_catalog")
        brains = catalog.searchResults({'portal_type': 'collective.directory.category', 'id': currCategory})
        retour = None
        for brain in brains:
            retour = brain
        return retour.getObject()

    # create a simple ttGoogleMapMarker object thank to objectify objData (come from xml).
    def createTTGoogleMapMarker(self, objData, container):
        ttGoogleMapMarker = obj()
        ttGoogleMapMarker.title = objData.getchildren()[0]
        ttGoogleMapMarker.creator = objData.getchildren()[1]
        ttGoogleMapMarker.container = container
        # add dynamicly other fields to our ttGoogleMapMarker object.
        for cptField in range(0, len(objData.field)):
            currField = objData.field[cptField]
            setattr(ttGoogleMapMarker, currField[cptField].get("name"), currField[cptField])
        return ttGoogleMapMarker

    # create a card
    def createCardFromTTGoogleMapMarker(self, ttGoogleMapMarker):
        coord = None
        try:
            card = api.content.create(
                type='collective.directory.card',
                title=ttGoogleMapMarker.title.text,
                description=hasattr(ttGoogleMapMarker, 'description') and ttGoogleMapMarker.description.text or '',
                container=ttGoogleMapMarker.container
            )
            # look if ttGoogleMapMarker has coordinates
            if hasattr(ttGoogleMapMarker, 'Coordinates'):
                lat, lon = ttGoogleMapMarker.Coordinates.text.split('|')
                coord = u"POINT({0} {1})".format(lon, lat)
            else:
                logger.warn("{} has no coordinates.".format(card.id))
            ICoordinates(card).coordinates = coord
            # Change new card worflow and publish it.
            api.content.transition(obj=card, transition='publish_and_hide')
        except:
            logger.warn("{} not created : card = {}".format(str(card.id), card.getPath()))


class obj:
    _title = None
    _creator = None
    _container = None

    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, title):
        self._title = title

    @property
    def creator(self):
        return self._creator

    @creator.setter
    def creator(self, creator):
        self._creator = creator

    @property
    def container(self):
        return self._container

    @container.setter
    def container(self, container):
        self._container = container
