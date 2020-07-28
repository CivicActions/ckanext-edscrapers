import os
import json
from pathlib import Path
import urllib.parse

import igraph

from edscrapers.cli import logger
from edscrapers.transformers.base.helpers import traverse_output
from edscrapers.scrapers.base.graph import GraphWrapper


OUTPUT_DIR = os.getenv('ED_OUTPUT_PATH')
Path(os.path.join(OUTPUT_DIR, 'transformers', 'deduplicate')).mkdir(parents=True, exist_ok=True)

def transform(name=None, input_file=None):
    transformer = Transformer(name)

    # load the Graph representing the scraped datasets
    GraphWrapper.load_graph(file_dir_path=Path(OUTPUT_DIR, 'graphs', name),
                            file_stem_name=name)
    # get the loaded graph
    graph = GraphWrapper.get_graph()

    if not input_file:
        out_file = os.path.join(OUTPUT_DIR, 'transformers', 'deduplicate', f'deduplicated_{name or "all"}.lst')
    else:
        out_file = input_file

    with open(out_file, 'w') as fp:
        for fname in transformer.urls_dict.values():
            fp.write(fname + '\n')
        

    vertex_seq = find_duplicate_dataset_vertices(graph, list(transformer.urls_dict.values()))
    remove_vertices(graph, vertex_seq)

    # write the graph to files
    # this method is explicitly thread/proccess safe, so no need for lock
    GraphWrapper.write_graph(file_dir_path=Path(os.getenv('ED_OUTPUT_PATH'), 
                                                        "graphs", f"{name}"),
                                        file_stem_name=f'{name}.deduplicate')
    # create the page legend file for this graph
    GraphWrapper.create_graph_page_legend(file_dir_path=Path(os.getenv('ED_OUTPUT_PATH'), 
                                                        "graphs", f"{name}"),
                                          file_stem_name=f'{name}.deduplicate')

    logger.success('Deduplicated list is ready.')


def find_duplicate_dataset_vertices(graph,
                                    kept_dataset_file_paths: list) -> igraph.VertexSeq:
    """ function is used to identify which vertices
    should be dropped from the graph based on the
    transformer deduplication process """

    kept_dataset_file_paths = list(map(lambda filepath: filepath[filepath.find("/scrapers/")+1 : ], 
                                     kept_dataset_file_paths))

    with graph.graph_lock: # activate lock on graph
        # find the dataset vertices to be dropped
        try:
            dropped_dataset_ver_seq = graph.vs.select(is_dataset_eq=True, name_notin=kept_dataset_file_paths)
        except:
            dropped_dataset_ver_seq = [] # since there are no dataset vertices, produce an empty list
    
    return dropped_dataset_ver_seq

def remove_vertices(graph, vertex_sequence):
    """ function removes the vertices contained in the sequence from
    the specified graph. The function also updates the parent vertex of
    the dataset vertex being removed """

    with graph.graph_lock: # activate lock on graph
        vertex_ids = [vertex_.index for vertex_ in vertex_sequence]
        for vertex in vertex_sequence:
            # remove the vertex from the datasets collection of the parent vertex
            for parent_vertex in vertex.predecessors():
                parent_vertex['datasets'].discard(vertex['name'])
                if len(parent_vertex['datasets']) == 0:
                    parent_vertex['is_dataset_page'] = None

        # delete the vertices from the graph
        graph.delete_vertices(vertex_ids)



class Transformer():

    def __init__(self, name=None):

        if name is None:
            self.file_list = traverse_output()
        else:
            self.file_list = traverse_output(name)

        # Deduplicate using a Python dict's keys uniqueness
        self.urls_dict = dict()
        self._make_list('source_url')


    def _make_list(self, key):
        for f in self.file_list:
            with open(f, 'r') as fp:
                try:
                    j = json.loads(fp.read())
                except Exception as e:
                    logger.warning(f'Failed to parse file {f} as JSON!')
                if '/print/' in j.get(key):
                    continue
                # In order to deduplicate with dicts, we need to normalize all keys
                self.urls_dict[self._normalize_url(j.get(key)) + '_' + j.get('name')] = str(f)


    def _normalize_url(self, url):
        # strip any query parameter(s) that may cause duplicate datasets
        url = self._url_query_param_strip(url, include_query_param=['referrer'])
        # strip protocol data
        url = url.replace('https://', '').replace('http://', '')
        # Remove www or www2
        url = url.replace('www2.', '').replace('www.', '')
        # Remove /print/ segment from printable pages
        # url = url.replace('/print/', '')
        # Lowercase all
        url = url.lower()

        return url
    

    def _url_query_param_strip(self, url: str, include_query_param: list=None,
                         exclude_query_param: list=None) -> str:
        """ function is a private helper.
        function helps to remove querystring name/value pairs from the provided url.

        PARAMETERS:
        - url: represents a valid url which can be parsed by urllib.parse.split()
        
        - include_query_param: a list containing the name(s) of query parameters to 
        be removed from url. if list is None (which is the default), no parameters are
        stripped. 
        If list is empty, ALL parameters are stripped

        - exclude_query_param: a list containing the name(s) of query parameters NOT to be 
        removed from url. That is, ALL available query parameters will
        be removed from url EXCEPT those provided in this list.
        if list is None (which is the default), ALL parameters are excluded from stripping.
        if list is empty, all parameters are excluded from being stripped provided
        'include_query_param' is None.

        NOTE: in terms of precedence, 'include_query_param' has a higher order than
        'exclude_query_param'. That is if both 'include_query_param' and
        'exclude_query_param' are specified AND 'include_query_param' is NOT None,
        then 'include_query_param' will be applied and 'exclude_query_param' disregarded.

        Returns: function returns a url that has been
        stripped of querystring name/value pairs"""

        split_url = urllib.parse.urlsplit(url) # holds the split components of the url
        stripped_url = url # holds the url string after stripping query parameters

        # if no query parameters are included or excluded,
        if include_query_param is None and exclude_query_param is None:
            # return a 'cleaned up' (but equivalent) version of the provided url
            stripped_url = urllib.parse.urlunsplit(urllib.parse.urlsplit(url))
            return stripped_url # return stripped url

        # if 'include_query_param' is empty list or includes params to be stripped
        if include_query_param is not None and len(include_query_param) >= 0:
            # get the query component of the url
            query_str = split_url.query
            if query_str == "": # no query string contained in the provided url
                # return a 'cleaned up' (but equivalent) version of the provided url
                stripped_url = urllib.parse.urlunsplit(urllib.parse.urlsplit(url))
            else: # query string was provided
                query_str_dict = urllib.parse.parse_qs(query_str)
                query_str_dict2 = dict(query_str_dict)
                for key in query_str_dict.keys(): # cycle through the query param names
                     # if any query param name in 'include_query_param' or 'include_query_param' 
                    if key in include_query_param or len(include_query_param) == 0:
                        del query_str_dict2[key] # delete the query param
                # convert the ammended query_param dict to a querystring
                query_str = urllib.parse.urlencode(query_str_dict2, doseq=True)
                stripped_url = urllib.parse.urlunsplit(urllib.parse.\
                                                       SplitResult(split_url.scheme,
                                                                   split_url.netloc,
                                                                   split_url.path,
                                                                   query_str,
                                                                   split_url.fragment))
            return stripped_url # return stripped url
        
        # if 'exclude_query_param' is empty list or includes params to be excluded
        if exclude_query_param is not None and len(exclude_query_param) >= 0:
            # get the query component of the url
            query_str = split_url.query
            if query_str == "": # no query string contained in the provided url
                # return a 'cleaned up' (but equivalent) version of the provided url
                stripped_url = urllib.parse.urlunsplit(urllib.parse.urlsplit(url))
            else: # query string was provided
                query_str_dict = urllib.parse.parse_qs(query_str)
                query_str_dict2 = dict(query_str_dict)
                for key in query_str_dict.keys(): # cycle through the query param names
                     # if any query param name not in 'exclude_query_param' and 'exclude_query_param' is not empty
                    if key not in exclude_query_param and len(exclude_query_param) > 0:
                        del query_str_dict2[key] # delete the query param
                # convert the ammended query_param dict to a querystring
                query_str = urllib.parse.urlencode(query_str_dict2, doseq=True)
                stripped_url = urllib.parse.urlunsplit(urllib.parse.\
                                                       SplitResult(split_url.scheme,
                                                                   split_url.netloc,
                                                                   split_url.path,
                                                                   query_str,
                                                                   split_url.fragment))
            return stripped_url # return stripped url
