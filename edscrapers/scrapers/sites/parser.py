""" main parser for sites.ed.gov. parser
handles branching and delication to
other parsers in the 'parsers' subpackage"""

# -*- coding: utf-8 -*-
import re
import json
import importlib

import bs4

from edscrapers.scrapers import base
from edscrapers.scrapers.sites import parsers
import edscrapers.scrapers.base.parser as base_parser
from edscrapers.scrapers.base.models import Publisher

publishers_map = {
    'hispanic-initiative': 'whieeh',
    'international': 'iae',
}

def parse(res):
    """ function parses content to create a dataset model
    or return None if no resource in content"""

    if '/print/' in res.url:
        return None

    soup_parser = bs4.BeautifulSoup(res.text, 'html5lib')

    try:
        publisher = res.url.split('sites.ed.gov')[1].split('/')[1]
    except:
        publisher = None

    if not publisher:
        print('No publisher', res.url)
        return None
    else:
        if publisher in publishers_map.keys():
            publisher = publishers_map[publisher]
        print('Publisher', publisher, res.url)


    # check if the content contains any of the extensions
    if soup_parser.body.find(name='a', href=base_parser.resource_checker,
                             recursive=True) is None:
        # no resource on this page, so return None
        print('(no resources found)\n')
        return None
    # if code gets here, at least one resource was found
    
    if soup_parser.body.find(name='div', recursive=True) is not None:
        # parse the page with the parser and return result
        return parsers.parser1.parse(res, publisher)
    else:
        return None


    


