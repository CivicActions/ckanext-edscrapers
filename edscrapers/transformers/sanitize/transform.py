""" module handles the sanitising of datajson output """

import os
import json
from pathlib import Path
import urllib
import re

from edscrapers.cli import logger
from edscrapers.transformers.base import helpers as h
from edscrapers.transformers.sanitize.helpers import categories as group_map


OUTPUT_DIR = os.getenv('ED_OUTPUT_PATH') # get the output directory

def transform(name=None, input_file=None):

    if input_file is None:
        file_list = h.traverse_output(name)
    else:
        try:
            with open(input_file, 'r') as fp:
                file_list = [line.rstrip() for line in fp]
        except:
            logger.warning(f'Cannot read from list of output files at {input_file}, falling back to all collected data!')
            file_list = h.traverse_output(name)
    
    # loop through filepath in file list
    for file_path in file_list:
        # read the json data in each filepath
        data = h.read_file(file_path)
        if not data: # if data is None
            continue
        # mark as private datasets that have certain keywords in their data
        data = _mark_private(data, search_words=['conference', 'awards',
                                                'user guide', 'applications'])

        # mark of removal datasets that have certain keywords
        data = _remove_dataset(data, search_words=['photo', 'foto', 'photos', 'fotos'])

        # REMOVE UNWANTED STRING FROM THE VALUE OF A DATASET'S KEY
        # 1. remove 'table [0-9].' from beginning of dataset title
        data = _strip_unwanted_string(data, r'^table [0-9a-z]+(-?[a-z])?\.', 
                                      dict_key='title')
        
        # set the 'level of data' for the dataset
        data = _set_dataset_level_of_data(data)

        # assign the dataset to groups
        # according to https://www2.ed.gov/rschstat/catalog/index.html
        data = _set_dataset_groups(data)
      
        # remove the old format for collections / sourcs
        data = _remove_old_sources_collections(data)
        
        # write modified dataset back to file
        h.write_file(file_path, data)


def _mark_private(dataset: dict, search_words=[], add_word_tag=True,
                  mark_as_private=True) -> dict:
    """ private helper function.
    FUNCTION ONLY adds/modifies the '_clean_data' key of 'dataset' during operations.

    searches the dataset title for provided search_words.
    if any search_words are found, will OPTIONALLY marks the datasets as private and
    adds the search word as a tag to the list of keywords"""

    if dataset.get('title') is None:
        return dataset
    
    dataset['title'] = dataset['title'].strip()

    # get the '_clean_data' key of dataset
    clean_data = dataset.setdefault('_clean_data', {})
    # get the title key from clean_data or use those from dataset
    title = clean_data.get('title', dataset['title'].strip())
    # get the tags key from clean_data or use those from dataset
    tags = clean_data.get('tags', dataset.get('tags', '').strip())


    for word in search_words:
        # check if word is in dataset title
        if re.search('\\b'+ re.escape(word) + '\\b', title, re.IGNORECASE):
            # word is in title
            if add_word_tag and word.lower().replace(' ', '-')\
                not in h.transform_keywords(tags):
                # word needs to be added to tag
                tags = h.transform_keywords(tags)
                tags.append(word.lower().replace(' ', '-'))
                tags = ';'.join(tags)
                clean_data['tags'] = tags
            # mark dataset as 'private;
            if mark_as_private:
                clean_data['accessLevel'] = 'non-public'

    if len(clean_data.keys()) > 0: # if '_clean_data' has keys
        dataset['_clean_data'] = clean_data # update dataset
    else: # else no keys
        del dataset['_clean_data'] # delete '_clean_data' key from dataset

    return dataset


def _remove_dataset(dataset: dict, search_words=[]) -> dict:
    """ private helper function.
    FUNCTION ONLY adds/modifies the '_clean_data' key of 'dataset' during operations.

    searches the dataset title for provided search_words.
    if any search_words are found, will flag the dataset for deletion/removal i.e.
    dataset should NOT be harvested.
    
    A dataset is flagged for deletion by adding the _remove_dataset key to the 
    _clean_data key/dict pair """

    if dataset.get('title') is None:
        return dataset
    
    dataset['title'] = dataset['title'].strip()

    # get the '_clean_data' key of dataset
    clean_data = dataset.setdefault('_clean_data', {})
    # get the title key from clean_data or use those from dataset
    title = clean_data.get('title', dataset['title'].strip())
     # if dataset already flagged for deletion/removal
    if clean_data.get('_remove_dataset') and\
        clean_data['_remove_dataset'] is True:
        return dataset # exit function


    for word in search_words:
        # check if word is in dataset title
        if re.search('\\b'+ re.escape(word) + '\\b', title, re.IGNORECASE):
            # word is in title, so flag datset for removal/deletion
            clean_data['_remove_dataset'] = True
            break # exit foor loop since dataset has been marked

    # Temporary fix for removing the 'edgov' datasets from the resulting datajson file
    # FIXME set this to True once parsing / sanitizing for the publisher is improved
    try:
        if dataset['publisher'].get('name') == 'edgov':
            clean_data['_remove_dataset'] = True
    except:
        if dataset['publisher'] == 'edgov':
            clean_data['_remove_dataset'] = True

    if len(clean_data.keys()) > 0: # if '_clean_data' has keys
        dataset['_clean_data'] = clean_data # update dataset
    else: # else no keys
        del dataset['_clean_data'] # delete '_clean_data' key from dataset

    return dataset


def _strip_unwanted_string(dataset: dict, regex_str: str,
                           dict_key='title', count=0) -> dict:
    """ private helper function.
    FUNCTION ONLY adds/modifies the '_clean_data' key of 'dataset' during operations.

    performs a case-insensitive search for 'regex_str' on the specified
    dataset key (dict_key) and removes the regex_str from dataset[dict_key] value.

    'count' represents the number of types 'regex_str' will be removed from
    dataset[dict_key]. 0 (the defualt) means remove all occurrences of 'regex_str'
    
    NOTE: the value of dataset[dict_key] MUST BE a string
    """

    if dataset.get(dict_key) is None:
        return dataset
    
    # get the '_clean_data' key of dataset
    clean_data = dataset.setdefault('_clean_data', {})

    # get the dict_key value from clean_data or use those from dataset
    dict_key_val = clean_data.get(dict_key, dataset[dict_key]).strip()

    # remove regex_str from dict_key_val
    clean_key = re.sub(regex_str, '', dict_key_val,
                                  count=count, flags=re.IGNORECASE)

    if clean_key != dataset.get(dict_key):
        clean_data[dict_key] = clean_key

    if len(clean_data.keys()) > 0: # if '_clean_data' has keys
        dataset['_clean_data'] = clean_data # update dataset
    else: # else no keys
        del dataset['_clean_data'] # delete '_clean_data' key from dataset
    
    return dataset


def _set_dataset_level_of_data(dataset: dict) -> dict:
    """ private helper function.
    FUNCTION ONLY adds/modifies the '_clean_data' key of 'dataset' during operations.
    
    function sets the 'level_of_data' for the dataset.
    
    possible values are: ['national', 'state', 
    'district', 'school', 'individual', 
    'Institution of Higher Education', 
    'Accreditor', 'Grantee', 'Zip Code', 
    'Census Block', 'Census Tract']

    level of data is determined by examining each resource 'name' in the dataset.
    """
    if dataset.get('resources') is None:
        return dataset
    
    # get the '_clean_data' key of dataset
    clean_data = dataset.setdefault('_clean_data', {})

    level_of_data = set()

    # get the state names (used to determine if level of data is 'state')
    list_of_states = list(map(lambda state: state.lower(), h.get_country_states(None)))

    # loop through resources
    for resource in dataset['resources']:
        # if level_of_data already contain 'national' and 'state', no need to continue
        if 'national' in level_of_data and 'state' in level_of_data:
            break
        else:
            # if the string 'national' is found in the resource name or dataset title
            if 'national' not in level_of_data and\
                ('national' in resource.get('name', '').lower() or\
                    'national' in dataset.get('title', '').lower()):
                level_of_data.add('national') # add 'national'to level of data

            # loop through each State name in list_of_states
            for state in list_of_states:
                # check if State name is contained in resource name
                if state in resource.get('name', '').lower():
                    level_of_data.add('state')  # add 'state' to level of data
                    break # leave list_of_states loop

    # update 'level_of_data'
    if len(level_of_data) > 0:
        clean_data['level_of_data'] = list(level_of_data)
    
    if len(clean_data.keys()) > 0: # if 'clean_data' has keys
        dataset['_clean_data'] = clean_data # update dataset
    else: # else no keys
        del dataset['_clean_data'] # delete '_clean_data' key from dataset
    
    return dataset


def _set_dataset_groups(dataset: dict) -> dict:
    """ private helper function.
    FUNCTION ONLY adds/modifies the '_clean_data' key of 'dataset' during operations.
    
    function sets the 'groups' for the dataset.
    
    groups are collected from a mapping, produced following the structure
    in this page: https://www2.ed.gov/rschstat/catalog/index.html
    """

    def find_groups(url):
        """returns a set of group names, if applicable"""
        groups = []
        keys = group_map.keys()
        for key in keys:
            for base_url in group_map[key]:
                if base_url in url:
                    # print(f'Found: {base_url} in {url} for {key}')
                    groups.append(key)
                # else:
                #     print(f'Not found: {base_url} in {url} for {key}')
        return groups

    # get the '_clean_data' key of dataset
    clean_data = dataset.setdefault('_clean_data', {})
    groups = dataset.get('groups', [])
    new_groups = None

    if dataset.get('resources'):
        for resource in dataset['resources']:
            url = urllib.parse.urljoin(resource['source_url'], resource['url'])
            new_groups = find_groups(url)
            if new_groups:
                groups.extend(new_groups)

    if new_groups:
        clean_data['groups'] = list(set(groups))

    if len(clean_data.keys()) > 0: # if '_clean_data' has keys
        dataset['_clean_data'] = clean_data # update dataset
    else: # else no keys
        del dataset['_clean_data'] # delete '_clean_data' key from dataset

    return dataset


def _remove_old_sources_collections(dataset: dict) -> dict:
    """ private helper function.
    removes sources and collections that were produced by earlier
    implementations of their respective transformers"""

    if dataset.get('collection') is None or dataset.get('source'):
        return dataset

    # get the '_clean_data' key of dataset
    clean_data = dataset.setdefault('_clean_data', {})
    # get the title key from clean_data or use those from dataset
    collection = clean_data.get('collection', dataset.get('collection', []))
    # get the tags key from clean_data or use those from dataset
    source = clean_data.get('source', dataset.get('source', []))

    if type(collection) == dict:
        clean_data['collection'] = None
    if type(source) == dict:
        clean_data['source'] = None

    if len(clean_data.keys()) > 0: # if '_clean_data' has keys
        dataset['_clean_data'] = clean_data # update dataset
    else: # else no keys
        del dataset['_clean_data'] # delete '_clean_data' key from dataset

    return dataset
