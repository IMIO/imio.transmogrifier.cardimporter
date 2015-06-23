#!/usr/bin/env python
# -*- coding: utf-8 -*-
from collective.geo.behaviour.interfaces import ICoordinates
from collective.transmogrifier.interfaces import ISection, ISectionBlueprint
from lxml import objectify
from plone.app.textfield.value import RichTextValue
from plone.namedfile.file import NamedBlobImage
from plone import api
from zope.interface import classProvides, implements
import logging
import re
import unicodedata

logger = logging.getLogger('collective.directory.migrate')

MIGRATE_CONTAINER_SHOP = 'directory-shop'
MIGRATE_CONTAINER_ASSOCIATION = 'directory-association'
MIGRATE_CONTAINER_HEBERGEMENT = 'directory-hebergement'
MIGRATE_CONTAINER_CLUBSPORTIF = 'directory-clubs-sportifs'


class CardImporterSection(object):
    """
    Blueprint to import shop, Shop, association or Association into Card.
    """
    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        """
        Initialize shop and association. Building two default directory.
        """
        self._set_encoding()
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
            curr_item = Item.create(item, {'migrate_container_association': self.migrate_container_association,
                                           'migrate_container_shop': self.migrate_container_shop,
                                           'migrate_container_hebergement': self.migrate_container_hebergement,
                                           'migrate_container_clubsSportifs': self.migrate_container_clubsSportifs
                                          }
                                   )
            if curr_item is None or not curr_item.is_valid():
                yield item
                continue
            else:
                try:
                    # Item migration (register in portal_catalog)
                    curr_item.migrate()
                    yield item
                except Exception:
                    pass

    def _set_encoding(self):
        import sys
        stdin, stdout = sys.stdin, sys.stdout
        reload(sys)
        sys.stdin, sys.stdout = stdin, stdout
        sys.setdefaultencoding('utf-8')


class Item:
    _obj_data = None
    _xml_item = None
    _type = None
    _files = None
    _path = None
    _available_item = ['clubs-sportifs', 'artisanat', 'hebergement', 'produits-du-terroir',
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
    def xml_item(self):
        return self._xml_item

    @xml_item.setter
    def xml_item(self, xml_item):
        self._xml_item = xml_item

    @property
    def type(self):
        if '_type' in self.xml_item:
            self._type = self.xml_item['_type']
        return self._type

    @property
    def files(self):
        if '_files' in self.xml_item:
            self._files = self.xml_item['_files']
        return self._files

    @property
    def path(self):
        if '_path' in self.xml_item:
            self._path = self.xml_item['_path']
        return self._path

    def __init__(self, xml_item):
        self.xml_item = xml_item
        if '_files' in self.xml_item:
            self.Files = self.xml_item['_files']
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
        for cpt_field in range(0, len(self.objData.field)):
            current_field = self.objData.field[cpt_field]
            setattr(self, current_field[cpt_field].get("name"), regex.sub("", current_field[cpt_field].text))

    @staticmethod
    def create(xml_item, dic_container):
        item = None
        if '_type' in xml_item:
            current_type = xml_item['_type']
            # , 'artisanat', 'hebergement', 'produits-du-terroir'
            if current_type == 'clubs-sportifs':
                item = ClubsSportifs(xml_item)
                item.container = dic_container['migrate_container_clubsSportifs']
            if current_type == 'commercants':
                item = commercants(xml_item)
                item.container = dic_container['migrate_container_shop']
            if current_type == 'Shop' or current_type == 'shop':
                item = Shop(xml_item)
                item.container = dic_container['migrate_container_shop']
            if current_type == 'association' or current_type == 'Association':
                item = Association(xml_item)
                item.container = dic_container['migrate_container_association']
            if current_type == 'associations':
                item = Associations(xml_item)
                item.container = dic_container['migrate_container_association']
            if current_type == 'hebergement':
                item = Hebergement(xml_item)
                item.container = dic_container['migrate_container_hebergement']
            if current_type == 'Contact':
                item = Contact(xml_item)
        return item

    # Creation of a new category or use an already existant category to create in a new card.
    def migrate(self):
        try:
            migrate_category = None
            regex = re.compile(r'[\n\r\t]')
            # if item has no category. Set a default category.
            if not hasattr(self, "category"):
                if hasattr(self, "shopType"):
                    setattr(self, "category", self.shopType)
                elif hasattr(self, "association_type"):
                    setattr(self, "category", self.association_type)
                else:
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
                migrate_category = self._get_category_from_catalog(self._remove_accents(self.category))
            self.category = migrate_category
            # really keep this test?
            # if str(self.id) not in self.category.keys():
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
        coord = None
        sous_titre = ''
        description = ''
        website = hasattr(self, 'websiteurl') and self.websiteurl or hasattr(self, 'url') and self.url or None
        city = hasattr(self, 'commune') and self.commune or hasattr(self, 'city') and self.city or None
        phone = hasattr(self, 'phone') and self.phone or hasattr(self, 'phone1') and self.phone1 or None
        horaire = hasattr(self, 'opening_hours') and self.opening_hours or hasattr(self, 'schedule') and self.schedule or ''
        adresse = hasattr(self, 'street') and self.street or None
        code_postal = hasattr(self, 'zip') and int(self.zip) or None
        gsm = hasattr(self, 'mobile') and self.mobile or None
        faxe = hasattr(self, 'fax') and self.fax or None
        mail = hasattr(self, 'email') and self.email or None
        if hasattr(self, 'surname_president'):
            sous_titre += self.surname_president
        if hasattr(self, 'firstname_president'):
            sous_titre += ' ' + self.firstname_president
        if isinstance(self, commercants) or isinstance(self, Associations):
            if hasattr(self, 'lastname'):
                sous_titre += self.lastname
            if hasattr(self, 'firstname'):
                sous_titre += ' ' + self.firstname
        if isinstance(self, Association):
            if hasattr(self, 'asbl') and self.asbl == 'True':
                description = "asbl "
        if isinstance(self, Shop):
            sous_titre += hasattr(self, 'shopOwner') and self.shopOwner or ''
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
                subtitle=sous_titre,
                description=description,
                content=content,
                city=city,
                address=adresse,
                zip_code=code_postal,
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
        if self.type is None or self.type not in self._available_item:
            retour = False
        return retour

    def _remove_accents(self, input_string):
        """
        Remove accent from input string input_str
        """
        if type(input_string) is unicode:
            nkfd_form = unicodedata.normalize('NFKD', input_string)
            input_string = nkfd_form.encode('ASCII', 'ignore')
        return input_string

    def _get_category_from_catalog(self, current_category):
        catalog = api.portal.get_tool(name="portal_catalog")
        brains = catalog.searchResults({'portal_type': 'collective.directory.category', 'id': current_category})
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
    _logo_name = None
    _logo = None

    @property
    def container(self):
        return self._container

    @container.setter
    def container(self, container):
        self._container = container

    @property
    def logo_name(self):
        return self._logo_name

    @logo_name.setter
    def logo_name(self, container):
        self._logo_name = container

    @property
    def logo(self):
        return self._logo

    @logo.setter
    def logo(self, container):
        self._logo = container

    def __init__(self, xml_item):
        Item.__init__(self, xml_item)

    def __create(self):
        Item.__create(self)
        # self.container = self.migrate_container_association
        if 'file-fields' in self.files:
            xml_string_logo = self.files['file-fields']['data']
            deb = self.files['file-fields']['data'].index('<filename>\n') + len('<filename>\n')
            end = self.files['file-fields']['data'].index('</filename>')
            self.logo_name = xml_string_logo[deb:end].strip(" ").replace("\n", "").replace("&amp;", "&")
            self.logo = self.files[self.logo_name]['data']

    def migrate(self):
        try:
            Item.migrate(self)
        except Exception:
            import ipdb
            ipdb.set_trace()


class Associations(Association):
    """
    For "associations" objets (ver.4.3.2)
    """
    def __init__(self, xml_item):
        Association.__init__(self, xml_item)


class Hebergement(Item):
    """
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
    """
    _container = None
    _logo_name = None
    _logo = None

    @property
    def container(self):
        return self._container

    @container.setter
    def container(self, container):
        self._container = container

    @property
    def logo_name(self):
        return self._logo_name

    @logo_name.setter
    def logo_name(self, container):
        self._logo_name = container

    @property
    def logo(self):
        return self._logo

    @logo.setter
    def logo(self, container):
        self._logo = container

    def __init__(self, xml_item):
        Item.__init__(self, xml_item)

    def __create(self):
        Item.__create(self)
        # self.container = self.migrate_container_association
        if 'file-fields' in self.files:
            xml_string_logo = self.files['file-fields']['data']
            deb = self.files['file-fields']['data'].index('<filename>\n') + len('<filename>\n')
            end = self.files['file-fields']['data'].index('</filename>')
            self.logo_name = xml_string_logo[deb:end].strip(" ").replace("\n", "").replace("&amp;", "&")
            self.logo = self.files[self.logo_name]['data']

    def migrate(self):
        try:
            Item.migrate(self)
        except Exception:
            import ipdb
            ipdb.set_trace()


class ClubsSportifs(Item):
    _container = None
    _logo_name = None
    _logo = None

    @property
    def container(self):
        return self._container

    @container.setter
    def container(self, container):
        self._container = container

    @property
    def logo_name(self):
        return self._logo_name

    @logo_name.setter
    def logo_name(self, container):
        self._logo_name = container

    @property
    def logo(self):
        return self._logo

    @logo.setter
    def logo(self, container):
        self._logo = container

    def __init__(self, xml_item):
        Item.__init__(self, xml_item)

    def __create(self):
        Item.__create(self)
        # self.container = self.migrate_container_shop
        if 'file-fields' in self.files:
            xml_string_logo = self.files['file-fields']['data']
            deb = self.files['file-fields']['data'].index('<filename>\n') + len('<filename>\n')
            end = self.files['file-fields']['data'].index('</filename>')
            self.logo_name = xml_string_logo[deb:end].strip(" ").replace("\n", "").replace("&amp;", "&")
            self.logo = self.files[self.logo_name]['data']

    def migrate(self):
        try:
            Item.migrate(self)
        except Exception:
            import ipdb
            ipdb.set_trace()


class Shop(Item):
    _container = None
    _logo_name = None
    _logo = None

    @property
    def container(self):
        return self._container

    @container.setter
    def container(self, container):
        self._container = container

    @property
    def logo_name(self):
        return self._logo_name

    @logo_name.setter
    def logo_name(self, container):
        self._logo_name = container

    @property
    def logo(self):
        return self._logo

    @logo.setter
    def logo(self, container):
        self._logo = container

    def __init__(self, xml_item):
        Item.__init__(self, xml_item)

    def __create(self):
        Item.__create(self)
        # self.container = self.migrate_container_shop
        if 'file-fields' in self.files:
            xml_string_logo = self.files['file-fields']['data']
            deb = self.files['file-fields']['data'].index('<filename>\n') + len('<filename>\n')
            end = self.files['file-fields']['data'].index('</filename>')
            self.logo_name = xml_string_logo[deb:end].strip(" ").replace("\n", "").replace("&amp;", "&")
            self.logo = self.files[self.logo_name]['data']

    def migrate(self):
        try:
            Item.migrate(self)
        except Exception:
            import ipdb
            ipdb.set_trace()


class Artisanat(Shop):
    def __init__(self, xml_item):
        Shop.__init__(self, xml_item)


class ProduitsDuTerroir(Shop):
    def __init__(self, xml_item):
        Shop.__init__(self, xml_item)


class commercants(Shop):
    """
    For "commercants" objets (ver.4.3.2)
    """
    def __init__(self, xml_item):
        Shop.__init__(self, xml_item)


class Contact(Item):
    def __init__(self, xml_item):
        Item.__init__(self, xml_item)

    def __create(self):
        Item.__create(self)

    def migrate(self):
        """
        Contact type hasn't equivalent type in collective.directory.type. It's merge in card.
        """
        # split fullPath to the contact.
        split_path = self.path.split('/')
        # get idCard from the path
        id_card = split_path[len(split_path) - 2]
        try:
            # Try to get Card thank to idCard.
            brain_card = self._get_item_by_id('collective.directory.card', id_card)
            if brain_card is not None and len(brain_card) > 0:
                card = brain_card.getObject()
                self._merge_in_existant_card(card)
        except Exception:
            import ipdb
            ipdb.set_trace()
