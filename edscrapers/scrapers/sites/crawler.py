# -*- coding: utf-8 -*-
import re

from scrapy.spiders import Rule
from scrapy.spiders import CrawlSpider
from scrapy.linkextractors import LinkExtractor

from edscrapers.scrapers.sites.parser import parse
from edscrapers.scrapers.base import helpers as h


class Crawler(CrawlSpider):

    name = 'sites'

    allowed_regex = r'^http.*://sites\.ed\.gov/.*$'
    # allowed_domains = ['ed.gov', 'www2.ed.gov']

    def __init__(self):

        self.start_urls = [
            'https://sites.ed.gov/'
        ]

        extensions_to_avoid = []
        for ext in [h.get_data_extensions(), h.get_document_extensions(), h.get_avoidable_extensions()]:
            extensions_to_avoid.extend(ext.keys())

        # Make rules
        self.rules = [
            Rule(LinkExtractor(
                allow=self.allowed_regex,
                deny_extensions=[ext[1:] for ext in extensions_to_avoid],
            ), callback=parse, follow=True),
        ]

        # Inherit parent
        super(Crawler, self).__init__()
