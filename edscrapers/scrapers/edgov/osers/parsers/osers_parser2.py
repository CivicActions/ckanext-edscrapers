import re
import requests

import bs4
from slugify import slugify

import edscrapers.scrapers.base.helpers as h
import edscrapers.scrapers.base.parser as base_parser
from edscrapers.scrapers.base.models import Dataset, Resource


def parse(res):
    """ function parses content to create a dataset model """

    # ensure that the response text gotten is a string
    if not isinstance(getattr(res, 'text', None), str):
        return None

    # create parser object
    try:
        soup_parser = bs4.BeautifulSoup(res.text, 'html5lib')
    except:
        return None

    dataset_containers = soup_parser.body.find_all(class_='contentText',
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
        dataset['source_url'] = res.url

        # title
        if soup_parser.head.find(name='meta',attrs={'name': 'DC.title'}) is None:
            dataset['title'] = str(soup_parser.head.\
                                find(name='title').string).strip()
        else:
            dataset['title'] = soup_parser.head.find(name='meta',
                                    attrs={'name': 'DC.title'})['content']

        # name
        dataset['name'] = slugify(dataset['title'])
        
        # publisher
        if soup_parser.head.find(name='meta', attrs={'name': 'ED.office'}) is None:
            dataset['publisher'] = __package__.split('.')[-2]
        else:
            dataset['publisher'] = soup_parser.head.\
                                find(name='meta', attrs={'name': 'ED.office'})['content']
        
        # description
        if soup_parser.head.find(name='meta', attrs={'name': 'DC.description'}) is None:
            dataset['notes'] = str(soup_parser.body.find(class_='headersLevel1',
                                    recursive=True).string).strip()
        else:
            dataset['notes'] = soup_parser.head.\
                                find(name='meta', attrs={'name': 'DC.description'})['content']
        # if after searching, description is still not satisfactorily set
        if dataset['notes'] is None or str(dataset['notes']).strip() == "":
            # set description to document title
            dataset['notes'] = dataset['title']

        # tags
        if soup_parser.head.find(name='meta', attrs={'name': 'keywords'}) is None:
            dataset['tags'] = ''
        else:
            dataset['tags'] = soup_parser.head.\
                                find(name='meta', attrs={'name': 'keywords'})['content']
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
            try:
                resource['name'] = str(resource_link.find_parent(name='ul').\
                                find_previous_sibling(name=True))
            except:
                resource['name'] = str(resource_link.string).strip()
            resource['name'] +=  " " + str(resource_link.parent.contents[0]).strip()
            resource['name'] = re.sub(r'(</.+>)', '', resource['name'])
            resource['name'] = re.sub(r'(<.+>)', '', resource['name'])

            resource['description'] = str(resource_link.\
                find_parent(class_='contentText').contents[0].string).strip()

            resource['description'] = re.sub(r'(</.+>)', '', resource['description'])
            resource['description'] = re.sub(r'(<.+>)', '', resource['description'])

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
