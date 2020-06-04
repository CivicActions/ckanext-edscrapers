import os
from pathlib import Path
from urllib.parse import urlparse
from urllib.parse import urljoin

import edscrapers.transformers.base.helpers as h
from edscrapers.cli import logger
from edscrapers.transformers.base.helpers import traverse_output, read_file
from edscrapers.transformers.datajson.models import Catalog, Dataset, Resource, Organization, Source, Collection

OUTPUT_DIR = os.getenv('ED_OUTPUT_PATH')
resources_common_names = ['excel', 'doc', 'download excel', 'download se excel',
                        'dowload doc', 'download this table as an excel file.',
                        'download this table as a microsoft excel spreadsheet',
                        'excel download', 'download standard error excel']

dataset_title_list = []
dataset_identifier_list = []


def transform(name, input_file=None):
    if input_file is None:
        file_list = traverse_output(name)
    else:
        try:
            with open(input_file, 'r') as fp:
                file_list = [line.rstrip() for line in fp]
        except:
            logger.warning(f'Cannot read from list of output files at {input_file}, falling back to all collected data!')
            file_list = traverse_output(name)

    logger.debug(f'{len(file_list)} files to transform.')

    catalog = Catalog()
    catalog.catalog_id = "datopian_data_json_" + (name or 'all')


    # keep track/stata for item transformed
    datasets_number = 0
    resources_number = 0
    sources_number = 0
    collections_number = 0

    # loop through the list of filepaths to be transformed
    for file_path in file_list:

        data = read_file(file_path)
        if not data:
            continue

        dataset = _transform_scraped_dataset(data, name)

        if not dataset: # no dataset was returned (i.e. dataset probably marked for removal)
            continue
        
        catalog.datasets.append(dataset)

        datasets_number += 1
        resources_number += len(dataset.distribution)

    # TODO WORK FROM BELOW HERE
    # get the list of Sources for this catalog
    catalog_sources = list()
    try:
        # read the list of preprocessed (but still 'raw') Sources from file
        catalog_sources = read_file(f"{h.get_output_path('sources')}/{(name or 'all')}.sources.json")
        # transform the list of preprocessed Sources to a list of Source objects acceptable for the catalog object
        catalog_sources = _transform_preprocessed_sources(catalog_sources)
    except:
        logger.warning(f'"sources transformer" output file ({(name or "all")}.sources.json) not found. This datajson output will have no "source" field')
    
    # add the list of Source objects to the catalog
    catalog.sources = catalog_sources or []
    # update the number fo transformed Sources
    sources_number = len(catalog_sources or [])
    
    # get the list of Collections for this catalog
    catalog_collections = list()
    try:
        # read the list of preprocessed (but still 'raw') Collections from file
        catalog_collections = read_file(f"{h.get_output_path('collections')}/{(name or 'all')}.collections.json")
        # transform the list of preprocessed Collections to a list of Collection objects acceptable for the catalog object
        catalog_collections = _transform_preprocessed_collections(catalog_collections)
    except:
        logger.warning(f'"sources transformer" output file ({(name or "all")}.collections.json) not found. This datajson output will have no "collection" field')
    
    # add the list of Collection objects to the catalog
    catalog.collections = catalog_collections or []
    # update the number fo transformed Collections
    collections_number = len(catalog_collections or [])

    # validate the catalog object
    if not catalog.validate_catalog(pls_fix=True):
        logger.error(f"catalog validation Failed! Ending transform process")
        return

    logger.debug('{} Sources transformed.'.format(sources_number))
    logger.debug('{} Collections transformed.'.format(collections_number))
    logger.debug('{} datasets transformed.'.format(datasets_number))
    logger.debug('{} resources transformed.'.format(resources_number))

    output_path = h.get_output_path('datajson')
    file_path = os.path.join(output_path, f'{(name or "all")}.data.json')
    with open(file_path, 'w') as output:
        output.write(catalog.dump())
        logger.debug(f'Output file: {file_path}')

    h.upload_to_s3_if_configured(file_path, f'{(name or "all")}.data.json')


def _transform_scraped_dataset(data: dict, target_dept='all'):

    # check if 'data' has sanitised data to be adopted
    if data.get('_clean_data', None):
        # there is sanitised data to be adopted into the datajson
        if data['_clean_data'].get('_remove_dataset', False) is True:
            # the 'data' has been flagged for removal
            return None # exit function with no Dataset instance
        else:
            # update 'data' with the keys/value from _clean_data
            data.update(data['_clean_data'])

    dataset = Dataset()

    scraped_from = data.get('source_url')
    if '|' in scraped_from:
        scraped_from = scraped_from.split('|')[0]

    dataset.scraped_from = scraped_from
    
    ### removing leading and trailing withespaces from title
    title = data.get('title').strip()
    # ensure datasets have a unique title
    if title and title not in dataset_title_list:
        dataset.title = title
        dataset_title_list.append(title)
    else:
        dataset.title = h.transform_dataset_title(title, scraped_from)

    identifier = data.get('name')
    # ensure datasets have a unique identifier
    if identifier in dataset_identifier_list:
        identifier = h.transform_dataset_identifier(title, scraped_from)
    dataset.identifier = identifier
    dataset_identifier_list.append(identifier)

    if data.get('tags'):
        dataset.keyword = h.transform_keywords(data.get('tags'))
    
    if data.get('notes'):
        dataset.description = data.get('notes')

    if data.get('date'):
        dataset.modified = data.get('date')

    publisher = Organization()
    if type(data.get('publisher')) is dict:
        publisher.name = data.get('publisher', {'name': 'edgov'})['name']
        publisher.sub_organization_of = data.get('publisher', {}).get('subOrganizationOf', None)
    else:
        # if no publisher present, use the target_dept - part after last dot, if applicable
        # (e.g. both "oese" and "edgov.oese" will yield "oese")
        publisher.name = data.get('publisher', target_dept.split('.')[-1])
    dataset.publisher = publisher

    contactPoint = {
        "@type": "vcard:Contact",
    }

    if data.get('contact_person_name'):
        contactPoint['fn'] = data.get('contact_person_name')
    else:
        contactPoint['fn'] = 'n/a' #h.get_office_name(target_dept)

    if data.get('contact_person_email'):
        contactPoint['hasEmail'] = "mailto:" + data.get('contact_person_email')
    else:
        contactPoint['hasEmail'] = f'mailto:{target_dept}@ed.gov'

    dataset.contactPoint = contactPoint

    if data.get('accessLevel'):
        dataset.accessLevel = data.get('accessLevel')

    if not len(dataset.bureauCode) > 0:
        dataset.bureauCode = ["018:40"]

    if not len(dataset.programCode) > 0:
        dataset.programCode = ["018:000"]

    if not len(dataset.keyword) > 0:
        dataset.keyword = [(target_dept or 'all')]

    distributions = []
    resources = data.get('resources')
    for resource in resources:
        distribution = _transform_scraped_resource(target_dept, resource)
        distributions.append(distribution)

    dataset.distribution = distributions

    # get the 'source' attribute for the dataset object
    dataset_source = _transform_scraped_source(data)
    if dataset_source:
        dataset.source.append(dataset_source)
    
    # get the 'collection' attribute for the dataset object
    dataset_collection = _transform_scraped_collection(data)
    if dataset_collection:
        dataset.collection.append(dataset_collection)
    
    # get levelOfData
    if data.get('level_of_data', None):
        dataset.levelOfData = data.get('level_of_data')

    return dataset

def _transform_scraped_resource(target_dept, resource):

    distribution = Resource()

    downloadURL = str()
    if urlparse(resource.get('url')).scheme:
        downloadURL = resource.get('url')
    else:
        downloadURL = urljoin(resource.get('source_url'), resource.get('url'))

    #remove spaces in links
    downloadURL = downloadURL.replace(' ','%20')
    distribution.downloadURL = downloadURL

    resource_name = str(resource.get('name'))
    if resource_name and resource_name.lower() not in resources_common_names:
        distribution.title = resource.get('name')
    else:
        distribution.title = h.extract_resource_name_from_url(distribution.downloadURL)

    if resource.get('description'):
        distribution.description = resource.get('description')

    if resource.get('format'):
        distribution.resource_format = resource.get('format')
        distribution.mediaType = h.get_media_type(resource.get('format'))
    else:
        extension = h.extract_resource_format_from_url(distribution.downloadURL)
        if extension:
            distribution.resource_format = extension
            distribution.mediaType = h.get_media_type(extension)
    
    if resource.get('headers'):
        distribution.headerMetadata = resource.get('headers')

    return distribution


def _transform_scraped_source(data: dict):
    """
    function is a private helper.
    function returns the Source object from raw data provided
    """

    source = None
    if data.get('collection', None) and data['collection'].get('source', None):
        source = Source()
        source.id = data['collection']['source'].get('source_id')
        source.title = data['collection']['source'].get('source_title')
        source.url = data['collection']['source'].get('source_url')
    
    return source

def _transform_scraped_collection(data: dict):
    """
    function is a private helper.
    function returns the Collection object from raw data provided
    """

    collection = None
    if data.get('collection', None):
        collection = Collection()
        collection.id = data['collection'].get('collection_id')
        collection.title = data['collection'].get('collection_title')
        collection.url = data['collection'].get('collection_url')
        
        source = None
        # get a Source object from the raw data
        source = _transform_scraped_source(data)
        if source:
            collection.sources.append(source)
    
    return collection

def _transform_preprocessed_sources(sources_list: list):
    """ function is a private helper.
    function takes a list of 'raw' Source json/dicts and transforms them to a
    list of Source objects.
    NOTE:
    for details on the expected structure of the raw Source json/dict, see the
    output from the `sources transformer`
    """
    
    if not sources_list or len(sources_list) == 0: # sources not provided
        return None
    
    source_obj_list = [] # holds the list of Source objects

    # loop through the provided 'sources_list'
    for raw_source in sources_list:
        source_obj = Source() # create a Source object
        # populate the Source object from the raw source
        source_obj.id = raw_source.get('source_id')
        source_obj.title = raw_source.get('source_title')
        source_obj.url = raw_source.get('source_url')
        # add the Source object to the list of Source objects
        source_obj_list.append(source_obj)

    return source_obj_list # return the list of Source objects


def _transform_preprocessed_collections(collections_list: list):
    """ function is a private helper.
    function takes a list of 'raw' Collection json/dicts and transforms them to a
    list of Collection objects.
    NOTE:
    for details on the expected structure of the raw Collection json/dict, see the
    output from the `collections transformer`
    """
    
    if not collections_list or len(collections_list) == 0: # collections not provided
        return None
    
    collection_obj_list = [] # holds the list of Collection objects

    # loop through the provided 'collections_list'
    for raw_collection in collections_list:
         # create a Collection object, using the private helper
        collection_obj = _transform_scraped_collection(dict(collection=raw_collection))
        # add the Collection object to the list of Collection objects
        collection_obj_list.append(collection_obj)

    return collection_obj_list # return the list of Collection objects
