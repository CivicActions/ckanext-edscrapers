# -*- coding: utf-8 -*-
import re

from scrapy.spiders import Rule
from scrapy.spiders import CrawlSpider
from scrapy.linkextractors import LinkExtractor

from edscrapers.scrapers.edgov.oese.parser import parse


class Crawler(CrawlSpider):

    name = 'oese'

    allowed_regex = r'oese.ed.gov'
    allowed_domains = ['oese.ed.gov']

    def __init__(self, conf=None):

        self.conf = conf

        self.start_urls = [
            'https://oese.ed.gov/'
        ]

        # Make rules
        self.rules = [
            Rule(LinkExtractor(
                allow=self.allowed_regex,
                # deny=f'.*({"|".join(h.get_data_extensions())})',
                # restrict_xpaths='//*[@id="maincontent"]'
                # process_value=self.process_value
            ), callback=parse, follow=True),
        ]


        # Inherit parent
        super(Crawler, self).__init__()
        
