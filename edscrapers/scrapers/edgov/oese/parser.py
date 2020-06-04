""" main parser for oese. parser
handles branching and delication to
other parsers in the 'parsers' subpackage"""

# -*- coding: utf-8 -*-
import re
import json

import bs4

from edscrapers.scrapers import base
import edscrapers.scrapers.base.parser as base_parser
from edscrapers.scrapers.edgov.oese import parsers

# contains list of data resources to exclude from dataset
deny_list = []

def parse(res, publisher={'name': 'oese', 'subOrganizationOf': None}):
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
    
    # check if the parser is working on OESE web page
    if soup_parser.body.find(name='div', class_='container', recursive=True) is not None:
        # parse the page with the parser and return result
        return parsers.parser1.parse(res, publisher)
    else:
        return None


    


