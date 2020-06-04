"""Generic sites.ed.gov parser"""

import json
import requests

import bs4 # pip install beautifulsoup4
from slugify import slugify

import edscrapers.scrapers.base.helpers as h
import edscrapers.scrapers.base.parser as base_parser
from edscrapers.scrapers.base.models import Dataset, Resource, Collection, Source


def parse(res, publisher) -> dict:
    """ function parses content to create a dataset model """

    # create parser object
    soup_parser = bs4.BeautifulSoup(res.text, 'html5lib')

    dataset_containers = soup_parser.body.find_all(name='div', id='page', recursive=True)

    # check if this page is a collection (i.e. collection of datasets)
    if len(dataset_containers) > 0: # this is a collection
        # create the collection (with a source)
        collection = h.extract_dataset_collection_from_url(collection_url=res.url,
                                        namespace="all",
                                        source_url=\
                                        str(res.request.headers.get(str(b'Referer',
                                                                    encoding='utf-8'), b''), 
                                            encoding='utf-8'))

    # print(dataset_containers)

    for container in dataset_containers:
        # create dataset model dict
        dataset = Dataset()
        dataset['source_url'] = res.url

        # import ipdb; ipdb.set_trace()
        try:
            dataset['title'] = str(container.find(class_='site-title').string).strip()
        except:
            dataset['title'] = str(soup_parser.head.\
                                find(name='title').string).strip()
        # replace all non-word characters (e.g. ?/) with '-'
        dataset['name'] = slugify(dataset['title'])
        # get publisher from parent package name
        dataset['publisher'] = publisher

        try:
            dataset['notes'] = str(container.find(_class='site-description').string).\
                                  strip()
        except:
            dataset['notes'] = dataset['title']

        dataset['tags'] = ''
        dataset['date'] = ''
        dataset['contact_person_name'] = ""
        dataset['contact_person_email'] = ""

        # specify the collection which the dataset belongs to
        if collection: # if collection exist
            dataset['collection'] = collection

        dataset['resources'] = list()

        # add  resources from the 'container' to the dataset
        page_resource_links = container.find_all(name='a',
                                                 href=base_parser.resource_checker,
                                                 recursive=True)
        for resource_link in page_resource_links:
            resource = Resource(source_url = res.url,
                                url = resource_link['href'],
                                name = str(resource_link.string).strip())

            # get the format of the resource from the file extension of the link
            resource_format = resource_link['href']\
                            [resource_link['href'].rfind('.') + 1:]
            resource['format'] = resource_format

            # Add header information to resource object
            resource['headers'] = h.get_resource_headers(res.url, resource_link['href'])

            # add the resource to collection of resources
            dataset['resources'].append(resource)


        # if this dataset alread has data resource files look for
        # document resource files
        if len(dataset['resources']) > 0:
            yield dataset
