import bs4

import logging
from datetime import datetime

from edscrapers.cli import logger
import edscrapers.scrapers.base.parser as base_parser
from edscrapers.scrapers.osers import parsers

deny_list = []

def parse(res):

    """ function parses content to create a dataset model
    or return None if no resource in content"""

    # ensure that the response text gotten is a string
    if not isinstance(getattr(res, 'text', None), str):
        return None

    try:
        soup_parser = bs4.BeautifulSoup(res.text, 'html5lib')
    except:
        return None

    # check if the content contains any of the extensions
    if soup_parser.body.find(name='a', href=base_parser.resource_checker,
                             recursive=True) is None:
        # no resource on this page, so return None
        return None

    # if code gets here, at least one resource was found
    
    # check if the parser is working on OSERS web page
    if soup_parser.body.find(name='div', id='maincontent', recursive=True) is not None:
        # parse the page with the parser and return result
        return parsers.parser1.parse(res)

    # check if the parser is working on OCTAE web page (variant 2)
    if soup_parser.body.select_one('.headersLevel1') is not None:
        # parse the page with the parser and return result
        return parsers.parser2.parse(res)
    else:

        logger.error('Page doesnt fit in any structure:')
        logger.error(res)

        return None

        

    

    
