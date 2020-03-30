""" parser3 for nces pages """

import re

import bs4 # pip install beautifulsoup4
from slugify import slugify

import edscrapers.scrapers.base.helpers as h
import edscrapers.scrapers.base.parser as base_parser
from edscrapers.scrapers.base.models import Dataset, Resource


def parse(res) -> dict:
    """ function parses content to create a dataset model """

    # create parser object
    soup_parser = bs4.BeautifulSoup(res.text, 'html5lib')

    dataset_containers = soup_parser.body.select('div.MainContent')
    for container in dataset_containers:
        # create dataset model dict
        dataset = Dataset()
        dataset['source_url'] = res.url

        if (soup_parser.head.find(name='meta',attrs={'name': 'DC.title'}) is None)\
            or (soup_parser.head.find(name='meta',attrs={'name': 'DC.title'})['content']\
                is None or\
                    soup_parser.head.find(name='meta',attrs={'name': 'DC.title'})['content'] == ""):
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
            # the page structure has NO description available for resources
            resource['description'] = ''

            # get the format of the resource from the file extension of the link
            resource_format = resource_link['href']\
                            [resource_link['href'].rfind('.') + 1:]
            resource['format'] = resource_format
            resource['headers'] = requests.get(resource_link['href']).headers
            # add the resource to collection of resources
            dataset['resources'].append(resource)
        
        # check if created dataset has resources attached.
        if len(dataset['resources']) == 0: # no resources so don't yield it
            continue # skip this loop

        yield dataset
