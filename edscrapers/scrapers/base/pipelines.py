import os
import json
import hashlib

from datetime import datetime
from pathlib import Path
from slugify import slugify
from scrapy.exceptions import DropItem

from edscrapers.cli import logger
from edscrapers.scrapers.base.graph import GraphWrapper



class JsonWriterPipeline(object):

    def open_spider(self, spider):
        Path(f"{os.getenv('ED_OUTPUT_PATH')}/scrapers/{spider.name}").\
                                                  mkdir(parents=True, exist_ok=True)

    def close_spider(self, spider):
        pass

    def process_item(self, dataset, spider):

        slug = slugify('-'.join(dataset['source_url'].split('/')[3:]))[:100] # restrict slug to 100 characters
        hashed_url = hashlib.md5(dataset['source_url'].encode('utf-8')).hexdigest()
        hashed_name = hashlib.md5(dataset['name'].encode('utf-8')).hexdigest()
        file_name = f"{slug}-{hashed_url}-{hashed_name}.json"
        if dataset.get('publisher') and (spider.name == 'edgov' or spider.name == 'sites'):
            try:
                name = dataset['publisher'].get('name', '')
            except:
                name = dataset['publisher']
            Path(f"{os.getenv('ED_OUTPUT_PATH')}/scrapers/{spider.name}/{name}").mkdir(parents=True, exist_ok=True)
            file_path = f"{os.getenv('ED_OUTPUT_PATH')}/scrapers/{spider.name}/{name}/{file_name}"
        else:
            if spider.name in ['oese', 'osers', 'oela', 'octae', 'ope', 'opepd']:
                Path(f"{os.getenv('ED_OUTPUT_PATH')}/scrapers/edgov/{spider.name}").mkdir(parents=True, exist_ok=True)
                file_path = f"{os.getenv('ED_OUTPUT_PATH')}/scrapers/edgov/{spider.name}/{file_name}"
            else:
                file_path = f"{os.getenv('ED_OUTPUT_PATH')}/scrapers/{spider.name}/{file_name}"
        self._log(dataset)
        logger.debug(f"Dumping to {file_path}")
        with open(file_path, 'w') as output:
            output.write(dataset.toJSON())
        
        # add this attribute so that the saved (relative) location of datasets can be tracked
        dataset['saved_as_file'] = file_path[file_path.find("/scrapers/")+1 : ]

        return dataset # return the dataset

    def _log(self, d):
        logger.info("==================================================================================================")
        logger.success(f"{d['source_url']}")
        logger.info(f"Title: {d['title']}")
        logger.debug(f"Description: {d['notes']}")
        logger.debug(f"Name:{d['name']}")
        logger.info(f"Resources: {len(d['resources'])}")
        for r in d['resources']:
            logger.debug(f"\t{r['url']} > {r['name']}")

class GraphItemPipeline:

    def open_spider(self, spider):
        # create the folder for storing graph files
        Path(os.getenv('ED_OUTPUT_PATH'), "graphs", f"{spider.name}").\
                                                  mkdir(parents=True, exist_ok=True)
        print("SPIDER STARTED")
        # setup the graph objet for this scraper
        # set the graph object as a class attribute
        if not hasattr(spider, 'scraper_graph'):
            spider.__class__.scraper_graph = GraphWrapper.get_graph()


    def close_spider(self, spider):
        print("SPIDER CLOSED")
        
        # write the graph to files
        # this method is explicitly thread/proccess safe, so no need for lock
        GraphWrapper.write_graph(file_dir_path=Path(os.getenv('ED_OUTPUT_PATH'), 
                                                            "graphs", f"{spider.name}"),
                                         file_stem_name=spider.name)
        
        # create the page legend file for this graph
        # this method is explicitly thread/proccess safe, so no need for lock
        GraphWrapper.create_graph_page_legend(file_dir_path=Path(os.getenv('ED_OUTPUT_PATH'), 
                                                            "graphs", f"{spider.name}"),
                                         file_stem_name=spider.name)
            

    def process_item(self, dataset, spider):
        
        with spider.scraper_graph.graph_lock:

            # check if this dataset already exist, i.e. is this somehow a duplicate scrape of the dataset
            try:
                spider.scraper_graph.vs.find(name=dataset['saved_as_file'])
                # if no error, it means this dataset vertex already exist, so exit method
                return dataset
            except ValueError: # if error it means this dataset vertex does NOT previously exists, so proceed
                pass
            
            # find the vertex page that represents this dataset
            parent_vertex = spider.scraper_graph.vs.find(name=dataset['source_url'])

            # check if the parent_vertex has an attribute to track if its a dataset page or not
            if 'is_dataset_page' not in parent_vertex.attribute_names() or parent_vertex['is_dataset_page'] is None: # no attribute set
                parent_vertex['is_dataset_page'] = True
                parent_vertex['datasets'] = set()
            # add the dataset identified to the page vertex
            parent_vertex['datasets'].add(dataset['saved_as_file'])

            # create the vertex to represent this dataset
            current_vertex = spider.scraper_graph.add_vertex(name=dataset['saved_as_file'], color='blue', shape=1)
            # change the vertex attribute to visually indicate it is a dataset
            current_vertex['label'] = f"D{current_vertex.index}"
            current_vertex['color'] = 'blue'
            current_vertex['is_dataset'] = True
            current_vertex['title'] = dataset['title']
            current_vertex['dataset_url'] = dataset['source_url']

            #add the edge between the parent_vertex and current_vertex
            spider.scraper_graph.add_edge(source=parent_vertex['name'],
                                          target=current_vertex['name'])


        return dataset


class DuplicatesPipeline(object):

    def __init__(self):
        self.ids_seen = set()

    def process_item(self, item, spider):
        if item['id'] in self.ids_seen:
            raise DropItem("Duplicate dataset found: %s" % item)
        else:
            self.ids_seen.add(item['source_url'])
            return item
