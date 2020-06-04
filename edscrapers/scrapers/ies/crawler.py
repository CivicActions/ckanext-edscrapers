# -*- coding: utf-8 -*-
import re

from scrapy.spiders import Rule
from scrapy.spiders import CrawlSpider
from scrapy.linkextractors import LinkExtractor

from edscrapers.scrapers.ies.parser import parse
from edscrapers.scrapers.base import helpers as h


class Crawler(CrawlSpider):

    name = 'ies'

    allowed_regex = r'(nces|ies)\.ed\.gov'
    # Only nces has a dedicated website. All the other centers are subsections of `ies.ed/gov`
    allowed_domains = ['nces.ed.gov','ies.ed.gov', ]

    # TODO: Get the name of the suboffice from the publisher meta tag and ask Victor how to save these attributes
    def __init__(self):

        self.start_urls = [
            # Get all records since 1980
            'https://ies.ed.gov/pubsearch/index.asp?searchyear=1980'
            # Imported from the nces parser
            'https://nces.ed.gov/datatools/',
            'https://ies.ed.gov/data.asp',
            'https://nces.ed.gov/pubsearch/index.asp',
            'https://nces.ed.gov/Datalab/TablesLibrary',
            #'https://nces.ed.gov/pubs2009/expenditures/tables/table_08.asp?referrer=report'
            #'https://nces.ed.gov/surveys/els2002/tables/APexams_01.asp'
            #'https://nces.ed.gov/ipeds/deltacostproject/'
            #'https://nces.ed.gov/pubs2009/expenditures/tables.asp'
        ]

        # Make rules
        self.rules = [
            Rule(LinkExtractor(
                allow=self.allowed_regex,
                deny=["\\" + regex for regex in h.get_data_extensions().keys()],
                # restrict_xpaths='//*[@id="maincontent"]'
                # process_value=lambda value: value.replace('http', 'https', 1),
            ), callback=parse, follow=True),
        ]


        # Inherit parent
        super(Crawler, self).__init__()
