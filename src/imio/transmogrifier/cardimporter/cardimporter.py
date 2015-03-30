from zope.interface import classProvides, implements

from collective.transmogrifier.interfaces import ISection, ISectionBlueprint
# from collective.transmogrifier.utils import defaultMatcher
from collective.geo.behaviour.interfaces import ICoordinates
from plone.app.textfield.value import RichTextValue
from plone import api
from lxml import objectify
import logging
import re
logger = logging.getLogger('collective.directory.migrate')

MIGRATE_CONTAINER_SHOP = 'directory-shop'
MIGRATE_CONTAINER_ASSOCIATION = 'directory-association'


class CardImporterSection(object):
    classProvides(ISectionBlueprint)
    implements(ISection)

    def _setEncoding(self):
        import sys
        stdin, stdout = sys.stdin, sys.stdout
        reload(sys)
        sys.stdin, sys.stdout = stdin, stdout
        sys.setdefaultencoding('utf-8')

    def __init__(self, transmogrifier, name, options, previous):
        self._setEncoding()
        self.previous = previous
        self.context = transmogrifier.context
        self.portal = self.context
        qi_tool = api.portal.get_tool(name='portal_quickinstaller')
        pid = 'collective.directory'
        installed = [p['id'] for p in qi_tool.listInstalledProducts()]
        if pid not in installed:
            setup = api.portal.get_tool(name='portal_setup')
            setup.runAllImportStepsFromProfile('profile-collective.directory:default')
        # Create collective.directory.directory to stock shop categories
        if MIGRATE_CONTAINER_SHOP not in self.portal.keys():
            self.migrate_container_shop = api.content.create(
                type='collective.directory.directory',
                title=MIGRATE_CONTAINER_SHOP,
                container=self.portal
            )
        # Create collective.directory.directory to stock association categories
        if MIGRATE_CONTAINER_ASSOCIATION not in self.portal.keys():
            self.migrate_container_association = api.content.create(
                type='collective.directory.directory',
                title=MIGRATE_CONTAINER_ASSOCIATION,
                container=self.portal
            )

    def __iter__(self):
        # cross the transmogrify structure
        for item in self.previous:
            # we continue to execute loop except as we got a shop or a contact or an association type.
            if not item.has_key('_type') or (not item['_type'] == 'shop' and not item['_type'] == 'Shop' and not item['_type'] == 'Contact' and not item['_type'] == 'association'):
                if not item.has_key('_name'):
                    yield item; continue
            # we find a shop, a contact or an association in the transmogrifier xml structure.
            else:
                # Logo importing?
                #
                #if item.has_key('_name'):
                #    if item['_name'] == 'logo':

                # xml data string contains datas and "category" of an item (shop, association, contact,...).
                try:
                    if '_files' in item:
                        strData = item['_files']['marshall']['data']
                        objData = objectify.fromstring(strData)
                        mItem = migrateItem()
                        if item['_type'] == 'Shop':
                            shop = self.createShop(objData)
                            shop.container = self.migrate_container_shop
                            mItem.migrate(shop)
                        if item['_type'] == 'shop':
                            shop = self.create_shop(objData)
                            shop.container = self.migrate_container_shop
                            mItem.migrate(shop)
                        if item['_type'] == 'association':
                            association = self.createAssociation(objData)
                            association.container = self.migrate_container_association
                            mItem.migrate(association)
                        if item['_type'] == 'Contact':
                            # Contact type hasn't equivalent type in collective.directory.type. It's merge in card object.
                            splitPath = item['_path'].split('/')
                            idCard = splitPath[len(splitPath) - 2]
                            braincard = self.getItemById('collective.directory.card', idCard)
                            if len(braincard) > 0:
                                card = braincard.getObject()
                                contact = self.createContact(objData)
                                mItem.mergeContactInCard(card, contact)
                    yield item
                except Exception:
                    pass

    def _create(self, obj, objData):
        regex = re.compile(r'[\n\r\t]')
        obj.title = regex.sub("", objData.getchildren()[0].text)
        obj.creator = regex.sub("", objData.getchildren()[1].text)
        for cptField in range(0, len(objData.field)):
            currField = objData.field[cptField]
            setattr(obj, currField[cptField].get("name"), regex.sub("", currField[cptField].text))
        return obj

    # create a simple contact object thank to objectify objData (come from xml).
    def createContact(self, objData):
        currContact = contact()
        currContact = self._create(currContact, objData)
        return currContact

    # create a simple association object thank to objectify objData (come from xml).
    def createAssociation(self, objData):
        currAssociation = association()
        currAssociation = self._create(currAssociation, objData)
        return currAssociation

    # create a simple Shop (S MAJ) object thank to objectify objData (come from xml).
    def createShop(self, objData):
        currShop = Shop()
        currShop = self._create(currShop, objData)
        return currShop

    # create a simple shop object thank to objectify objData (come from xml).
    def create_shop(self, objData):
        currShop = shop()
        currShop = self._create(currShop, objData)
        return currShop

    def getItemById(self, portal_type, id):
        catalog = api.portal.get_tool(name="portal_catalog")
        brains = catalog.searchResults({'portal_type': portal_type, 'id': id})
        retour = None
        for brain in brains:
            retour = brain
        return retour


class migrateItem:
    # Creation of a new category or use an already existant category to create in a new card.
    def migrate(self, item):
        try:
            if isinstance(item, shop) or isinstance(item, association) or isinstance(item, Shop):
                # case Shop (S majuscule => plone 2.55) , no category property
                migrate_category = None
                if hasattr(item, "shopType"):
                    category = item.shopType
                    regex = re.compile(r'[\n\r\t]')
                    category = regex.sub("", category)
                    setattr(item, "category", category)
                if hasattr(item, "category"):
                    category = item.category
                    if str(category) not in item.container.keys():
                        # creating new category in Plone in collective.directory.directory "MIGRATE_CONTAINER_ASSOCIATION"
                        migrate_category = api.content.create(
                            type='collective.directory.category',
                            title=item.category,
                            id=item.category,
                            container=item.container
                        )
                        api.content.transition(obj=migrate_category, transition='publish_and_hide')
                    else:
                        # Find category with this ID so we don't create it but we get it.
                        migrate_category = self.getCategoryWrapperFromCatalog(item.category)
                    item.container = migrate_category
                    if str(item.id) not in item.container.keys():
                        # create card from an typed item.
                        migrate_card = self._migrateToCard(item)
                        if migrate_card is not None:
                            api.content.transition(obj=migrate_card, transition='publish_and_hide')
        except:
            import ipdb
            ipdb.set_trace()

    # create a card
    # shop : contains shop informations to migrate into card.
    # category : good collective.directory.category to stock card.
    def _migrateToCard(self, item):
        description = ''
        phone = hasattr(item, 'phone') and item.phone or None
        city = hasattr(item, 'commune') and item.commune or None
        if isinstance(item, association):
            if hasattr(item, 'asbl') and item.asbl == 'True':
                description = "asbl "
        if isinstance(item, Shop):
            phone = hasattr(item, 'phone1') and item.phone1 or None
            city = hasattr(item, 'city') and item.city or None
        coord = None
        card = None
        try:
            if hasattr(item, 'Coordinates'):
                lat, lon = item.Coordinates.split('|')
                coord = u"POINT({0} {1})".format(lon, lat)
            content = "{0} <br/> {1}".format((hasattr(item, 'presentation') and " " + item.presentation or ''),
                                            (hasattr(item, 'opening_hours') and item.opening_hours or ''))
            content = RichTextValue(unicode(content, 'utf8'))
            description = "{0} {1}".format(description, hasattr(item, 'description') and item.description or '')
            card = api.content.create(
                type='collective.directory.card',
                title=item.title,
                description=description,
                content=content,
                city=city,
                address=hasattr(item, 'street') and item.street or None,
                zip_code=hasattr(item, 'zip') and int(item.zip) or None,
                phone=phone,
                mobile_phone=hasattr(item, 'mobile') and item.mobile or None,
                fax=hasattr(item, 'fax') and item.fax or None,
                email=hasattr(item, 'email') and item.email or None,
                website=hasattr(item, 'websiteurl') and item.websiteurl or None,
                container=item.container
            )
            ICoordinates(card).coordinates = coord
            return card
        except:
            logger.warn("{} not created : item = {}".format(str(item.id), item.container.getPath()))

    def getCategoryWrapperFromCatalog(self, currCategory):
        catalog = api.portal.get_tool(name="portal_catalog")
        brains = catalog.searchResults({'portal_type': 'collective.directory.category', 'id': currCategory})
        retour = None
        for brain in brains:
            retour = brain
        return retour.getObject()

    def mergeContactInCard(self, card, contact):
        content = card.content.output + "<br /> {0} {1}".format(contact.firstname, contact.lastname)
        content = RichTextValue(unicode(content, 'utf8'))
        card.content = content


class obj:
    _title = None
    _creator = None

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


class association(obj):
    _container = None

    @property
    def container(self):
        return self._container

    @container.setter
    def container(self, container):
        self._container = container


class Shop(obj):
    _container = None

    @property
    def container(self):
        return self._container

    @container.setter
    def container(self, container):
        self._container = container


class shop(obj):
    _container = None

    @property
    def container(self):
        return self._container

    @container.setter
    def container(self, container):
        self._container = container


class contact(obj):
    def __init__(self, ):
        pass
    