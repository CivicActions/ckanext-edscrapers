# -*- coding: utf-8 -*-
import re

from scrapy.spiders import Rule
from scrapy.spiders import CrawlSpider
from scrapy.linkextractors import LinkExtractor

from edscrapers.scrapers.edgov.octae.parser import parse
from edscrapers.scrapers.base import helpers as h

class Crawler(CrawlSpider):

    name = 'octae'
    allowed_regex = r'ovae|OVAE|octae|OCTAE'

    allowed_domains = ['www2.ed.gov','lincs.ed.gov']

    def __init__(self, conf=None):

        self.conf = conf

        self.start_urls = [
            'https://www2.ed.gov/about/offices/list/ovae/index.html',
            'https://www2.ed.gov/offices/OVAE/CTE/legis.html',
            'https://www2.ed.gov/about/offices/list/ovae/pi/memoperkinsiv.html',
            'https://www2.ed.gov/about/offices/list/ovae/pi/AdultEd/index.html',
            
            'https://www2.ed.gov/about/reports/annual/index.html',
            'https://www2.ed.gov/about/reports/annual/otherplanrpts.html',
            'https://www2.ed.gov/policy/sectech/leg/cte/fsrhome.html',
            'https://lincs.ed.gov/lincs/resourcecollections/background.html',
            
        ]

        # Make rules
        self.rules = [
            Rule(LinkExtractor(
                allow=self.allowed_regex,
                #deny=f'.*({"|".join(h.get_data_extensions())})',
                #restrict_xpaths='//*[@id="maincontent"]',
                process_value=self.process_value
            ), callback=parse, follow=True),
        ]

        # Inherit parent
        super(Crawler, self).__init__()

    def process_value(self, value):
        m = re.search("javascript:goToPage\('(.*?)'", value)
        if m:
            return m.group(1)
        else:
            return value
