# -*- coding: utf-8 -*-
import re

from scrapy.spiders import Rule
from scrapy.spiders import CrawlSpider
from scrapy.linkextractors import LinkExtractor

from edscrapers.scrapers.ocr.parser import parse
from edscrapers.scrapers.base import helpers as h


class Crawler(CrawlSpider):

    name = 'ocr'

    allowed_regex = r'^http.*://.*ocrdata\.ed\.gov.*'
    # depth = 10

    def __init__(self):

        self.start_urls = [
            # The main menu
            #'https://ocrdata.ed.gov/StateNationalEstimations'
            'https://ocrdata.ed.gov/Home',
            'https://ocrdata.ed.gov/DistrictSchoolSearch',
            #'https://ocrdata.ed.gov/StateNationalEstimations/Estimations_2015_16',
            #'https://ocrdata.ed.gov/StateNationalEstimations/Projections_2009_10',
            #'https://ocrdata.ed.gov/StateNationalEstimations/Estimations_2011_12#',
            #'https://ocrdata.ed.gov/StateNationalEstimations/Estimations_2011_12#',
            'https://ocrdata.ed.gov/DownloadDataFile',
            'https://ocrdata.ed.gov/StateNationalEstimations',
            'https://ocrdata.ed.gov/SpecialReports',
            'https://ocrdata.ed.gov/DataAnalysisTools'
        ]

        """ self.start_urls = [
            # The main menu
            'https://ocrdata.ed.gov/StateNationalEstimations/Estimations_2013_14',
    'https://ocrdata.ed.gov/StateNationalEstimations/Estimations_2011_12',
    'https://ocrdata.ed.gov/StateNationalEstimations/Projections_2009_10',
    'https://ocrdata.ed.gov/StateNationalEstimations/Projections_2006',
    'https://ocrdata.ed.gov/StateNationalEstimations/Projections_2004',
    'https://ocrdata.ed.gov/StateNationalEstimations/Projections_2000'
    ] """

        # Make rules
        self.rules = [
            Rule(LinkExtractor(
                allow=r'http.*://.*ocrdata\.ed\.gov.*$',
                # deny=f'.*({"|".join(h.get_data_extensions())})',
                #restrict_xpaths='//*[@id="maincontent"]'
            ), callback=parse, follow=True),
        ]

        # Inherit parent
        super(Crawler, self).__init__()
