import re
from scrapy.spidermiddlewares.offsite import OffsiteMiddleware

import bs4

class RegexOffsiteMiddleware(OffsiteMiddleware):
    def get_host_regex(self, spider):

        allowed_domains = getattr(spider, 'allowed_domains', None)

        if allowed_domains:
            regex = r'^(.*\.)?(%s)$' % '|'.join(re.escape(d) for d in allowed_domains if d is not None)
        else:
            return re.compile('') # allow all by default

        allowed_regex = getattr(spider, 'allowed_regex', None)
        if allowed_regex:
            return re.compile(allowed_regex)
        else:
            return re.compile(regex)


class GraphMiddleWare():
    
    def process_spider_input(self, response, spider):

        # ensure that the response text gotten is a string
        if not isinstance(getattr(response, 'text', None), str):
            raise TypeError("invalid response type gotten. Expected 'str' type")

        try:
            soup_parser = bs4.BeautifulSoup(response.text, 'html5lib')
        except Exception as exc:
            raise exc

        current_vertex = None # holds the current vertex which represents the current Response
        
        with spider.scraper_graph.graph_lock:
            # check if this particular vertex already exist
            try:
                current_vertex = spider.scraper_graph.vs.find(name=response.url)
            except:
                pass
            if not current_vertex: # if the current vertex does NOTalready exist, create it
                current_vertex = spider.scraper_graph.add_vertex(name=response.url, color='pink', shape=1)
                current_vertex['label'] = f"P{current_vertex.index}" # add label for the vertex
                # set the title for the vertex
                if soup_parser.head.find(name='title'):
                    current_vertex['title'] = str(soup_parser.head.\
                            find(name='title').string).strip()
                else:
                    current_vertex['title'] = '[no title]'

            if response.meta.get('depth', 0) == 0: # this is a response from a start url
                spider.scraper_graph.add_edge(source='base_vertex', target=current_vertex['name'])

            elif str(response.request.headers.get(b'Referer', b''), encoding='utf-8') == response.url:
                # this is also a response from a start url
                spider.scraper_graph.add_edge(source='base_vertex', target=current_vertex['name'])
            
            else:
                # get the parent vertex this response
                parent_vertex = spider.scraper_graph.vs.find(name=str(response.request.headers.get(b'Referer', b''), encoding='utf-8'))
                spider.scraper_graph.add_edge(source=parent_vertex['name'], target=current_vertex['name'])