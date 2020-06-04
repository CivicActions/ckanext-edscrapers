""" parser for edgov pages """

import re
import requests

import bs4 # pip install beautifulsoup4
from slugify import slugify

import edscrapers.scrapers.base.helpers as h
import edscrapers.scrapers.base.parser as base_parser
from edscrapers.scrapers.base.models import Dataset, Resource


def parse(res) -> dict:
    """ function parses content to create a dataset model """

    # create parser object
    soup_parser = bs4.BeautifulSoup(res.text, 'html5lib')

    dataset_containers = soup_parser.find_all(name='body')
    
    # check if this page is a collection (i.e. collection of datasets)
    if len(dataset_containers) > 0: # this is a collection
        # create the collection (with a source)
        collection = h.extract_dataset_collection_from_url(collection_url=res.url,
                                        namespace="all",
                                        source_url=\
                                        str(res.request.headers.get(str(b'Referer',
                                                                    encoding='utf-8'), b''), 
                                            encoding='utf-8'))

    for container in dataset_containers:
        # create dataset model dict
        dataset = Dataset()
        dataset['source_url'] = res.url

        if soup_parser.head.find(name='meta',attrs={'name': 'DC.title'}) is None:
            dataset['title'] = str(soup_parser.head.\
                                find(name='title').string).strip()
        else:
            dataset['title'] = soup_parser.head.find(name='meta',
                                           attrs={'name': 'DC.title'})['content']

        # replace all non-word characters (e.g. ?/) with '-'
        dataset['name'] = slugify(dataset['title'])
        if soup_parser.head.find(name='meta', attrs={'name': 'ED.office'}) is None:
            dataset['publisher'] = __package__.split('.')[-2]
        else:
            dataset['publisher'] = soup_parser.head.\
                                find(name='meta', attrs={'name': 'ED.office'})['content']
        
        if soup_parser.head.find(name='meta', attrs={'name': 'DC.description'}) is None:
            dataset['notes'] = dataset['title']
        else:
            dataset['notes'] = soup_parser.head.\
                                find(name='meta', attrs={'name': 'DC.description'})['content']

        if soup_parser.head.find(name='meta', attrs={'name': 'keywords'}) is None:
            dataset['tags'] = ''
        else:
            dataset['tags'] = soup_parser.head.\
                                find(name='meta', attrs={'name': 'keywords'})['content']
    
        if soup_parser.head.find(name='meta', attrs={'name': 'DC.date.valid'}) is None:
            dataset['date'] = ''
        else:
            dataset['date'] = soup_parser.head.\
                                    find(name='meta', attrs={'name': 'DC.date.valid'})['content']
        
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
            resource = Resource(source_url=res.url,
                                url=resource_link['href'])
            # get the resource name iteratively
            for child in resource_link.parent.children:
                if resource_link.parent.name == 'td':
                    resource['name'] = str(resource_link.find_parent(name='tr').contents[1]).strip()
                else:
                    resource['name'] = str(child).strip()
                if re.sub(r'(<.+>)', '',
                re.sub(r'(</.+>)', '', resource['name'])) != "":
                    break
            resource['name'] = re.sub(r'(</.+>)', '', resource['name'])
            resource['name'] = re.sub(r'(<.+>)', '', resource['name'])

            if resource_link.parent.parent.find(name=True):

                # concatenate the text content of parents with 
                # resource name
                resource['description'] = str(resource_link.parent.parent.find(name=True)).strip() +\
                                            " - " + str(resource['name']).strip()
                resource['description'] = re.sub(r'(</.+>)', '', resource['description'])
                resource['description'] = re.sub(r'(<.+>)', '', resource['description'])
                resource['description'] = re.sub(r'^\s+\-\s+', '', resource['description'])
            else:
                # use the resource name for description
                resource['description'] = str(resource['name']).strip()
                resource['description'] = re.sub(r'(</.+>)', '', resource['description'])
                resource['description'] = re.sub(r'(<.+>)', '', resource['description'])
            # after getting the best description possible, strip any white space
            resource['description'] = resource['description'].strip()

            # get the format of the resource from the file extension of the link
            resource_format = resource_link['href']\
                            [resource_link['href'].rfind('.') + 1:]
            resource['format'] = resource_format

            # Add header information to resource object
            resource['headers'] = h.get_resource_headers(res.url, resource_link['href'])

            # add the resource to collection of resources
            dataset['resources'].append(resource)
        if len(dataset['resources']) == 0:
            continue

        yield dataset
