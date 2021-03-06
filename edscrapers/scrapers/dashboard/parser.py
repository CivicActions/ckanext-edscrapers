""" main parser for edgov. parser
handles branching and delication to
other parsers in the 'parsers' subpackage"""

# -*- coding: utf-8 -*-
import re
import json
import importlib

import bs4

from edscrapers.cli import logger
from edscrapers.scrapers import base
import edscrapers.scrapers.base.parser as base_parser
from edscrapers.scrapers.dashboard import parsers
from edscrapers.scrapers.base.models import Publisher


def parse(res):
    """ function parses content to create a dataset model
    or return None if no resource in content"""

    if '/print/' in res.url:
        return None

    logger.debug(f'{res.url}')

    soup_parser = bs4.BeautifulSoup(res.text, 'html5lib')

    publisher = Publisher()
    publisher['name'] = 'edgov'
    publisher['subOrganizationOf'] = None

    # check if the content contains any of the extensions
    if soup_parser.body.find(name='a', href=base_parser.resource_checker,
                             recursive=True) is None:
        # no resource on this page, so return None
        return None
    # if code gets here, at least one resource was found
    
    # check if the parser is working on EDGOV web page
    if soup_parser.body.find(name='div', recursive=True) is not None:
        # parse the page with the parser and return result
        return parsers.parser1.parse(res, publisher)
    else:
        return None

