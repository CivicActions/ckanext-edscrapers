import bs4
import re
import json
import requests

from slugify import slugify

import edscrapers.scrapers.base.helpers as h
import edscrapers.scrapers.base.parser as base_parser
from edscrapers.scrapers import base
from edscrapers.scrapers.base.models import Dataset, Resource

def parse(res, publisher):
    """ function parses content to create a dataset model
    or return None if no resource in content"""

    # ensure that the response text gotten is a string
    if not isinstance(getattr(res, 'text', None), str):
        return None

    try:
        soup_parser = bs4.BeautifulSoup(res.text, 'html5lib')
    except:
        return None
        
    # check if the content contains any of the data extensions
    if soup_parser.body.find(name='a', href=base_parser.resource_checker,
                             recursive=True) is None:
        # no resource on this page, so return None
        return None

    # if code gets here, at least one resource was found

    dataset_containers = soup_parser.body.find_all(name='div',
                                                   id='maincontent',
                                                   recursive=True)
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

        # dataset source url
        dataset['source_url'] = res.url

        # dataset title
        if soup_parser.head.find(name='meta',attrs={'name': 'DC.title'}) is None:
            dataset['title'] = str(soup_parser.head.\
                                find(name='title').string).strip()
        else:
            dataset['title'] = soup_parser.head.find(name='meta',
                                attrs={'name': 'DC.title'})['content']

        # dataset name
        dataset['name'] = slugify(dataset['title'])
        dataset['publisher'] = publisher

        # description
        if soup_parser.head.find(name='meta', attrs={'name': 'DC.description'}) is None:
            dataset['notes'] = dataset['title']
        else:
            dataset['notes'] = soup_parser.head.\
                                find(name='meta', 
                                attrs={'name': 'DC.description'})['content']

        # tags
        if soup_parser.head.find(name='meta', attrs={'name': 'keywords'}) is None:
            dataset['tags'] = ''
        else:
            dataset['tags'] = soup_parser.head.\
                                find(name='meta', 
                                attrs={'name': 'keywords'})['content']
    
        # date
        if soup_parser.head.find(name='meta', attrs={'name': 'DC.date.valid'}) is None:
            dataset['date'] = ''
        else:
            dataset['date'] = soup_parser.head.\
                                    find(name='meta', 
                                    attrs={'name': 'DC.date.valid'})['content']
        
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
                resource['name'] = str(child).strip()
                if re.sub(r'(<.+>)', '',
                re.sub(r'(</.+>)', '', resource['name'])) != "":
                    break
            resource['name'] = re.sub(r'(</.+>)', '', resource['name'])
            resource['name'] = re.sub(r'(<.+>)', '', resource['name'])


            if resource_link.find_parent(class_='contentText').\
                find_previous_sibling(class_='headersLevel2'):

                # concatenate the text content of parents with 
                # class 'headersLevel1' & 'headersLevel2'
                resource['description'] = str(resource_link.\
                                        find_parent(class_='contentText').\
                                            find_previous_sibling(class_='headersLevel1').\
                                                contents[0]).strip() +\
                                            " - " + str(resource_link.\
                                        find_parent(class_='contentText').\
                                            find_previous_sibling(class_='headersLevel2').\
                                                contents[1]).strip()
                resource['description'] = re.sub(r'(</.+>)', '', resource['description'])
                resource['description'] = re.sub(r'(<.+>)', '', resource['description'])
            else:
                # concatenate the text content of parents with
                # class 'headersLevel1' & 'contentText'
                resource['description'] = str(resource_link.\
                                        find_parent(class_='contentText').\
                                            find_previous_sibling(class_='headersLevel1').\
                                                contents[0]).strip() +\
                                            " - " + str(resource_link.\
                                        find_parent(class_='contentText').\
                                                contents[0].string or resource_link.\
                                        find_parent(class_='contentText').\
                                                contents[0]).strip()
                resource['description'] = re.sub(r'(</.+>)', '', resource['description'])
                resource['description'] = re.sub(r'(<.+>)', '', resource['description'])
            # after getting the best description possible, remove any " - "
            # and trailing white space
            resource['description'] = re.sub(r'^\s+\-\s+', '', resource['description'])
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
