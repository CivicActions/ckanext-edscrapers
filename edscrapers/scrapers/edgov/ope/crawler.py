# -*- coding: utf-8 -*-
from scrapy.spiders import Rule
from scrapy.spiders import CrawlSpider
from scrapy.linkextractors import LinkExtractor

from edscrapers.scrapers.edgov.ope.parser import parse
from edscrapers.scrapers.base import helpers as h

class Crawler(CrawlSpider):

    name = 'ope'
    allowed_regex = r'ope/|iegpsnrc'

    allowed_domains = ['www2.ed.gov']

    def __init__(self, conf=None):

        self.conf = conf

        self.start_urls = [
            'https://www2.ed.gov/about/offices/list/ope/index.html',
            'https://www2.ed.gov/about/offices/list/ope/idues/eligibility.html',
            'https://www2.ed.gov/programs/iegpsnrc/awards.html'
        ]

        # Make rules
        self.rules = [
            Rule(LinkExtractor(
                allow=self.allowed_regex,
                #deny=f'.*({"|".join(h.get_data_extensions())})',
                #restrict_xpaths='//*[@id="maincontent"]'
            ), callback=parse, follow=True),
        ]

        # Inherit parent
        super(Crawler, self).__init__()
