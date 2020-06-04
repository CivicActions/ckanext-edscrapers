import os
import json
import hashlib

from pathlib import Path
from scrapy import Item, Field

class Source(Item):
    source_title = Field()
    source_id = Field()
    source_url = Field()

class Collection(Item):

    collection_title = Field()
    collection_id = Field()
    collection_url = Field()
    source = Field()

class Publisher(Item):
    name = Field()
    subOrganizationOf = Field()


class Dataset(Item):

    source_url = Field()

    title = Field()
    name = Field()
    notes = Field()
    date = Field()
    contact_person_name = Field()
    contact_person_email = Field()

    tags = Field()
    resources = Field()
    collection = Field()
    saved_as_file = Field()
    publisher = Field()

    def toJSON(self):
        # dont convert the collection field to JSON
        if self.__dict__['_values'].get('collection', None):
            del self.__dict__['_values']['collection']

        return json.dumps(self, default=lambda o: o.__dict__['_values'],
                          sort_keys=False, indent=2)


class Resource(Item):

    name = Field()
    url = Field()
    source_url = Field()
    description = Field()
    format = Field()
    headers = Field()
