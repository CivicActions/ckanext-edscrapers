""" main parser for edgov. parser
handles branching and delication to
other parsers in the 'parsers' subpackage"""

# -*- coding: utf-8 -*-
import re
import json

import bs4

from edscrapers.scrapers import base
import edscrapers.scrapers.base.parser as base_parser
from edscrapers.scrapers.edgov import parsers
from edscrapers.scrapers.base.models import MetaPage, MetaItem, MetaHeader




def parse(res):

    if '/print/' in res.url:
        return None

    soup_parser = bs4.BeautifulSoup(res.text, 'html5lib')
    all_meta = soup_parser.find_all(name='meta')
    all_headers = res.headers

    page = MetaPage()

    page['source_url'] = res.url
    if soup_parser.head.find(name='title'):
        page['title'] = str(soup_parser.head.find(name='title').string).strip()
    else:
        page['title'] = ''
    page['notes'] = ''
    page['resources'] = ''
    page['name'] = res.url

    page['meta'] = []
    page['headers'] = []

    for h in res.headers.keys():
        header = MetaHeader()
        header['name'] = str(h)
        header['content'] = str(res.headers[h])
        page['headers'].append(header)

    for m in all_meta:
        meta = MetaItem()
        meta['name'] = str(m.get('name'))
        meta['content'] = str(m.get('content'))
        page['meta'].append(meta)

    return page



