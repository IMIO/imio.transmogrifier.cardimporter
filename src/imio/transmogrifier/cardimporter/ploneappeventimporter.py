#!/usr/bin/env python
# -*- coding: utf-8 -*-
from collective.transmogrifier.interfaces import ISection, ISectionBlueprint
from collective.transmogrifier.utils import defaultMatcher
from plone.app.event.dx.behaviors import IEventBasic
from zope.interface import classProvides, implements
import logging

logger = logging.getLogger('imio.transmogrifier.cardimporer.ATPhotoToBlobImage')


class PloneAppEventImporter(object):
    """
    Blueprint that transform old archetypes event to dexterity plone.app.event.
    """
    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        self.context = transmogrifier.context
        self.pathkey = defaultMatcher(options, 'path-key', name, 'path')
        self.previous = previous

    def __iter__(self):
        """
        Iterate transmogrifier structure
        """
        for item in self.previous:
            pathkey = self.pathkey(*item.keys())[0]
            path = item[pathkey]
            obj = self.context.unrestrictedTraverse(path.lstrip('/'), None)
            import ipdb;ipdb.set_trace()
            timezone = 'Europe/Brussels'
            obj.timezone = timezone
            behavior = IEventBasic(obj)
            behavior.start = obj.start_date
            behavior.end = obj.end_date
            if path == '' or obj is None or obj.aq_parent is None:
                yield item; continue
            else:
                parent = obj.aq_parent
                if parent.getPortalTypeName() != 'FormFolder':
                    yield item; continue
            yield item
