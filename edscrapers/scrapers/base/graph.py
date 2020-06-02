""" module contains necessary classes and functions for
the graphs used by edscrapers """

from pathlib import Path
import multiprocessing as mp
from datetime import datetime

import igraph
import pandas as pd

class GraphWrapper():
    """ class provides the singleton
    graph object to be used by a scraper or transformer """

    graph = igraph.Graph(directed=True)
        
    # create a process Lock for the
    # graph to ensure that accessing the graph is process/thread safe
    # ALWAYS USE THE LOCK WHILE ACCESSING THE GRAPH
    graph_lock = mp.Lock()
    graph.graph_lock = graph_lock # make the proccess lock accessible from the graph object

    # add the default base vertex
    with graph.graph_lock:
        graph.add_vertex(name='base_vertex', label='START', title='START POINT', color='orange', shape=1)
    

    @classmethod
    def get_graph(cls):
        """ returns the singleton graph object """
        return cls.graph

    @classmethod
    def write_graph(cls, file_dir_path, file_stem_name,
                    graph_width=1200, graph_height=1200,
                    vertex_size=32, font_size=26):
        """ write the graph to files """

        file_dir_path = Path(file_dir_path)
        file_dir_path.mkdir(parents=True, exist_ok=True)

        with cls.graph.graph_lock:
            # destroy the lock object, so it's not pickled
            del cls.graph.graph_lock
            # write the graph to a dated file
            cls.graph.write_pickle(fname=Path(file_dir_path, 
            f'{datetime.now().year}-{datetime.now().month:02d}-{datetime.now().day:02d}.pickle'),
            version=4)
            # write the graph to a general file
            # this general file will ALWAYS hold the latest graph
            cls.graph.write_pickle(fname=Path(file_dir_path, 
            f'{file_stem_name}.pickle'),
            version=4)
            # write the general file as svg
            cls.graph.write_svg(fname=open(Path(file_dir_path, 
                                                      f'{file_stem_name}.svg'), mode='wt'),
                                            width=graph_width, height=graph_height,
                                            vertex_size=vertex_size, font_size=font_size,
                                            edge_colors=['black']*cls.graph.ecount(),
                                            edge_stroke_widths=[4]*cls.graph.ecount())
            
            #reinstate the previously destroyed process lock since pickling is complete
            cls.graph.graph_lock = cls.graph_lock
    
    @classmethod
    def create_graph_page_legend(cls, file_dir_path, file_stem_name):
        """ create a csv that provides more details about the pages on the graph """

        # create the file_dir_path if it doesn't already exist
        file_dir_path = Path(file_dir_path)
        file_dir_path.mkdir(parents=True, exist_ok=True)

        with cls.graph.graph_lock:
            # get the VertexSequence for the pages we want to create legends for
            vertex_seq = cls.graph.vs.select(is_dataset_eq=None) # get vertices NOT flagged as dataset
            # create a dataframe that will contain the info to be written to csv
            df = pd.DataFrame(columns=['Page Label', 'Page Title', 'Page URL'])
            df['Page Label'] = vertex_seq['label']
            df['Page Title'] = vertex_seq['title']
            df['Page URL'] = vertex_seq['name']

            df.to_csv(Path(file_dir_path, f'{file_stem_name}_page_legend.csv'),
                      columns=['Page Label', 'Page Title', 'Page URL'],
                      header=True, index=False)