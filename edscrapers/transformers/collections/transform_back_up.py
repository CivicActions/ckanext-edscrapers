""" module transforms the raw dataset files (i.e. the results/output from scraping)
into a different json data structure referred to as Collections.
Each scraping output directory will have its own
collections file upon completion of the transformation. Files are titled
'{name}.collections.json' .
All transformation output is written into 'collections' subdirectory of the
'transformers' directory on 'ED_OUTPUT_PATH'
"""

import os
import json
from pathlib import Path
import re
from collections import Counter

from edscrapers.cli import logger
from edscrapers.transformers.base import helpers as h


OUTPUT_DIR = os.getenv('ED_OUTPUT_PATH') # get the output directory

# get this transformer's output directory
CURRENT_TRANSFORMER_OUTPUT_DIR = h.get_output_path('collections')


def transform(name=None, input_file=None):
    """
    function is responsible for transofrming raw datasets into Collections
    """

    if input_file is None: # no input file specified
        file_list = h.traverse_output(name) # run through all the files in 'name' directory
    else:
        try:
            with open(input_file, 'r') as fp:
                file_list = [line.rstrip() for line in fp]
        except:
            logger.warning(f'Cannot read from list of output files at {input_file}, falling back to all collected data!')
            file_list = h.traverse_output(name)
    
    collections_list = [] # holds the list of collections acquired from 'name' scraper directory
    # loop through filepath in file list
    for file_path in file_list:
        # read the json data in each filepath
        data = h.read_file(file_path)
        if not data: # if data is None
            continue

        # retrieve collection from dataset
        collection = extract_collection_from(dataset=data, use_key='collection')
        if not collection: # collection could not be retrieved
            continue
        # add collection to list
        collections_list.append(collection)

    # get a list of non-duplicate collections
    collections_list = get_distinct_collections_from(collections_list,
                                                     min_occurence_counter=2)
    # get the path were the gotten Collections will be saved to on local disk
    file_output_path = f'{CURRENT_TRANSFORMER_OUTPUT_DIR}/{(name or "all")}.collections.json'
    # write to file the collections gotten from 'name' scraped output
    h.write_file(file_output_path, collections_list)
    # write file the collections gotten from 'name' scraped out to S3 bucket
    h.upload_to_s3_if_configured(file_output_path, 
                                 f'{(name or "all")}.collections.json')


def extract_collection_from(dataset: dict, use_key: str='collection') -> dict:
    """ function is used to extract a Collection from the provided dataset 
    
    - use_key: the key within the dataset that houses the collection object
    """

    if not dataset.get(use_key, None): # if there is no collection present
        return None
    
    if len(dataset[use_key]) == 0: # empty key (no collection content)
        return None
    
    return dataset[use_key] # return extracted Collection


def get_distinct_collections_from(collection_list,
                                  min_occurence_counter: int=1) -> list:
    """ function returns a list of distinct/unique (non-duplicate) collections
    extracted from the provided collections list 
    
    PARAMETERS
    - collection_list: a list containing the Collections to extract distinct
    Collections from

    - min_occurence_counter: the operations used to identify a distinct Collection can 
    be instructed on how to identify a Collection for consideration. The
    'min_occurence_counter' instructs the algorithm to
    ignore/remove a Collection from the list of distinct collections if it does not
    occur/appear within the provided 'collection_list' at least that number of times.
    The default value is 1. Setting 'min_occurence_counter to < 1 will disable this
    check when creating a distinct/unique (non-duplicate) Collection list
    """

    if (not collection_list) or len(collection_list) == 0: # parameter not provided
        return None
    
    # get a 'mapped' collection_list for easy operation
    mapped_collections = map(lambda collection: collection.get('collection_id', 
                                                        collection['collection_title']),
                                   collection_list)
    
    # find out if minimum occurence checks should be performed
    min_occurence_counter = int(min_occurence_counter)
    if min_occurence_counter > 0: # perform minimum occcurence check
        collections_counter = Counter(mapped_collections) # Counter for how many times a Collection occurs
        count_keys = list(collections_counter.keys()) # create a list from the counter key/collection id
        for key in count_keys: # loop through each counter key/collection id
            if collections_counter[key] < min_occurence_counter: # if counter key/collection id < min_occurence counter
                # remove this key as it represents a Collection that occurs less than requested
                del collections_counter[key]
        # end of minimum occurence checks,
        # so, generate the 'mapped' collection list from the results of this check
        mapped_collections = collections_counter.elements()

    # get distinct (non-duplicate) 'mapped' collection_list
    mapped_collections = set(mapped_collections)

    distinct_collection_list = [] # holds the list of distinct collection objects
    # iterate through 'mapped_collection'
    for mapped_collection in mapped_collections:
        # iterate through 'collection_list'  parameter
        for collection in collection_list:
            # the collection has the same id or title as mapped_collection
            if collection.get('collection_id', collection['collection_title']) == mapped_collection:
                # add this collection to the list of distinct collection objects
                distinct_collection_list.append(collection)
                break # leave the inner loop
    
    return distinct_collection_list # return the distinct collection
