# -*- coding: utf-8 -*-
from scrapy.spiders import Rule
from scrapy.spiders import CrawlSpider
from scrapy.linkextractors import LinkExtractor

from edscrapers.scrapers.edgov.osers.parser import parse
from edscrapers.scrapers.base import helpers as h

class Crawler(CrawlSpider):

    name = 'osers'
    allowed_regex = r'osers|osep|idea'
    allowed_domains = ['www2.ed.gov','osep.grads360.org']

    def __init__(self, conf=None):

        self.conf = conf

        self.start_urls = [
            'https://www2.ed.gov/about/offices/list/osers/index.html',
            'https://www2.ed.gov/about/offices/list/osers/products/employmentguide/index.html'
        ]

        # Make rules
        self.rules = [
            Rule(LinkExtractor(
                allow=self.allowed_regex,
                deny_extensions=[regex[1:] for regex in h.get_data_extensions().keys()],
                allow_domains=Crawler.allowed_domains
                #restrict_xpaths='//*[@id="maincontent"]'
            ), callback=parse, follow=True),
        ]

        # Inherit parent
        super(Crawler, self).__init__()
