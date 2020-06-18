""" module transforms the raw dataset files (i.e. the results/output from scraping)
into a different json data structure referred to as Sources.
Each scraping output directory will have its own
sources file upon completion of the transformation. Files are titled
'{name}.sources.json' .
All transformation output is written into 'sources' subdirectory of the
'transformers' directory on 'ED_OUTPUT_PATH' """

import os
import sys
import json
import hashlib
from pathlib import Path
from collections import Counter
import re

from edscrapers.cli import logger
from edscrapers.transformers.base import helpers as h
from edscrapers.scrapers.base.graph import GraphWrapper


OUTPUT_DIR = os.getenv('ED_OUTPUT_PATH') # get the output directory

# get this transformer's output directory
CURRENT_TRANSFORMER_OUTPUT_DIR = h.get_output_path('sources')


def transform(name=None, input_file=None):
    """
    function is responsible for transofrming raw datasets into Sources
    """

    if not name: # user has not provided a scraper name to get collections with
        logger.error('Scraper/Office name not provided. Cannot generate collections')
        sys.exit(1)
    
    # load the Graph representing the scraped datasets
    GraphWrapper.load_graph(file_dir_path=Path(OUTPUT_DIR, 'graphs', name),
                            file_stem_name=f'{name}.collections')
    # get the loaded graph
    graph = GraphWrapper.get_graph()

    # identify sources within the graph
    identify_sources_within_graph(graph)
    # link collection vertices to their appropriate sources(s) within the graph
    link_collection_to_sources_in_graph(graph)
    # write the identified sources to the {name}.collections.json file
    add_sources_to_collections_json(name=name, graph=graph,
                                    output_dir=OUTPUT_DIR)

    # write the graph to files
    # this method is explicitly thread/proccess safe, so no need for lock
    GraphWrapper.write_graph(file_dir_path=Path(os.getenv('ED_OUTPUT_PATH'), 
                                                        "graphs", f"{name}"),
                                        file_stem_name=f'{name}.sources')
    # create the page legend file for this graph
    GraphWrapper.create_graph_page_legend(file_dir_path=Path(os.getenv('ED_OUTPUT_PATH'), 
                                                        "graphs", f"{name}"),
                                         file_stem_name=f'{name}.sources')
    
    # create the sources.json file
    sources_list = [] # holds the list of sources acquired from 'name' scraper directory
    with graph.graph_lock:
        for source in graph.vs.select(is_source_eq=True, name_ne='base_vertex'):
            sources_list.append({'source_id': source['source_id'],
                                     'source_title': source['title'],
                                      'source_url': source['name']})
        

    # get a list of non-duplicate Sources
    sources_list = get_distinct_sources_from(sources_list, min_occurence_counter=1)
    # get the path were the gotten Sources will be saved to on local disk
    file_output_path = f'{CURRENT_TRANSFORMER_OUTPUT_DIR}/{(name or "all")}.sources.json'
    # write to file the Sources gotten from 'name' scraped output
    h.write_file(file_output_path, sources_list)
    # write file the Sources gotten from 'name' scraped out to S3 bucket
    h.upload_to_s3_if_configured(file_output_path, 
                                 f'{(name or "all")}.sources.json')


def identify_sources_within_graph(graph):
    """ function identifies AND flags/marks source vertices
    within the provided graph. All updates are done inplace,
    so the provided graph will be updated/modified after this process """

    with graph.graph_lock:
        graph.vs['is_source'] = None # do this to ensure no vertice are identified as sources yet
        collection_vertices = graph.vs.select(is_collection_eq=True, name_ne='base_vertex')
        source_vertices = set()
        for collection_vertex in collection_vertices:
            source_vertices.update(collection_vertex.predecessors())

        for source_vertex in source_vertices:
            if source_vertex['name'] == 'base_vertex': # this is the start-point vertex, ignore it
                continue
            source_vertex['is_source'] = True
            source_vertex['label'] = f'S{source_vertex.index}'
            source_vertex['color'] = 'yellow'
            source_vertex['source_id'] = f'{hashlib.md5(source_vertex["name"].encode("utf-8")).hexdigest()}-{hashlib.md5("all".encode("utf-8")).hexdigest()}'


def link_collection_to_sources_in_graph(graph=GraphWrapper.graph):
    """ function marks collection and dataset vertices within the graph as
    belonging to their appropriate Source """

    with graph.graph_lock:
        # select all the source vertices
        source_vertex_seq = graph.vs.select(is_source_eq=True)
        # select all the collection vertices
        collection_vertex_seq = graph.vs.select(is_collection_eq=True)

        # select the edges which connect source vertices to collection vertices                                                  
        source_collection_edge_seq = graph.es.select(_between=([vertex.index for vertex in source_vertex_seq],
                                  [vertex.index for vertex in collection_vertex_seq]))

        for edge in source_collection_edge_seq:
            # assign the collection vertex to the source which is it's parent
            if 'in_source' not in edge.target_vertex.attribute_names() or\
                edge.target_vertex['in_source'] is None:
                edge.target_vertex['in_source'] = list()
            
            # mark the collection vertex as belonging to the source
            edge.target_vertex['in_source'].\
                    append({'source_id': edge.source_vertex['source_id'],
                            'source_title': edge.source_vertex['title'],
                            'source_url': edge.source_vertex['name']})
            
            # for each collection vertex belonging to a source,
            # identify the datasets belonging to that collection vertex
            dataset_vertex_seq = graph.vs(is_dataset_eq=True, name_ne='base_vertex')
            for dataset_vertex in dataset_vertex_seq:
                # if the dataset does NOT belong to a collection, skip it
                if dataset_vertex['in_collection'] is None or\
                    len(dataset_vertex['in_collection']) == 0:
                    continue
                # get the objects within the dataset vertex that represent the collection we are interested in
                dataset_collection_list = list(filter(lambda collection_obj, compare_collection_id=edge.target_vertex['collection_id']: collection_obj['collection_id'] == compare_collection_id,
                       dataset_vertex['in_collection']))
                if len(dataset_collection_list) == 0: # we are not interested in any collection object within this dataset vertex
                    continue # skip it
                
                dataset_collection_list[0].setdefault('source', [])
                dataset_collection_list[0]['source'].\
                    append({'source_id': edge.source_vertex['source_id'],
                            'source_title': edge.source_vertex['title'],
                            'source_url': edge.source_vertex['name']})
                 

def add_sources_to_collections_json(name, graph=GraphWrapper.graph,
                                    output_dir=OUTPUT_DIR):
    """ function writes the sources which have been identified in `graph`
    to their associated collections.json and raw dataset json files. 
    This function updates the json files by
    adding a `source` field to the `collection` key within the json structure """

    # get the collection datajson
    collections_json = h.read_file(Path(output_dir, 
                                   'transformers/collections', 
                                   f'{name}.collections.json'))
    
    with graph.graph_lock:
        # select all collection vertices within the graph
        collection_vertex_seq = graph.vs.select(is_collection_eq=True, name_ne='base_vertex')
        for collection in collection_vertex_seq:
            # get the list of collections within the collections.json that matches this collection vertex
            collection_json_list = list(filter(lambda collection_obj, compare_collection_id=collection['collection_id']: collection_obj['collection_id'] == compare_collection_id,
                       collections_json))
            # if no collection returned from the datajson, skip this collection vertex
            if len(collection_json_list) == 0:
                continue
            # assign the source info from the collection vertex to the collection json
            collection_json_list[0]['source'] = collection['in_source']
        # write the updated collection datajson back to file
        h.write_file(Path(output_dir, 
                                   'transformers/collections', 
                                   f'{name}.collections.json'), collections_json)

        # update the source info for each raw dataset i.e. each dataset json file
        # select the dataset vertices from the graph
        dataset_vertex_seq = graph.vs.select(is_dataset_eq=True, 
                                             name_ne='base_vertex',
                                             in_collection_ne=None)
        for dataset_vertex in dataset_vertex_seq:
            # read the raw dataset
            data = h.read_file(Path(output_dir, dataset_vertex['name']))
            if not data:
                continue
            # update the raw dataset collection field & source sub-field
            data['collection'] = dataset_vertex['in_collection']
            # write the updated raw dataset back to file
            h.write_file(Path(output_dir, dataset_vertex['name']), data)






def get_distinct_sources_from(source_list,
                                  min_occurence_counter: int=1) -> list:
    """ function returns a list of distinct/unique (non-duplicate) Sources
    extracted from the provided sources list
    
    PARAMETERS
    - sources_list: a list containing the Sources to extract distinct
    Sources from

    - min_occurence_counter: the operations used to identify a distinct Source can 
    be instructed on how to identify a Source for consideration. The
    'min_occurence_counter' instructs the algorithm to
    ignore/remove a Source from the list of distinct Sources if it does not
    occur/appear within the provided 'sources_list' at least that number of times.
    The default value is 1. Setting 'min_occurence_counter to < 1 will disable this
    check when creating a distinct/unique (non-duplicate) Source list
    """

    if (not source_list) or len(source_list) == 0: # parameter not provided
        return None
    
    # get a 'mapped' source_list for easy operation
    mapped_sources = map(lambda source: source.get('source_id', 
                                                        source['source_title']),
                                   source_list)
    
    # find out if minimum occurence checks should be performed
    min_occurence_counter = int(min_occurence_counter)
    if min_occurence_counter > 0: # perform minimum occcurence check
        sources_counter = Counter(mapped_sources) # Counter for how many times a Source occurs
        count_keys = list(sources_counter.keys()) # create a list from the counter key/source id
        for key in count_keys: # loop through each counter key/source id
            if sources_counter[key] < min_occurence_counter: # if counter key/source id < min_occurence counter
                # remove this key as it represents a Source that occurs less than requested
                del sources_counter[key]
        # end of minimum occurence checks,
        # so, generate the 'mapped' source list from the results of this check
        mapped_sources = sources_counter.elements()

    # get distinct (non-duplicate) 'mapped' source_list
    mapped_sources = set(mapped_sources)

    distinct_source_list = [] # holds the list of distinct source objects
    # iterate through 'mapped_source'
    for mapped_source in mapped_sources:
        # iterate through 'source_list'  parameter
        for source in source_list:
            # the source has the same id or title as mapped_source
            if source.get('source_id', source['source_title']) == mapped_source:
                # add this source to the list of distinct source objects
                distinct_source_list.append(source)
                break # leave the inner loop
    
    return distinct_source_list # return the distinct source
