""" module computes the weighted scores of data.json files and 
transforms the resources into a csv file 
with name 'datasets_weighted_scores_{yyyy_mm_dd}.csv' """

import urllib.parse
import os
import pandas as pd
from datetime import datetime as dt
from pathlib import Path

import edscrapers.transformers.base.helpers as h
from edscrapers.cli import logger
from edscrapers.transformers.rag import DATASET_WEIGHTING_SYS, TOTAL_WEIGHT # import weighting system & total weight

# get the output directory
OUTPUT_DIR = h.get_output_path('rag')


def transform(name=None, input_file=None, use_raw_datasets=False) -> pd.DataFrame:
    """ function transforms the datajson/datasets into
    a dataframe/csv containig data to be used for RAG analyses on
    the efficacy of the scraping toolkit to get viable/usable structured data from
    the unstructured data source.
    
    The function by default operates on/utilises datajson i.e.
    the json that is ready to be ingested by the ckan harvester;
    However, setting 'use_raw_datasets' to True means the function will
    operate on the raw, parsed data which was scraped from the data source.

    PARAMETERS
    - name: if provided must correspond to the name of a scraper.
    if 'use_raw_datasets' is False, file with the format '<name>.data.json'
    will be located in the datajson subdirectory of 'ED_OUTPUT_PATH/transformers'
    and read.
    if 'use_raw_datasets' is True, dataset files contained in the 'name'
    scrapers subdirectory of the 'ED_OUTPUT_PATH/scrapers' will be read
    
    input_file: if provided mut be a file with list of datajson or dataset files
    to read.

    If no parameters are provided, which is the default behaviour;
    then all datajson files contained in datajson subdirectory of
    'ED_OUTPUT_PATH/transformers' will be read.

    function returns the DataFrame containing the transformed datajson/dataset files
    """
    
    file_list = [] # holds the list of files which contain datajson/dataset
    datasets_list = [] # holds the data jsons gotten from files

    if use_raw_datasets == True: # work on raw datasets
        if not input_file: # no input file provided
            # loop over directory structure
            if name:
                # loop over <name> scraper output e.g nces
                file_list = h.traverse_output(name)
                # datasets = list of all <name> files
            else:
                # loop over everything
                file_list = h.traverse_output(None)
                # datasets = list of all JSON files
        else: # input file provided
            # read input_file, which is a list of files
            with open(input_file, 'r') as fp:
                try:
                    file_list = [line.rstrip() for line in fp]
                except Exception:
                    logger.warning(f'Cannot read from list of output files at {input_file}, falling back to all collected data!')
                    file_list = h.traverse_output(None)
    
    else: # work with processed/transformed datajson
        if not input_file: # no input file provided
            if name: # name of processed datajson is provided so get the file path
                file_list.append(Path(h.get_output_path('datajson'), f'{name}.data.json'))
            else: # name of processed datajson not provided
                file_list.extend(Path(h.get_output_path('datajson')).glob('*.json'))
        else: # input file provided
            # read input_file, which is a list of files
            with open(input_file, 'r') as fp:
                try:
                    file_list = [line.rstrip() for line in fp]
                except Exception:
                    logger.warning(f'Cannot read from list of output files at {input_file}, falling back to all collected data!')
                    file_list.extend(Path(h.get_output_path('datajson')).glob('*.json'))

    if use_raw_datasets == True: # work on raw datasets
        # read the contents in file_list
        for file_path in file_list:
            # read json from the file using helper
            data = h.read_file(file_path)
            # compute the weight score of the dataset
            compute_score(data, append_score=True, use_raw_datasets=True)
            datasets_list.append(data)
    else: # work with processed json data
        # read the contents in the file_list
        for file_path in file_list:
            # read json from file using helper function
            data = h.read_file(file_path)
            for dataset_dict in data.get('dataset', []): # loop through the datasets contained in data
                # compute the weighted score of the dataset
                compute_score(dataset_dict, append_score=True, use_raw_datasets=False)
                datasets_list.append(dataset_dict)


    if use_raw_datasets == True: # work on raw datasets
        # map the datasets to pandas format
        dataset_rows_list = map(lambda dataset: [dataset.get('publisher'),\
                                                dataset.get('source_url'), \
                                                dataset.get('_weighted_score'), \
                                                dataset.get('_weighted_score_ratio')], 
                                datasets_list)
    else: # work on processed datajson
        # map the dataset to pandas format
        dataset_rows_list = map(lambda dataset: [dataset.get('publisher')['name'],\
                                                dataset.get('scraped_from'), \
                                                dataset.get('_weighted_score'), \
                                                dataset.get('_weighted_score_ratio')], 
                                datasets_list)
    # create the pandas df
    weighted_datasets_scores_df = pd.DataFrame(dataset_rows_list,
                                                columns=['publisher',
                                                         'source url',
                                                         'weighted score',
                                                         'weighted score ratio'])
    
    # create a df that incorporates domain info
    weighted_datasets_scores_df2 = pd.DataFrame(columns=['domain'])
    weighted_datasets_scores_df2['domain'] = weighted_datasets_scores_df.\
            apply(lambda row: urllib.parse.\
                    urlparse(row['source url']).hostname.\
                        replace('www2.', 'www.').replace('www.', ''), axis=1)
    
    weighted_datasets_scores_df2['publisher'] = weighted_datasets_scores_df['publisher']
    weighted_datasets_scores_df2['source url'] = weighted_datasets_scores_df['source url']
    weighted_datasets_scores_df2['weighted score'] = weighted_datasets_scores_df['weighted score']
    weighted_datasets_scores_df2['weighted score ratio'] = weighted_datasets_scores_df['weighted score ratio']

    # create the output csv file name

    output_dated_dir = os.path.join(OUTPUT_DIR,
                                    f'{dt.now().year}-{dt.now().month}-{dt.now().day}')
    Path(output_dated_dir).mkdir(parents=True, exist_ok=True)
    
    if use_raw_datasets == True: # use raw datasets
        output_filename = "datasets_weighted_scores_{}_raw.csv".format(name or "all")
    else: # use processed datajson
        output_filename = "datasets_weighted_scores_{}.csv".format(name or "all")

    # create the fullpath weer file will be written
    fullpath = os.path.join(OUTPUT_DIR, output_filename)

    # write the dataframe to csv
    weighted_datasets_scores_df2.to_csv(fullpath, index=False)
    weighted_datasets_scores_df2.to_csv(os.path.join(output_dated_dir,
                                                     output_filename),
                                        index=False)
    # write the csv to S3 bucket
    h.upload_to_s3_if_configured(fullpath, f'{output_filename}')
    
    return weighted_datasets_scores_df2



def compute_score(dataset: dict, append_score=True, use_raw_datasets=False) -> dict:
    """ function computed the weighted score for the provided dataset.
    It uses the WEIGHTING SYSTEM provided in this package/module.
    
    If 'append_score' is True (the default), then the weighted score and 
    the weighted score ratio are added to the dataset as additional keys.
    The keys are '_weighted_score' and '_weighted_score_ratio'.

    'use_raw_datasets' is False (the default), the function operates
    on the processed datajson structure; if True, function operates on
    the raw/parsed dataset structure.
    
    function returns a dict with the two keys.
    """
    
    score = 0 # used to tally weighted score for the dataset or datajson
    
    if use_raw_datasets == True: # operate on raw datasets
        dict_key = 'dataset_key' # set the key used for computing score to dataset
    else:
        dict_key = 'datajson_key' # set the key used for computing score to datajson

    # loop through all the keys in the weighted system
    for weighted_value_dict in DATASET_WEIGHTING_SYS.values():
        # check if the current json schema has the attribute/key/metadata required
        if weighted_value_dict[dict_key] == '': # the key is not present
            score += 0 # that is a 'no score'
        else: # key is present in schema
            # check if the dataset provided for scoring has the metadata
            metadata_value = dataset.get(weighted_value_dict[dict_key], None)
            # check if the dataset has useful value
            if metadata_value is None or str(metadata_value).strip() == "":
                score += 0 # no useful value
            else: # there is useful value
                # score the dataset metadata based on the agreed weight
                score += weighted_value_dict['score']

    # check if score should be appended
    if append_score:
        dataset['_weighted_score'] = score
        dataset['_weighted_score_ratio'] = score / TOTAL_WEIGHT  
    
    return {'_weighted_score': score, '_weight_score_ratio': score / TOTAL_WEIGHT}


# TODO REMOVE THIS. THIS IS JUST FOR CONVENIENT TESTING
if __name__ == "__main__":
    transform(name='ocr')
