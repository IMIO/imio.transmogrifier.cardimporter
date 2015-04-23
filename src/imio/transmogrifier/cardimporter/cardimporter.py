#!/usr/bin/env python
# -*- coding: utf-8 -*-
from zope.interface import classProvides, implements
from collective.transmogrifier.interfaces import ISection, ISectionBlueprint
from collective.geo.behaviour.interfaces import ICoordinates
from plone.app.textfield.value import RichTextValue
from plone.namedfile.file import NamedBlobImage
from plone import api
from lxml import objectify
import unicodedata
import logging
import re
logger = logging.getLogger('collective.directory.migrate')

MIGRATE_CONTAINER_SHOP = 'directory-shop'
MIGRATE_CONTAINER_ASSOCIATION = 'directory-association'
MIGRATE_CONTAINER_HEBERGEMENT = 'directory-hebergement'
MIGRATE_CONTAINER_CLUBSPORTIF = 'directory-clubs-sportifs'


class CardImporterSection(object):
    classProvides(ISectionBlueprint)
    implements(ISection)
    """
    Blueprint to import shop, Shop, association or Association into Card.
    """

    def _setEncoding(self):
        import sys
        stdin, stdout = sys.stdin, sys.stdout
        reload(sys)
        sys.stdin, sys.stdout = stdin, stdout
        sys.setdefaultencoding('utf-8')

    def __init__(self, transmogrifier, name, options, previous):
        """
        Initialize shop and association. Building two default directory.
        """
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
        # Create collective.directory.directory to stock hebergement categories
        if MIGRATE_CONTAINER_HEBERGEMENT not in self.portal.keys():
            self.migrate_container_hebergement = api.content.create(
                type='collective.directory.directory',
                title=MIGRATE_CONTAINER_HEBERGEMENT,
                container=self.portal
            )
        # Create collective.directory.directory to stock clubs-sportifs categories
        if MIGRATE_CONTAINER_CLUBSPORTIF not in self.portal.keys():
            self.migrate_container_clubsSportifs = api.content.create(
                type='collective.directory.directory',
                title=MIGRATE_CONTAINER_CLUBSPORTIF,
                container=self.portal
            )

    def __iter__(self):
        """
        Iterate transmogrifier structure
        """
        # cross the transmogrify structure
        for item in self.previous:
            currItem = Item.create(item, {'migrate_container_association': self.migrate_container_association,
                                          'migrate_container_shop': self.migrate_container_shop,
                                          'migrate_container_hebergement': self.migrate_container_hebergement,
                                          'migrate_container_clubsSportifs': self.migrate_container_clubsSportifs
                                          }
                                   )
            if currItem is None or not currItem.is_valid():
                yield item
                continue
            else:
                try:
                    # Item migration (register in portal_catalog)
                    currItem.migrate()
                    yield item
                except Exception:
                    pass


class Item:
    __objData = None
    __xmlitem = None
    __type = None
    __mImportContext = None
    __files = None
    __path = None
    __availableItem = ['clubs-sportifs', 'artisanat', 'hebergement', 'produits-du-terroir'
                       'commercants', 'shop', 'Shop', 'Contact',
                       'association', 'Association', 'associations']

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

    @property
    def xmlitem(self):
        return self.__xmlitem

    @xmlitem.setter
    def xmlitem(self, xmlitem):
        self.__xmlitem = xmlitem

    @property
    def type(self):
        if '_type' in self.xmlitem:
            self.__type = self.xmlitem['_type']
        return self.__type

    @property
    def files(self):
        if '_files' in self.xmlitem:
            self.__files = self.xmlitem['_files']
        return self.__files

    @property
    def path(self):
        if '_path' in self.xmlitem:
            self.__path = self.xmlitem['_path']
        return self.__path

    def __init__(self, xmlitem):
        self.xmlitem = xmlitem
        if '_files' in self.xmlitem:
            self.Files = self.xmlitem['_files']
            strData = self.Files['marshall']['data']
            self.objData = objectify.fromstring(strData)
            self.__create()

    def __create(self):
        """
        Create a typed object from an objectofy object
        typedObject : Typed object
        objData : Objectify object
        """
        regex = re.compile(r'[\n\r\t]')
        self.title = regex.sub("", self.objData.getchildren()[0].text)
        self.creator = regex.sub("", self.objData.getchildren()[1].text)
        for cptField in range(0, len(self.objData.field)):
            currField = self.objData.field[cptField]
            setattr(self, currField[cptField].get("name"), regex.sub("", currField[cptField].text))

    @staticmethod
    def create(xmlitem, dicContainer):
        item = None
        if '_type' in xmlitem:
            currtype = xmlitem['_type']
            # , 'artisanat', 'hebergement', 'produits-du-terroir'
            if currtype == 'clubs-sportifs':
                item = ClubsSportifs(xmlitem)
                item.container = dicContainer['migrate_container_clubsSportifs']
            if currtype == 'commercants':
                item = commercants(xmlitem)
                item.container = dicContainer['migrate_container_shop']
            if currtype == 'Shop' or currtype == 'shop':
                item = Shop(xmlitem)
                item.container = dicContainer['migrate_container_shop']
            if currtype == 'association' or currtype == 'Association':
                item = Association(xmlitem)
                item.container = dicContainer['migrate_container_association']
            if currtype == 'associations':
                item = Associations(xmlitem)
                item.container = dicContainer['migrate_container_association']
            if currtype == 'hebergement':
                item = Hebergement(xmlitem)
                item.container = dicContainer['migrate_container_hebergement']
            if currtype == 'Contact':
                item = Contact(xmlitem)
        return item

    # Creation of a new category or use an already existant category to create in a new card.
    def migrate(self):
        try:
            migrate_category = None
            regex = re.compile(r'[\n\r\t]')
            if not hasattr(self, "category"):
                setattr(self, "category", "get-no-default-category")
            category = regex.sub("", self.category)
            setattr(self, "category", category)
            if self._remove_accents(self.category) not in self.container.keys():
                # creating new category in Plone in collective.directory.directory "MIGRATE_CONTAINER_ASSOCIATION"
                migrate_category = api.content.create(
                    type='collective.directory.category',
                    title=self.category,
                    id=self._remove_accents(self.category),
                    container=self.container
                )
                api.content.transition(obj=migrate_category, transition='publish_and_hide')

            else:
                # Find category with this ID so we don't create it but we get it.
                migrate_category = self._getCategoryWrapperFromCatalog(self._remove_accents(self.category))
            self.category = migrate_category
            # really keep this test?
            if str(self.id) not in self.category.keys():
                migrate_card = self._migrate_to_card()
                if migrate_card is not None:
                    api.content.transition(obj=migrate_card, transition='publish_and_hide')
        except:
            import ipdb
            ipdb.set_trace()

    def _migrate_to_card(self):
        """
        Create new card into catalog.
        """
        #import ipdb
        #ipdb.set_trace()
        coord = None
        soustitre = ''
        description = ''
        website = hasattr(self, 'websiteurl') and self.websiteurl or hasattr(self, 'url') and self.url or None
        city = hasattr(self, 'commune') and self.commune or hasattr(self, 'city') and self.city or None
        phone = hasattr(self, 'phone') and self.phone or hasattr(self, 'phone1') and self.phone1 or None
        horaire = hasattr(self, 'opening_hours') and self.opening_hours or hasattr(self, 'schedule') and self.schedule or ''
        adresse = hasattr(self, 'street') and self.street or None
        codePostal = hasattr(self, 'zip') and int(self.zip) or None
        gsm = hasattr(self, 'mobile') and self.mobile or None
        faxe = hasattr(self, 'fax') and self.fax or None
        mail = hasattr(self, 'email') and self.email or None
        if hasattr(self, 'surname_president'):
            soustitre += self.surname_president
        if hasattr(self, 'firstname_president'):
            soustitre += ' ' + self.firstname_president
        if isinstance(self, commercants) or isinstance(self, Associations):
            if hasattr(self, 'lastname'):
                soustitre += self.lastname
            if hasattr(self, 'firstname'):
                soustitre += ' ' + self.firstname
        if isinstance(self, Association):
            if hasattr(self, 'asbl') and self.asbl == 'True':
                description = "asbl "
        if isinstance(self, Shop):
            soustitre += hasattr(self, 'shopOwner') and self.shopOwner or ''
            city = hasattr(self, 'city') and self.city or None
        try:
            if hasattr(self, 'Coordinates'):
                lat, lon = self.Coordinates.split('|')
                coord = u"POINT({0} {1})".format(lon, lat)
            content = "{0} <br/> {1} <br/> {2}".format((hasattr(self, 'presentation') and " " + self.presentation or ''),
                                                        horaire, (hasattr(self, 'information') and self.information or ''))
            content = RichTextValue(unicode(content, 'utf8'))
            description = "{0} {1}".format(description, hasattr(self, 'description') and self.description or '')
            image = NamedBlobImage()
            if self.logo is not None:
                image.data = self.logo
            else:
                image = None
            card = api.content.create(
                type='collective.directory.card',
                title=self.title,
                subtitle=soustitre,
                description=description,
                content=content,
                city=city,
                address=adresse,
                zip_code=codePostal,
                phone=phone,
                photo=image,
                mobile_phone=gsm,
                fax=faxe,
                email=mail,
                website=website,
                container=self.category
            )
            ICoordinates(card).coordinates = coord
            return card
        except:
            import ipdb
            ipdb.set_trace()
            # logger.warn("{} not created : item = {}".format(str(self.id), self.container.getPath()))

    def is_valid(self):
        retour = True
        if self.type is None:
            retour = False
        if self.type not in self.__availableItem:
            retour = False
        return retour

    def _remove_accents(self, input_str):
        """
        Remove accent from input string input_str
        """
        if type(input_str) is unicode:
            nkfd_form = unicodedata.normalize('NFKD', input_str)
            input_str = nkfd_form.encode('ASCII', 'ignore')
        return input_str

    def _getCategoryWrapperFromCatalog(self, currCategory):
        catalog = api.portal.get_tool(name="portal_catalog")
        brains = catalog.searchResults({'portal_type': 'collective.directory.category', 'id': currCategory})
        retour = None
        for brain in brains:
            retour = brain
        return retour.getObject()

    def _merge_in_existant_card(self, card):
        """
        Merge contact informations into card.
        """
        firstname = hasattr(self, 'firstname') and self.firstname or ""
        lastname = hasattr(self, 'lastname') and self.lastname or ""
        content = card.content.output + "<br /> {0} {1}".format(firstname, lastname)
        content = RichTextValue(unicode(content, 'utf8'))
        card.content = content

    def _get_item_by_id(self, portal_type, id):
        """
        Get object thank to its id.
        """
        catalog = api.portal.get_tool(name="portal_catalog")
        brains = catalog.searchResults({'portal_type': portal_type, 'id': id})
        retour = None
        for brain in brains:
            retour = brain
        return retour


class Association(Item):
    _container = None
    _logoName = None
    _logo = None

    @property
    def container(self):
        return self._container

    @container.setter
    def container(self, container):
        self._container = container

    @property
    def logoName(self):
        return self._logoName

    @logoName.setter
    def logoName(self, container):
        self._logoName = container

    @property
    def logo(self):
        return self._logo

    @logo.setter
    def logo(self, container):
        self._logo = container

    def __init__(self, xmlitem):
        Item.__init__(self, xmlitem)

    def __create(self):
        Item.__create(self)
        # self.container = self.migrate_container_association
        if 'file-fields' in self.files:
            xmlLogoString = self.files['file-fields']['data']
            deb = self.files['file-fields']['data'].index('<filename>\n') + len('<filename>\n')
            end = self.files['file-fields']['data'].index('</filename>')
            self.logoName = xmlLogoString[deb:end].strip(" ").replace("\n", "").replace("&amp;", "&")
            self.logo = self.files[self.logoName]['data']

    def migrate(self):
        try:
            Item.migrate(self)
        except Exception:
            import ipdb
            ipdb.set_trace()


class Associations(Association):
    '''
    For "associations" objets (ver.4.3.2)
    '''
    def __init__(self, xmlitem):
        Association.__init__(self, xmlitem)


class Hebergement(Item):
    '''
    id
    Coordinates
    category
    lastname (firstname option)
    street
    zip
    commune
    mobile
    email
    presentation
    '''
    _container = None
    _logoName = None
    _logo = None

    @property
    def container(self):
        return self._container

    @container.setter
    def container(self, container):
        self._container = container

    @property
    def logoName(self):
        return self._logoName

    @logoName.setter
    def logoName(self, container):
        self._logoName = container

    @property
    def logo(self):
        return self._logo

    @logo.setter
    def logo(self, container):
        self._logo = container

    def __init__(self, xmlitem):
        Item.__init__(self, xmlitem)

    def __create(self):
        Item.__create(self)
        # self.container = self.migrate_container_association
        if 'file-fields' in self.files:
            xmlLogoString = self.files['file-fields']['data']
            deb = self.files['file-fields']['data'].index('<filename>\n') + len('<filename>\n')
            end = self.files['file-fields']['data'].index('</filename>')
            self.logoName = xmlLogoString[deb:end].strip(" ").replace("\n", "").replace("&amp;", "&")
            self.logo = self.files[self.logoName]['data']

    def migrate(self):
        try:
            Item.migrate(self)
        except Exception:
            import ipdb
            ipdb.set_trace()


class ClubsSportifs(Item):
    _container = None
    _logoName = None
    _logo = None

    @property
    def container(self):
        return self._container

    @container.setter
    def container(self, container):
        self._container = container

    @property
    def logoName(self):
        return self._logoName

    @logoName.setter
    def logoName(self, container):
        self._logoName = container

    @property
    def logo(self):
        return self._logo

    @logo.setter
    def logo(self, container):
        self._logo = container

    def __init__(self, xmlitem):
        Item.__init__(self, xmlitem)

    def __create(self):
        Item.__create(self)
        # self.container = self.migrate_container_shop
        if 'file-fields' in self.files:
            xmlLogoString = self.files['file-fields']['data']
            deb = self.files['file-fields']['data'].index('<filename>\n') + len('<filename>\n')
            end = self.files['file-fields']['data'].index('</filename>')
            self.logoName = xmlLogoString[deb:end].strip(" ").replace("\n", "").replace("&amp;", "&")
            self.logo = self.files[self.logoName]['data']

    def migrate(self):
        try:
            Item.migrate(self)
        except Exception:
            import ipdb
            ipdb.set_trace()


class Shop(Item):
    _container = None
    _logoName = None
    _logo = None

    @property
    def container(self):
        return self._container

    @container.setter
    def container(self, container):
        self._container = container

    @property
    def logoName(self):
        return self._logoName

    @logoName.setter
    def logoName(self, container):
        self._logoName = container

    @property
    def logo(self):
        return self._logo

    @logo.setter
    def logo(self, container):
        self._logo = container

    def __init__(self, xmlitem):
        Item.__init__(self, xmlitem)

    def __create(self):
        Item.__create(self)
        # self.container = self.migrate_container_shop
        if 'file-fields' in self.files:
            xmlLogoString = self.files['file-fields']['data']
            deb = self.files['file-fields']['data'].index('<filename>\n') + len('<filename>\n')
            end = self.files['file-fields']['data'].index('</filename>')
            self.logoName = xmlLogoString[deb:end].strip(" ").replace("\n", "").replace("&amp;", "&")
            self.logo = self.files[self.logoName]['data']

    def migrate(self):
        try:
            Item.migrate(self)
        except Exception:
            import ipdb
            ipdb.set_trace()


class Artisanat(Shop):
    def __init__(self, xmlitem):
        Shop.__init__(self, xmlitem)


class ProduitsDuTerroir(Shop):
    def __init__(self, xmlitem):
        Shop.__init__(self, xmlitem)


class commercants(Shop):
    def __init__(self, xmlitem):
        Shop.__init__(self, xmlitem)


class Contact(Item):
    def __init__(self, xmlitem):
        Item.__init__(self, xmlitem)

    def __create(self):
        Item.__create(self)

    def migrate(self):
        """
        Contact type hasn't equivalent type in collective.directory.type. It's merge in card.
        """
        # split fullPath to the contact.
        splitPath = self.path.split('/')
        # get idCard from the path
        idCard = splitPath[len(splitPath) - 2]
        try:
            # Try to get Card thank to idCard.
            braincard = self._get_item_by_id('collective.directory.card', idCard)
            if braincard is not None and len(braincard) > 0:
                card = braincard.getObject()
                self._merge_in_existant_card(card)
        except Exception:
            import ipdb
            ipdb.set_trace()
