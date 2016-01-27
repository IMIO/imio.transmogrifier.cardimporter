#!/usr/bin/env python
# -*- coding: utf-8 -*-
from collective.transmogrifier.interfaces import ISection, ISectionBlueprint
from collective.transmogrifier.utils import defaultMatcher
from lxml import objectify
from plone import api
from zope.interface import classProvides, implements
import logging
import re
import transaction
import unicodedata

logger = logging.getLogger('imio.transmogrifier.cardimporer.ATPhotoToBlobImage')


class ATPhotoToBlobImageSection(object):
    """
    Blueprint to import shop, Shop, association or Association into Card.
    """
    classProvides(ISectionBlueprint)
    implements(ISection)
    _path = None
    _folder = None
    _image = None

    def __init__(self, transmogrifier, name, options, previous):
        self.context = transmogrifier.context
        self.portal = self.context
        self.previous = previous
        self.context = transmogrifier.context
        self.fromkey = defaultMatcher(options, 'from-key', name, 'from')
        self.pathkey = defaultMatcher(options, 'path-key', name, 'path')
        self.layout = options.get('layout', 'atct_album_view').strip()

    def __iter__(self):
        """
        Iterate transmogrifier structure
        """
        for item in self.previous:
            if '_type' in item and 'ATPhotoAlbum' in item['_type']:
                curr_item = Item.create(self, item)
                self._folder = self.atphotoalbum_to_folder(curr_item)
            if '_type' in item and 'ATPhoto' in item['_type'] and 'ATPhotoAlbum' not in item['_type']:
                curr_item = Item.create(self, item)
                self._image = self.atphoto_to_image(curr_item)
            else:
                yield item
                continue

    def _set_encoding(self):
        import sys
        stdin, stdout = sys.stdin, sys.stdout
        reload(sys)
        sys.stdin, sys.stdout = stdin, stdout
        sys.setdefaultencoding('utf-8')

    def atphotoalbum_to_folder(self, item_atphotoalbum):
        parent_folder_path = item_atphotoalbum.path[0:(len(item_atphotoalbum.path) - len(item_atphotoalbum.id) - 1)]
        parent_folder = self.context.restrictedTraverse(parent_folder_path)
        folder = api.content.create(
            id=item_atphotoalbum.id,
            title=item_atphotoalbum.title,
            type='Folder',
            container=parent_folder
        )
        api.content.transition(obj=folder, transition='publish_and_hide')
        return folder

    def atphoto_to_image(self, item_image):
        parent_folder_path = item_image.path[0:(len(item_image.path) - len(item_image.id) - 1)]
        parent_folder = self.context.restrictedTraverse(parent_folder_path)
        current_image = api.content.create(
            id=item_image.id,
            type='Image',
            description='ajout image : ' + item_image.id,
            container=parent_folder
        )
        try:
            if "file-fields" in item_image.files and "data" in item_image.files['file-fields']:
                key = item_image.files.keys()[2]
                img_data = item_image.files[key]['data']
                if "?xml" in img_data:
                    # bad hack...stupid and wicked...
                    key = item_image.files.keys()[0]
                    img_data = item_image.files[key]['data']
                current_image.setImage(img_data)
                current_image.setFilename(unicode(item_image.id))
                transaction.commit()
            else:
                import ipdb
                ipdb.set_trace()
            return current_image
        except:
            import ipdb
            ipdb.set_trace()


class Item:
    _obj_data = None
    _xml_item = None
    _type = None
    _files = None
    _path = None
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
    def create(self, xml_item):
        item = None
        # obj = self.context.unrestrictedTraverse(path, None)
        if xml_item['_type'] is not None:
            current_type = xml_item['_type']
            if current_type == 'ATPhotoAlbum':
                item = Folder(xml_item)
            if current_type == 'ATPhoto':
                item = Image(xml_item)
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
            category = regex.sub("", self.category).replace("'", "-")
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

    def _remove_accents(self, input_string):
        """
        Remove accent from input string input_str
        """
        if type(input_string) is unicode:
            nkfd_form = unicodedata.normalize('NFKD', input_string)
            input_string = nkfd_form.encode('ASCII', 'ignore')
        return input_string


class Folder(Item):
    _container = None

    @property
    def container(self):
        return self._container

    @container.setter
    def container(self, container):
        self._container = container

    def __init__(self, xml_item):
        Item.__init__(self, xml_item)

    def __create(self):
        Item.__create(self)

    def migrate(self):
        try:
            Item.migrate(self)
        except Exception:
            import ipdb
            ipdb.set_trace()


class Image(Item):
    _container = None
    _logo_name = None
    _logo = None

    @property
    def container(self):
        return self._container

    @container.setter
    def container(self, container):
        self._container = container

    def __init__(self, xml_item):
        Item.__init__(self, xml_item)

    def __create(self):
        Item.__create(self)

    def migrate(self):
        try:
            Item.migrate(self)
        except Exception:
            import ipdb
            ipdb.set_trace()
