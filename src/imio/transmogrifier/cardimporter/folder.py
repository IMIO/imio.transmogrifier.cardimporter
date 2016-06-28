#!/usr/bin/env python
# -*- coding: utf-8 -*-
from collective.transmogrifier.interfaces import ISection, ISectionBlueprint
from zope.interface import classProvides, implements
from collective.transmogrifier.utils import defaultMatcher
import logging
logger = logging.getLogger('collective.directory.migrate')


class FolderLayoutSection(object):
    """
    Blueprint to import news.
    """
    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        self._set_encoding()
        self.previous = previous
        self.context = transmogrifier.context
        self.portal = self.context
        self.pathkey = defaultMatcher(options, 'path-key', name, 'path')

    def _set_encoding(self):
        import sys
        stdin, stdout = sys.stdin, sys.stdout
        reload(sys)
        sys.stdin, sys.stdout = stdin, stdout
        sys.setdefaultencoding('utf-8')

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
            if '_type' in item and 'Folder' in item['_type']:
                # get new item path
                path = item[pathkey]
                folder_item = self.context.unrestrictedTraverse(path.lstrip('/'), None)
                if getattr(folder_item, "layout", '') and folder_item.layout != "folderview":
                    folder_item.layout = ""
            yield item

