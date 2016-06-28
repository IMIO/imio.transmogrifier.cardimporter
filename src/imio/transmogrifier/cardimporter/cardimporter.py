#!/usr/bin/env python
# -*- coding: utf-8 -*-
from base64 import b64decode
from collective.geo.behaviour.interfaces import ICoordinates
from collective.transmogrifier.interfaces import ISection, ISectionBlueprint
#from lxml import objectify
from plone.app.textfield.value import RichTextValue
from plone.namedfile.file import NamedBlobImage
from plone import api
from zope.interface import classProvides, implements
from collective.transmogrifier.utils import defaultMatcher
import logging
#import re
import unicodedata
import transaction
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
        self.pathkey = defaultMatcher(options, 'path-key', name, 'path')

        qi_tool = api.portal.get_tool(name='portal_quickinstaller')
        pid = 'collective.directory'
        installed = [p['id'] for p in qi_tool.listInstalledProducts()]
        if pid not in installed:
            setup = api.portal.get_tool(name='portal_setup')
            setup.runAllImportStepsFromProfile('profile-collective.directory:default')

        portal = api.portal.get()
        if MIGRATE_CONTAINER_SHOP in self.portal.keys():
            api.content.delete(obj=portal[MIGRATE_CONTAINER_SHOP])
        if MIGRATE_CONTAINER_ASSOCIATION in self.portal.keys():
            api.content.delete(obj=portal[MIGRATE_CONTAINER_ASSOCIATION])
        if MIGRATE_CONTAINER_HEBERGEMENT in self.portal.keys():
            api.content.delete(obj=portal[MIGRATE_CONTAINER_HEBERGEMENT])
        if MIGRATE_CONTAINER_CLUBSPORTIF in self.portal.keys():
            api.content.delete(obj=portal[MIGRATE_CONTAINER_CLUBSPORTIF])
        transaction.commit()
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

    def _set_encoding(self):
        import sys
        stdin, stdout = sys.stdin, sys.stdout
        reload(sys)
        sys.stdin, sys.stdout = stdin, stdout
        sys.setdefaultencoding('utf-8')

    def _traverse(self, path):
        return self.context.unrestrictedTraverse(path.lstrip('/'), None)

    def __iter__(self):
        """
        Iterate transmogrifier structure
        """
        # cross the transmogrify structure
        for item in self.previous:
            pathkey = self.pathkey(*item.keys())[0]
            if not pathkey:
                yield item
                continue

            if '_type' in item and item['_type'] == 'BottinAssociationsTool':
                yield item
                continue

            path = item[pathkey]
            container = None
            if isinstance(path, unicode):
                path = path.encode('ascii')

            # Looking for old type.
            if '_classname' in item and 'ASSOCIATION' in item['_classname'].upper():
                container = self.migrate_container_association
            if '_classname' in item and 'SHOP' in item['_classname'].upper():
                container = self.migrate_container_shop

            # If we got a container, we can create  a catedgory and a card from Item(**item) into container\category\
            if container is not None:
                current_item = Item(**item)
                if current_item.get_category is None:
                    import ipdb;ipdb.set_trace()
                if isinstance(current_item.get_category, list):
                    current_item.get_category = current_item.get_category[0]
                category = self._get_category_from_catalog(current_item.get_category)
                if category is None:
                    category = self.create_category(current_item.get_category, container)
                if isinstance(category, list):
                    category = category[0]
                self.create_card(current_item, category)

            # Card was create so we want usefull image from card-content follow the card.
            if '_classname' in item and 'IMAGE' in item['_classname'].upper():
                current_image = CustomImage(**item)
                self.search_image_into_card_content(current_image)
            transaction.commit()
            yield item
            continue

    def search_image_into_card_content(self, image):
        try:
            catalog = api.portal.get_tool(name="portal_catalog")
            # get all registered cards
            brains = catalog.searchResults({'portal_type': 'collective.directory.card'})
            for brain in brains:
                obj_card = brain.getObject()
                if image._uid in obj_card.content.output:
                    # get all registered images
                    img_brains = catalog.searchResults({'portal_type': 'Image'})
                    for img_brain in img_brains:
                        obj_img = img_brain.getObject()
                        # if we find a registered Image having uid used in card
                        if obj_img.UID() == image._uid:
                            try:
                                #First, we look if a folder "images was create in the card.
                                destination_folder = self.get_path_for_image(obj_card)
                                #Secondly, we move obj_img in the folder
                                api.content.move(obj_img, destination_folder)
                                #obj_img.reindexObject()
                                obj_card.reindexObject()
                            except Exception as e:
                                print e.message, e.args
                                import ipdb;ipdb.set_trace()
        except Exception as e:
            print e.message, e.args
            import ipdb;ipdb.set_trace()

    def get_path_for_image(self, card):
        complete_str_path = '/'.join(card.getPhysicalPath()) + '/images'
        folder_images_path = card.portal_catalog.searchResults(portal_type='Folder', path=complete_str_path, depth=1)
        if not len(folder_images_path):
            # Création d'un dossier "images" dans la card.
            folder_images = api.content.create(
                type='Folder',
                title='Images',
                id='images',
                container=card
            )
            api.content.transition(obj=folder_images, transition='publish_and_hide')
        else:
            for folder in folder_images_path:
                folder_images = folder.getObject()
        return folder_images

    def _get_category_from_catalog(self, current_category):
        catalog = api.portal.get_tool(name="portal_catalog")
        if current_category is None:
            import ipdb;ipdb.set_trace()
        brains = catalog.searchResults({'portal_type': 'collective.directory.category', 'id': _remove_special_chars(current_category)})
        retour = None
        for brain in brains:
            retour = brain
            retour = retour.getObject()
        return retour

    def create_category(self, category, container):
        new_category = None
        try:
            if isinstance(category, list):
                category = category[0]
            new_category = api.content.create(
                type='collective.directory.category',
                title=category,
                id=_remove_special_chars(category),
                container=container
            )
            api.content.transition(obj=new_category, transition='publish_and_hide')
            return new_category
        except:
            import ipdb;ipdb.set_trace()

    def create_card(self, item, category):
        coord = None
        sous_titre = ''
        description = ''
        website = hasattr(item, 'websiteurl') and item.websiteurl or hasattr(item, 'url') and item.url or None
        city = hasattr(item, 'commune') and item.commune or hasattr(item, 'city') and item.city or None
        phone = hasattr(item, 'phone') and item.phone or hasattr(item, 'phone1') and item.phone1 or None
        horaire = hasattr(item, 'opening_hours') and item.opening_hours or hasattr(item, 'schedule') and item.schedule or ''
        adresse = hasattr(item, 'street') and item.street or None
        #hasattr(item, 'zip') and item.zip.replace('','0')int(item.zip) or None
        code_postal = hasattr(item, 'zip') and item.zip or None
        gsm = hasattr(item, 'mobile') and item.mobile or None
        faxe = hasattr(item, 'fax') and item.fax or None
        mail = hasattr(item, 'email') and item.email or None
        # if isinstance(item, commercants) or isinstance(item, Associations):
        if hasattr(item, 'lastname'):
            sous_titre += item.lastname
            if hasattr(item, 'firstname'):
                sous_titre += ' ' + item.firstname
        # if isinstance(item, Association):
            if hasattr(item, 'asbl') and item.asbl == 'True':
                description = "ASBL "
        #if isinstance(item, Shop):
        sous_titre += hasattr(item, 'shopOwner') and item.shopOwner or ''
        if hasattr(item, 'Coordinates'):
            lat, lon = item.Coordinates.split('|')
            coord = u"POINT({0} {1})".format(lon, lat)
        content_str = "{0}<br/>{1}<br/>{2}<br/>{3}<br/>{4}<br/>{5}".format((hasattr(item, 'presentation') and " " + item.presentation.replace("/image_preview","/@@images/image/preview") or ''),
                                                                            horaire, (hasattr(item, 'information') and item.information or ''),
                                                                            self._get_str_coord_role(item, 'president'),
                                                                            self._get_str_coord_role(item, 'secretary'),
                                                                            self._get_str_coord_role(item, 'treasurer')
                                                                            )
        content = RichTextValue(unicode(content_str, 'utf8'))
        description = "{0} {1}".format(description, hasattr(item, 'description') and item.description or '')
        try:
            card = api.content.create(
                type='collective.directory.card',
                title=item.title,
                subtitle=sous_titre,
                description=description,
                content=content,
                city=city,
                address=adresse,
                zip_code=code_postal,
                phone=phone,
                photo=item.get_logo,
                mobile_phone=gsm,
                fax=faxe,
                email=mail,
                website=website,
                creators=tuple(item.creators),
                contributors=tuple(item.contributors),
                creation_date=item.creation_date,
                container=category
            )
            ICoordinates(card).coordinates = coord
            api.content.transition(obj=card, transition='publish_and_hide')
            return card
        except:
            import ipdb;ipdb.set_trace()

    def _get_str_coord_role(self, item, role):
        str = ""
        dict_role = {
            'president': 'Président',
            'secretary': 'Secrétaire',
            'treasurer': 'Trésorier'
        }
        if hasattr(item, 'surname_' + role) and getattr(item, 'surname_' + role) != "":
            str = dict_role[role] + ' : <br/>'
            str += getattr(item, 'surname_' + role)
        if hasattr(item, 'firstname_' + role) and getattr(item, 'firstname_' + role) != "":
            str += ' ' + getattr(item, 'firstname_' + role)
            str += '<br/>'
        if hasattr(item, 'street_' + role) and getattr(item, 'street_' + role) != "":
            str += getattr(item, 'street_' + role)
            str += '<br/>'
        if hasattr(item, 'zip_' + role) and getattr(item, 'zip_' + role) != "":
            str += getattr(item, 'zip_' + role)
        if hasattr(item, 'city_' + role) and getattr(item, 'city_' + role) != "":
            str += ' ' + getattr(item, 'city_' + role)
            str += '<br/>'
        if hasattr(item, 'gsm_' + role) and getattr(item, 'gsm_' + role) != "":
            str += 'gsm : ' + getattr(item, 'gsm_' + role)
        if hasattr(item, 'phone_' + role) and getattr(item, 'phone_' + role) != "":
            str += ' - tel : ' + getattr(item, 'phone_' + role)
            str += '<br/>'
        if hasattr(item, 'email_' + role) and getattr(item, 'email_' + role) != "":
            str += ' email : ' + getattr(item, 'email_' + role)
        if str != "":
            return '<p>' + str + '</p>'
        else:
            return ""


class Item():
    def __init__(self, **entries):
        self.__dict__.update(entries)
        self._setattr_get_category()
        self._setattr_get_logo()

    def _setattr_get_category(self):
        setattr(self, "get_category", None)
        if hasattr(self, "category"):
            setattr(self, "get_category", self.category)
        elif hasattr(self, "shopType"):
            setattr(self, "get_category", self.shopType)
        elif hasattr(self, "association_type"):
            setattr(self, "get_category", self.association_type)
        elif hasattr(self, "get_category") and isinstance(self.get_category, list):
            self.get_category = self.get_category[0]
        if self.get_category is None:
            import ipdb;ipdb.set_trace()

    def _setattr_get_logo(self):
        if hasattr(self, "_datafield_logo"):
            try:
                if self._datafield_logo['encoding'] == 'base64':
                    data = b64decode(self._datafield_logo['data'])
                filename = unicode(self._datafield_logo['filename'])
                contentType = self._datafield_logo['content_type']
                image = NamedBlobImage(data=data, contentType=contentType, filename=filename)
                setattr(self, "get_logo", image)
            except:
                import ipdb;ipdb.set_trace()
        else:
            setattr(self, "get_logo", None)


class CustomImage():
    def __init__(self, **entries):
        self.__dict__.update(entries)


def _remove_special_chars(input_string):
    """
    Remove accent from input string input_str (to make id)
    """
    return_string = input_string
    try:

        if type(input_string) is unicode:
            nkfd_form = unicodedata.normalize('NFKD', input_string)
            return_string = nkfd_form.encode('ASCII', 'ignore')
        if " " in return_string:
            return_string = return_string.replace(" ", "_")
        if "/" in return_string:
            return_string = return_string.replace("/", "-")
        if "&" in return_string:
            return_string = return_string.replace("&", "et")
        if "??" in return_string:
            return_string = return_string.replace("?", "ea")
        if "?" in return_string:
            return_string = return_string.replace("?", "e")
        return return_string
    except:
        import ipdb;ipdb.set_trace()
        return "None"
