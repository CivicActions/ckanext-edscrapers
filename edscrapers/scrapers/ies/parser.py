""" main parser for nces. parser
handles branching and delication to
other parsers in the 'parsers' subpackage"""

# -*- coding: utf-8 -*-
import re
import json

import bs4

from edscrapers.scrapers import base
import edscrapers.scrapers.base.parser as base_parser
from edscrapers.scrapers.ies import parsers

# contains list of data resources to exclude from dataset
deny_list = []

def parse(res):
    """ function parses content to create a dataset model
    or return None if no resource in content"""

    soup_parser = bs4.BeautifulSoup(res.text, 'html5lib')
    # check if the content contains any of the extensions
    if soup_parser.body.find(name='a', href=base_parser.resource_checker,
                             recursive=True) is None:
        # no resource on this page, so return None
        return None

    # if code gets here, at least one resource was found

    if (soup_parser.body.find(name='div', class_='nces', recursive=True) is not None)\
       and  (len(soup_parser.body.find_all(name='table', recursive=True)) > 0):
        return parsers.nces_parser.parse(res)

    if (soup_parser.body.find(name='div', class_='MainContent', recursive=True) is not None)\
       and (len(soup_parser.body.select('ul > li')) > 0)\
       or (soup_parser.body.find(name='div', id='ContentRight',recursive=True) is not None)\
       or (soup_parser.body.find(name='div', itemprop="mainEntity", recursive=True) is not None):
        return parsers.ies_parser.parse(res)
    else:
        return None


    


