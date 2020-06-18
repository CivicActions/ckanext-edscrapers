""" module transforms the raw dataset files (i.e. the results/output from scraping)
into a different json data structure referred to as Collections.
Each scraping output directory will have its own
collections file upon completion of the transformation. Files are titled
'{name}.collections.json' .
All transformation output is written into 'collections' subdirectory of the
'transformers' directory on 'ED_OUTPUT_PATH'
"""

import os
import sys
import json
from pathlib import Path
import re
from collections import Counter
import hashlib

from edscrapers.cli import logger
from edscrapers.transformers.base import helpers as h
from edscrapers.scrapers.base.graph import GraphWrapper

import igraph


OUTPUT_DIR = os.getenv('ED_OUTPUT_PATH') # get the output directory

# get this transformer's output directory
CURRENT_TRANSFORMER_OUTPUT_DIR = h.get_output_path('collections')


def transform(name=None, input_file=None):
    """
    function is responsible for transforming raw datasets into Collections
    """

    if not name: # user has not provided a scraper name to get collections with
        logger.error('Scraper/Office name not provided. Cannot generate collections')
        sys.exit(1)
    
    # load the Graph representing the scraped datasets
    GraphWrapper.load_graph(file_dir_path=Path(OUTPUT_DIR, 'graphs', name),
                            file_stem_name=name)
    # get the loaded graph
    graph = GraphWrapper.get_graph()

    # identify collections within the graph
    identify_collections_within_graph(graph)
    # link dataset vertices to their appropriate collection(s) within the graph
    link_datasets_to_collections_in_graph(graph)
    # write the identified collections to the raw dataset files
    add_collections_to_raw_datasets(graph=graph,
                                    output_dir=OUTPUT_DIR)

    # write the graph to files
    # this method is explicitly thread/proccess safe, so no need for lock
    GraphWrapper.write_graph(file_dir_path=Path(os.getenv('ED_OUTPUT_PATH'), 
                                                        "graphs", f"{name}"),
                                        file_stem_name=f'{name}.collections')
    # create the page legend file for this graph
    GraphWrapper.create_graph_page_legend(file_dir_path=Path(os.getenv('ED_OUTPUT_PATH'), 
                                                        "graphs", f"{name}"),
                                         file_stem_name=f'{name}.collections')                                    

    
    # create the collections.json file                                      
    collections_list = [] # holds the list of collections acquired from graph

    with graph.graph_lock:
        for collection in graph.vs.select(is_collection_eq=True, name_ne='base_vertex'):
            collections_list.append({'collection_id': collection['collection_id'],
                                     'collection_title': collection['title'],
                                      'collection_url': collection['name']})
    
    # get a list of non-duplicate collections
    collections_list = get_distinct_collections_from(collections_list,
                                                     min_occurence_counter=1)
    # get the path were the gotten Collections will be saved to on local disk
    file_output_path = f'{CURRENT_TRANSFORMER_OUTPUT_DIR}/{(name or "all")}.collections.json'
    # write to file the collections gotten from 'name' scraped output
    h.write_file(file_output_path, collections_list)
    # write file the collections gotten from 'name' scraped out to S3 bucket
    h.upload_to_s3_if_configured(file_output_path, 
                                 f'{(name or "all")}.collections.json')


def identify_collections_within_graph(graph=GraphWrapper.graph):
    """ function identifies AND flags/marks Collection vertices
    within the provided graph. All updates are done inplace,
    so the provided graph will be updated/modified after this process """

    with graph.graph_lock:
        graph.vs['is_collection'] = None # do this to ensure no vertice are identified as collections yet
        # Step 1: identify Dataset Page vertices that have multiple Dataset vertices pointing to it
        collection_vertex_seq1 = graph.vs.\
             select(lambda vertex: vertex['datasets'] is not None and len(vertex['datasets']) > 1)
        
        # Step 2: identify Page vertices that have at least 2 other dataset Page vertices pointing to it
        collection_vertex_seq2 = graph.vs.\
             select(_outdegree_ge=2, 
                   is_dataset_page_eq=None,
                   is_dataset_eq=None,
                   name_ne='base_vertex').\
            select(lambda vertex: (True not in [s['is_dataset'] for s in vertex.successors()]) and ([True] * len(vertex.successors())) == [s['is_dataset_page'] for s in vertex.successors()]).\
            select(lambda vertex: len(set(collection_vertex_seq1).intersection(set(vertex.successors()))) == 0)
        
        # Step 3: identify all predecessors of all the collections so far identified. 
        # the successors of these predecessors are also collections
        combined_col_seq = igraph.VertexSeq(graph, 
        [vertex.index for vertex in set(list(collection_vertex_seq1) + list(collection_vertex_seq2))])
        collection_vertex_seq3 = set()
        for vertex in combined_col_seq:
            for parent_vertex in vertex.predecessors():
                if parent_vertex['name'] == 'base_vertex': # this is the start-point vertex, ignore it
                    continue
                for another_vertex in parent_vertex.successors():
                    if another_vertex in combined_col_seq or another_vertex['is_dataset_page'] is None:
                        continue
                    collection_vertex_seq3.update([another_vertex])
        
        # END OF STPEPS USED TO IDENTIFY COLLECTIONS

        # NOW combine all the identified collections
        combined_col_seq = igraph.VertexSeq(graph, 
        [vertex.index for vertex in set(list(collection_vertex_seq1) + list(collection_vertex_seq2) + list(collection_vertex_seq3))])
        
        # update the identified collection vertices to flag/mark them as collections
        for collection_vertex in combined_col_seq:
            collection_vertex['is_collection'] = True
            collection_vertex['label'] = f'C{collection_vertex.index}'
            collection_vertex['color'] = 'green'
            collection_vertex['collection_id'] = f'{hashlib.md5(collection_vertex["name"].encode("utf-8")).hexdigest()}-{hashlib.md5("all".encode("utf-8")).hexdigest()}'
        
        # return all identified collections as a Vertext_Seq
        return combined_col_seq

def link_datasets_to_collections_in_graph(graph=GraphWrapper.graph):
    """ function marks dataset vertices within the graph as
    belonging to their appropriate Collection """

    with graph.graph_lock:
        graph.vs['in_collection'] = None
        # select all the collection vertices
        collection_vertex_seq = graph.vs.select(is_collection_eq=True)
        # select all the dataset Page vertices (i.e dataset page that are NOT marked as collections)
        dataset_page_vertex_seq = graph.vs.select(is_dataset_page_eq=True, 
                                                  is_collection_eq=None,
                                                  name_ne='base_vertex')
        # select the edges which connect collection vertices to dataset Page vertices                                                  
        collection_dataset_page_edge_seq = graph.es.select(_between=([vertex.index for vertex in collection_vertex_seq],
                                  [vertex.index for vertex in dataset_page_vertex_seq]))

        # loop through the collection-to-dataset pages links/edges
        for edge in collection_dataset_page_edge_seq:
            # loop through the successors of data Page vertex
            for dataset_vertex in edge.target_vertex.successors():
                # assign the dataset_vertex to the collection which is it's parent
                if 'in_collection' not in dataset_vertex.attribute_names() or\
                    dataset_vertex['in_collection'] is None:
                    dataset_vertex['in_collection'] = list()
                dataset_vertex['in_collection'].\
                    append({'collection_id': edge.source_vertex['collection_id'],
                            'collection_title': edge.source_vertex['title'],
                            'collection_url': edge.source_vertex['name']})
            
        # select collection vertices that have also been marked as 'is_dataset_page'
        collection_vertex_seq = graph.vs.select(is_collection_eq=True, 
                                                is_dataset_page_eq=True,
                                                name_ne='base_vertex').\
                                                select(lambda vertex: len(vertex['datasets']) > 0)
        # loop through the succesors of each identified collection vertex
        for vertex in collection_vertex_seq:
            for dataset_vertex in vertex.successors():
                # assign the dataset_vertex to the collection which is it's parent
                if 'in_collection' not in dataset_vertex.attribute_names() or\
                    dataset_vertex['in_collection'] is None:
                    dataset_vertex['in_collection'] = list()
                dataset_vertex['in_collection'].\
                    append({'collection_id': vertex['collection_id'],
                            'collection_title': vertex['title'],
                            'collection_url': vertex['name']})

def add_collections_to_raw_datasets(graph=GraphWrapper.graph, 
                                    output_dir=OUTPUT_DIR):
    """ function writes the collections which have been identified in `graph`
    to their associated raw dataset json file. 
    This function updates the raw dataset json files by
    adding a `collection` field to the json structure """
    
    with graph.graph_lock:
        # select the dataset vertices from the graph
        dataset_vertex_seq = graph.vs.select(is_dataset_eq=True, 
                                             name_ne='base_vertex',
                                             in_collection_ne=None)
        for dataset in dataset_vertex_seq:
            # read the raw dataset
            data = h.read_file(Path(output_dir, dataset['name']))
            if not data:
                continue
            # update the raw dataset
            data['collection'] = dataset['in_collection']
            # write the updated raw dataset back to file
            h.write_file(Path(output_dir, dataset['name']), data)


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
