# -*- coding: utf-8 -*-
from scrapy.spiders import Rule
from scrapy.spiders import CrawlSpider
from scrapy.linkextractors import LinkExtractor

from edscrapers.scrapers.oela.parser import parse
from edscrapers.scrapers.base import helpers as h


class Crawler(CrawlSpider):

    name = 'oela'
    allowed_regex = r'oela|ncela'
    allowed_domains = ['ed.gov']

    def __init__(self, conf=None):

        self.conf = conf

        self.start_urls = [
            'https://www2.ed.gov/about/offices/list/oela/index.html'
        ]

        # Make rules
        self.rules = [
            Rule(LinkExtractor(
                allow=self.allowed_regex,
                deny=["\\" + regex for regex in h.get_data_extensions().keys()],
                #restrict_xpaths='//div[@id="maincontent"]'
            ), callback=parse, follow=True),
        ]


        # Inherit parent
        super(Crawler, self).__init__()
