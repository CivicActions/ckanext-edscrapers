# -*- coding: utf-8 -*-
import re
import logging
import datetime
import hashlib
import urllib.parse
import itertools
import requests
import bs4
import ratelimit
import backoff

from urllib.parse import urlparse
from urllib.parse import urljoin
from scrapy.linkextractors.lxmlhtml import LxmlLinkExtractor
from edscrapers.scrapers.base.models import Resource, Collection, Source

import pathlib
import importlib

logger = logging.getLogger(__name__)

# some of the sites scraped have rate limits so we need to throttle.
# a simple throttling implementation is employed for some api calls (that are affected by rate limits) within this module because
# such calls occur outside of scrapy's control and need to be catered for.
NUMBER_OF_CALLS_PER_LIMIT_WINDOWS = 3 # number of api calls allowed per rate limit period/window
RATE_LIMIT_WINDOW = 3 # time period (in seconds) within which 'NUMBER_OF_CALLS_PER_LIMIT_WINDOWS' are allowed
NUMBER_OF_RETRIES_AFTER_LIMIT = 10 # total number of times to retry a rate-limited api call
# total number of time (in seconds) which the exponential backoff algorithm (for rate-limited api call) will wait before final failure
TOTAL_BACKOFF_TIME = sum(itertools.accumulate(itertools.repeat(RATE_LIMIT_WINDOW, 
                                    NUMBER_OF_RETRIES_AFTER_LIMIT+1)))

def get_data_extensions():
    return {
        '.xls': 'Excel data file',
        '.csv': 'Comma delimited text file',
        '.sas': 'SAS syntax file',
        '.dat': 'Generic data file',
        '.spss': 'SPSS syntax',  # This may be an incorrect extension, but we will continue to search for it
        '.db.': 'Generic data base',
        '.sql': 'Structured query language file',
        '.xml': 'Extensible Markup language',
        '.zip': 'File containing compressed files',
        '.txt': 'Text files',

        '.xlsx': 'Excel data file',
        '.sps': 'SPSS syntax',
        '.sav': 'SPSS data',
        '.dat': 'Stata data',
        '.do': 'Stata syntax',
        '.r': 'R script',
        '.rdata': 'R data',
        '.rda': 'R data',
        '.sd2': 'SAS data',
        '.sd7': 'SAS data',
        '.sas7bdat': 'SAS data'
    }

def get_document_extensions():
    return {
        '.docx': 'Word document',
        '.doc': 'Word document',
        '.pdf': 'PDF file'
    }

def get_avoidable_extensions():
    return {
        '.jpg': 'JPG image file',
        '.jpeg': 'JPEG image file',
        '.png': 'PNG image file',
        '.ppt': 'MS PowerPoint file',
        '.pptx': 'MS PowerPoint file',
        '.mp3': 'MP3 audio file',
    }

def get_all_resources(res, dataset, extensions, deny_list=[]):
    for link in LxmlLinkExtractor(deny_extensions=[], deny=deny_list).extract_links(res):
        for extension in extensions.keys():
            if link.url.endswith(extension):
                resource = Resource(
                    source_url = res.url,
                    url = link.url,
                    name = link.text,
                )
                dataset['resources'].append(resource)

def get_variables(object, filter=None):
    """Extract variables from object to dict using name filter.
    """
    variables = {}
    for name, value in vars(object).items():
        if filter is not None:
            if not filter(name):
                continue
        variables[name] = value
    return variables

def get_meta_value(soup, meta_name):
    meta_tag = soup.head.find(name='meta',attrs={'name': meta_name})
    if meta_tag is None:
        meta_tag = soup.head.find(name='meta',attrs={'property': meta_name})
        if meta_tag is None:
            return None
    return meta_tag['content']


@backoff.on_exception(backoff.expo, Exception,
                      max_time=TOTAL_BACKOFF_TIME,
                      max_tries=NUMBER_OF_RETRIES_AFTER_LIMIT) # exponential backoff
@ratelimit.limits(calls=NUMBER_OF_CALLS_PER_LIMIT_WINDOWS,
                  period=RATE_LIMIT_WINDOW) # apply rate-limit throttling
def get_resource_headers(source_url, url):
    headers = dict()
    #return headers
    if urlparse(url).scheme:
        raw_headers = requests.head(url).headers
    else:
        raw_headers = requests.head(urljoin(source_url, url)).headers

    headers['content-type'] = raw_headers.get('Content-Type', None)
    headers['last-modified'] = raw_headers.get('Last-Modified', None)
    headers['content-length'] = raw_headers.get('Content-Length', None)

    return headers

def retrieve_crawlers_allowed_domains(except_crawlers=[]) -> list:
    """ function retireves all 'allowed_domains'
    (domains which are allowed to be scraped) from the available
    crawlers in the 'scrapers' package EXCEPT for the 'allowed_domains'
    for crawlers listed in 'except_crawlers'.
    
    function returns a list containing domain names ('allowed_domains')
    retrieved from all crawlers EXCEPT crawlers listed in 'except_crawlers'

    PARMAETERS:
    - except_crawlers : contains a list of crawler names whose
    'allowed_domains' should NOT be retrieved'. The default
    value is an empty list (which means no crawler is excluded) """

    # get the path to the scrapers package
    scrapers_path = pathlib.Path('./edscrapers/scrapers')
    allowed_domains = set() # collection of allowed domains
    except_allowed_domains = set() # domains to be exempted from collection

    # iterate over all subpackages in the scrapers package
    for subpath in scrapers_path.iterdir():
        if subpath.is_dir(): # check if subpath is a directory
            try:
                # import the crawler module from the subpackage
                crawler = importlib.import_module('.' + subpath.name + '.crawler', 
                                                  'edscrapers.scrapers')
                # check if the subpath is in included in exempted crawlers
                if subpath.name not in except_crawlers: # subpath not exempted
                    # retrieve the 'allowed_domains' from the imported crawler
                    # and add it the set of 'allowed domains'
                    allowed_domains.update(crawler.Crawler.allowed_domains)
                else: # subpath is exempted
                    # add the 'allowed_domains' from this subpackage to
                    # set of exempted domains
                    except_allowed_domains.update(crawler.Crawler.allowed_domains)
            except:
                continue
            # remove all exempted domains which may also be present in
            # 'allowed domains'
            allowed_domains.difference_update(except_allowed_domains)
    return list(allowed_domains) # return allowed_domains


@backoff.on_exception(backoff.expo, Exception,
                      max_time=TOTAL_BACKOFF_TIME,
                      max_tries=NUMBER_OF_RETRIES_AFTER_LIMIT) # exponential backoff
@ratelimit.limits(calls=NUMBER_OF_CALLS_PER_LIMIT_WINDOWS,
                  period=RATE_LIMIT_WINDOW) # apply rate-limit throttling
def extract_dataset_collection_from_url(collection_url,
                                        namespace, source_url=None):
    """ function is used to generate/extract a dataset 'Collection' from
    the provided collection_url.
    A collection is created based on the Collection model in
    edscrapers.scrapers.base.models

    PARAMETERS
    - collection_url: the url from which the Collection should be extracted/generated

    - namespace: in order to ensure a unique collection_id is created across
    collections, a namespace MUST be provided, the namespace may be considered as
    a distinguishing label between Collections with the same title.
    A Collection's unique id (collection_id) is created using an
    encoding algorithm which combines the 'collection_url' and 'namespace'.

    - source_url: the url from which the Source (this
    Collection belongs to) should be extracted/generated.
    if not specified, it is assumed that the Collection has no source

    Returns a edscrapers.scrapers.base.models.Collection object.
    If any of the required parameters are not present, None is return
    """

    # check the required parameters
    if (not collection_url) or (not namespace):
        return None
    
    # if collection_url is not an absolute url
    if not urlparse(collection_url).scheme:
        return None

    # cleanup the collection_url i.e. remove all query parameters
    collection_url = url_query_param_cleanup(collection_url, include_query_param=[])
    # compare collection_url and source_url
    if source_url and urlparse(source_url).scheme: # first make sure source_url is valid
        # now the comparison
        if collection_url == url_query_param_cleanup(source_url, include_query_param=[]):
            # collection_url and source_url are the same, so this is not a valid collection
            return None


    # make a request for html page contained in the provided url
    res = requests.get(collection_url, verify=False)

    # ensure that the response text gotten is a string
    if not isinstance(getattr(res, 'text', None), str):
        return None

    try:
        soup_parser = bs4.BeautifulSoup(res.text, 'html5lib')
    except:
        return None
    
    collection = Collection()
    collection['collection_url'] = collection_url
    # get the collection title
    if soup_parser.head.find(name='title'):
        collection['collection_title'] = str(soup_parser.head.\
                            find(name='title').string).strip()
    else:
      collection['collection_title'] = '[no title]'

    collection['collection_id'] =\
        f'{hashlib.md5(collection["collection_url"].encode("utf-8")).hexdigest()}-{hashlib.md5(namespace.encode("utf-8")).hexdigest()}'

    # if source_url was specified and it's an absolute url
    if source_url and urlparse(source_url).scheme:
        # generate the Source for this collection
        collection['source'] = extract_dataset_source_from_url(source_url, namespace)
    
    return collection


@backoff.on_exception(backoff.expo, Exception,
                      max_time=TOTAL_BACKOFF_TIME,
                      max_tries=NUMBER_OF_RETRIES_AFTER_LIMIT) # exponential backoff
@ratelimit.limits(calls=NUMBER_OF_CALLS_PER_LIMIT_WINDOWS,
                  period=RATE_LIMIT_WINDOW) # apply rate-limit throttling
def extract_dataset_source_from_url(source_url, namespace):
    """ function is used to generate/extract a dataset 'Source' from
    the provided source_url.
    A source is created based on the Source model in
    edscrapers.scrapers.base.models

    PARAMETERS
    - source_url: the url from which the Source should be extracted/generated

    - namespace: in order to ensure a unique source_id is created across
    sources, a namespace MUST be provided, the namespace may be considered as
    a distinguishing label between Sources with the same title.
    A Source's unique id (source_id) is created using an
    encoding algorithm which combines the 'source_url' and 'namespace'.

    Returns a edscrapers.scrapers.base.models.Source object.
    If any of the required parameters are not present, None is return
    """

    # check the required parameters
    if (not source_url) or (not namespace):
        return None

    # cleanup the source_url i.e. remove all query parameters
    source_url = url_query_param_cleanup(source_url, include_query_param=[])
    
    # make a request for html page contained in the provided url
    res = requests.get(source_url, verify=False)

    # ensure that the response text gotten is a string
    if not isinstance(getattr(res, 'text', None), str):
        return None

    try:
        soup_parser = bs4.BeautifulSoup(res.text, 'html5lib')
    except:
        return None
    
    source = Source()
    source['source_url'] = source_url
    # get the Source title
    if soup_parser.head.find(name='title'):
        source['source_title'] = str(soup_parser.head.\
                            find(name='title').string).strip()
    else:
        source['source_title'] = '[no title]'
    
    source['source_id'] =\
        f'{hashlib.md5(source["source_url"].encode("utf-8")).hexdigest()}-{hashlib.md5(namespace.encode("utf-8")).hexdigest()}'

    return source


def url_query_param_cleanup(url: str, include_query_param: list=None,
                         exclude_query_param: list=None) -> str:
    """ function helps to remove querystring name/value pairs from the provided url.
    Returning the 'cleaned up' version of the url (without the specified query parameters).
    See PARAMETERS for details

    PARAMETERS:
    - url: represents a valid url which can be parsed by urllib.parse.split()
    
    - include_query_param: a list containing the name(s) of query parameters to 
    be removed from url. if list is None (which is the default), no parameters are
    stripped. 
    If list is empty, ALL parameters are stripped

    - exclude_query_param: a list containing the name(s) of query parameters NOT to be 
    removed from url. That is, ALL available query parameters will
    be removed from url EXCEPT those provided in this list.
    if list is None (which is the default), ALL parameters are excluded from stripping.
    if list is empty, all parameters are excluded from being stripped provided
    'include_query_param' is None.

    NOTE: in terms of precedence, 'include_query_param' has a higher order than
    'exclude_query_param'. That is if both 'include_query_param' and
    'exclude_query_param' are specified AND 'include_query_param' is NOT None,
    then 'include_query_param' will be applied and 'exclude_query_param' disregarded.

    Returns: function returns a url that has been
    stripped of querystring name/value pairs"""

    split_url = urllib.parse.urlsplit(url) # holds the split components of the url
    stripped_url = url # holds the url string after stripping query parameters

    # if no query parameters are included or excluded,
    if include_query_param is None and exclude_query_param is None:
        # return a 'cleaned up' (but equivalent) version of the provided url
        stripped_url = urllib.parse.urlunsplit(urllib.parse.urlsplit(url))
        return stripped_url # return stripped url

    # if 'include_query_param' is empty list or includes params to be stripped
    if include_query_param is not None and len(include_query_param) >= 0:
        # get the query component of the url
        query_str = split_url.query
        if query_str == "": # no query string contained in the provided url
            # return a 'cleaned up' (but equivalent) version of the provided url
            stripped_url = urllib.parse.urlunsplit(urllib.parse.urlsplit(url))
        else: # query string was provided
            query_str_dict = urllib.parse.parse_qs(query_str)
            query_str_dict2 = dict(query_str_dict)
            for key in query_str_dict.keys(): # cycle through the query param names
                    # if any query param name in 'include_query_param' or 'include_query_param' 
                if key in include_query_param or len(include_query_param) == 0:
                    del query_str_dict2[key] # delete the query param
            # convert the ammended query_param dict to a querystring
            query_str = urllib.parse.urlencode(query_str_dict2, doseq=True)
            stripped_url = urllib.parse.urlunsplit(urllib.parse.\
                                                    SplitResult(split_url.scheme,
                                                                split_url.netloc,
                                                                split_url.path,
                                                                query_str,
                                                                split_url.fragment))
        return stripped_url # return stripped url
    
    # if 'exclude_query_param' is empty list or includes params to be excluded
    if exclude_query_param is not None and len(exclude_query_param) >= 0:
        # get the query component of the url
        query_str = split_url.query
        if query_str == "": # no query string contained in the provided url
            # return a 'cleaned up' (but equivalent) version of the provided url
            stripped_url = urllib.parse.urlunsplit(urllib.parse.urlsplit(url))
        else: # query string was provided
            query_str_dict = urllib.parse.parse_qs(query_str)
            query_str_dict2 = dict(query_str_dict)
            for key in query_str_dict.keys(): # cycle through the query param names
                    # if any query param name not in 'exclude_query_param' and 'exclude_query_param' is not empty
                if key not in exclude_query_param and len(exclude_query_param) > 0:
                    del query_str_dict2[key] # delete the query param
            # convert the ammended query_param dict to a querystring
            query_str = urllib.parse.urlencode(query_str_dict2, doseq=True)
            stripped_url = urllib.parse.urlunsplit(urllib.parse.\
                                                    SplitResult(split_url.scheme,
                                                                split_url.netloc,
                                                                split_url.path,
                                                                query_str,
                                                                split_url.fragment))
        return stripped_url # return stripped url
