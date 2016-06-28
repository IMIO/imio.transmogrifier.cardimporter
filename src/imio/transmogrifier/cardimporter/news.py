#!/usr/bin/env python
# -*- coding: utf-8 -*-
from collective.transmogrifier.interfaces import ISection, ISectionBlueprint
from zope.interface import classProvides, implements
from collective.transmogrifier.utils import defaultMatcher
import logging
logger = logging.getLogger('collective.directory.migrate')
from DateTime import DateTime


class NewsImporterSection(object):
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
            # get new item path
            path = item[pathkey]
            if '_type' in item and 'Event' in item['_type']:
                # get news item.
                fake_event = Event(**item)
                event_item = self.context.unrestrictedTraverse(path.lstrip('/'), None)
                try:
                    if fake_event.effectiveDate == 'None':
                        fake_event.effectiveDate = None
                    if fake_event.expirationDate == 'None':
                        fake_event.expirationDate = None
                    if fake_event.creation_date == 'None':
                        fake_event.creation_date = None
                    if fake_event.modification_date == 'None':
                        fake_event.modification_date = None
                    event_item.end = self.transform_str_date(fake_event.endDate)
                    event_item.start = self.transform_str_date(fake_event.startDate)
                    event_item.contact_email = fake_event.contactEmail
                    event_item.contact_name = fake_event.contactName
                    event_item.contact_phone = fake_event.contactPhone
                    event_item.event_url = fake_event.eventUrl
                    event_item.creation_date = fake_event.creation_date
                    event_item.modification_date = self.transform_str_date(fake_event.modification_date)
                    event_item.effective_date = self.transform_str_date(fake_event.effectiveDate)
                    event_item.expiration_date = self.transform_str_date(fake_event.expirationDate)
                    self.attach_lead_image(item, event_item)
                except:
                    import ipdb;ipdb.set_trace()
            if '_type' in item and 'News' in item['_type'] and 'Newsletter' not in item['_type']:
                # get news item.
                fake_news = News(**item)
                news_item = self.context.unrestrictedTraverse(path.lstrip('/'), None)
                try:
                    if fake_news.effectiveDate == 'None':
                        fake_news.effectiveDate = None
                    if fake_news.expirationDate == 'None':
                        fake_news.expirationDate = None
                    if fake_news.creation_date == 'None':
                        fake_news.creation_date = None
                    if fake_news.modification_date == 'None':
                        fake_news.modification_date = None
                    news_item.creation_date = fake_news.creation_date
                    news_item.modification_date = self.transform_str_date(fake_news.modification_date)
                    news_item.effective_date = self.transform_str_date(fake_news.effectiveDate)
                    news_item.expiration_date = self.transform_str_date(fake_news.expirationDate)
                    #zopedate = DateTime(fake_news.modification_date)
                    #news_item.modification_date = zopedate.asdatetime()
                    self.attach_lead_image(item, news_item)
                except:
                    import ipdb;ipdb.set_trace()

            yield item

    def transform_str_date(self, strDate):
        import pytz, datetime
        local = pytz.timezone("Europe/Brussels")
        date_format = "%Y/%m/%d %H:%M:%S.%f"
        if strDate is None:
            return None
        else:
            if "." in strDate:
                date_format = "%Y/%m/%d %H:%M:%S.%f"
            elif ":" in strDate:
                date_format = "%Y/%m/%d %H:%M:%S"
            else:
                date_format = "%Y/%m/%d"
            if " GMT+1" in strDate:
                naive = datetime.datetime.strptime(strDate.replace(" GMT+1", ""), date_format)
                local_dt = local.localize(naive, is_dst=None)
            elif " GMT+2" in strDate:
                naive = datetime.datetime.strptime(strDate.replace(" GMT+2", ""), date_format)
                local_dt = local.localize(naive, is_dst=True)
            else:
                naive = datetime.datetime.strptime(strDate, date_format)
                local_dt = local.localize(naive, is_dst=True)
            utc_dt = local_dt.astimezone(pytz.utc)
            return utc_dt

    def attach_lead_image(self, json_item, item):
        from base64 import b64decode
        from plone.app.contenttypes.behaviors.leadimage import ILeadImage
        from plone.namedfile.file import NamedBlobImage
        image = None
        if '_datafield_leadImage' in json_item:
            datafield_leadImage = json_item['_datafield_leadImage']
            if datafield_leadImage['encoding'] == 'base64':
                data = b64decode(datafield_leadImage['data'])
                filename = unicode(datafield_leadImage['filename'])
                contentType = datafield_leadImage['content_type']
                image = NamedBlobImage(data=data, contentType=contentType, filename=filename)
            leadImage = ILeadImage(item)
            leadImage.image = image


class News():
    def __init__(self, **entries):
        self.__dict__.update(entries)


class Event():
    def __init__(self, **entries):
        self.__dict__.update(entries)
