import json
from datetime import datetime

from edscrapers.transformers.base import helpers as h 

class Organization():

    organization_type = str()
    name = str()
    sub_organization_of = None

    def __init__(self):

        self.organization_type = "org:Organization"

    def to_dict(self):

        if not self.name:
            return None

        org_dict = {
            "@type": self.organization_type,
            "name": self.name
        }

        if self.sub_organization_of is not None:
            org_dict["subOrganizationOf"] = self.sub_organization_of

        return org_dict

class Catalog():

    catalog_id = str()
    catalog_type = str()
    context = str()
    conformsTo = str()
    describedBy = str()
    datasets = list() # datasets list
    sources = list() # Sources list
    collections = list() # Collection list


    def __init__(self):
        
        self.catalog_type = "dcat:Catalog"
        self.context = "https://project-open-data.cio.gov/v1.1/schema/catalog.jsonld"
        self.conformsTo = "https://project-open-data.cio.gov/v1.1/schema"
        self.describedBy = "https://project-open-data.cio.gov/v1.1/schema/catalog.json"

    def to_dict(self):

        catalog_dict = {}

        if self.context:
            catalog_dict["@context"] = self.context

        if self.catalog_id:
            catalog_dict["@id"] = self.catalog_id

        if self.catalog_type:
            catalog_dict["@type"] = self.catalog_type

        if self.conformsTo:
            catalog_dict["conformsTo"] = self.conformsTo

        if self.describedBy:
            catalog_dict["describedBy"] = self.describedBy

        if len(self.datasets) > 0:
            catalog_dict["dataset"] = self.dump_datasets()
        
        if len(self.sources) > 0:
            catalog_dict['source'] = self.dump_sources()

        if len(self.collections) > 0:
            catalog_dict['collection'] = self.dump_collections() 

        return catalog_dict

    def dump_datasets(self):

        datasets_lst = []

        for dataset in self.datasets:
            datasets_lst.append(dataset.to_dict())

        return datasets_lst
    
    def dump_sources(self):

        sources_lst = []

        for source in self.sources:
            sources_lst.append(source.to_dict())

        return sources_lst

    def dump_collections(self):

        collections_lst = []

        for collection in self.collections:
            collections_lst.append(collection.to_dict())

        return collections_lst

    
    def dump(self):
        return json.dumps(self.to_dict(), sort_keys=False, indent=2)
    
    def validate_catalog(self, pls_fix: bool = True):
        """ function is used to validate the entire catalog object to ensure it
        conforms with the schema. The current schema is located at:
        [](https://schema-location)
        function returns True if validation was successful AND return False otherwise
        
        PARAMETERS
        - pls_fix: this parameter requests that the catalog object be fixed
        (i.e. updated/corrected to a valid state) as validation is going-on.
        It accepts a True (the default) or False value.
        When this parameter is True, the function will try its best
        efforts to fix the catalog object to a validate state;
        if all fixes are successful, the catalog object will become valid and the function
        will return True. However, if fixes are unsuccessful,
        then the catalog object will be invalid and the function will return False.
        NOTE: Because attempts to *fix* the catalog object are applied inplace,
        a failed attempt to fix the catalog object will result in a catalog that is
        in an unpredictable/unstable state.
        It is advised that whenever a validation fails and `pls-fix` was set to True,
        then the catalog object should be recreated.
        """

        # apply a top-down semantic order to validation
        # i.e. Sources [contain] Collections, Collections [contain] Datasets etc.
        
        # validate the Collections link to Sources in the catalog
        if not self.validate_collection_sources(pls_fix=pls_fix):
            return False # validation failed
        # validate the Datasets link to Sources in the catalog
        if not self.validate_dataset_sources(pls_fix=pls_fix):
            return False # validation failed
        # validate the Datasets link to Collections in the catalog
        if not self.validate_dataset_collections(pls_fix=pls_fix):
            return False # validation failed
        
        return True # validation successful

    def validate_collection_sources(self, pls_fix: bool = True):
        """
        function validates the relationship between a catalog
        `collections` and `sources` attributes.
        function uses the same schema as `catalog.validate_catalog()`.

        Parameters and return value for this function are the same as
        `catalog.validate_catalog()`
        """

        # get a mapped list of sources that belong to this catalog
        mapped_sources = list(map(lambda source: source.id, self.sources))

        # loop through the list of collections in this catalog object
        for collection in self.collections:
            remove_collection_sources = [] # holds the list of collection sources to be removed
            # loop through the list of sources in each collection
            for collection_source in collection.sources:
                # check if this collection source is in the list of Sources within this catalog
                if collection_source.id not in mapped_sources: # collection source not in catalog sources
                    # check if this validation error should be fixed
                    if pls_fix is False: # do not fix
                        return False # validation failed
                    elif pls_fix is True: # try to fix
                        # flag/collect the 'failed' collection_source for removal/unlinking
                        remove_collection_sources.append(collection_source)
                    else:
                        raise TypeError("wrong type for parameter 'pls_fix'. expecting bool")
            # after looping through collection sources, check if there are any collection sources within the catalog that need to be deleted
            if len(remove_collection_sources) > 0:
                # remove invalid collection sources for this catalog
                for remove_collection_source in remove_collection_sources:
                    try:
                        collection.sources.remove(remove_collection_source)
                    except:
                        pass
        return True # validation completed
    
    def validate_dataset_sources(self, pls_fix: bool = True):
        """
        function validates the relationship between a catalog
        `sources` attribute and the Sources contained within a catalog `datasets`
        attribute.
        function uses the same schema as `catalog.validate_catalog()`.

        Parameters and return value for this function are the same as
        `catalog.validate_catalog()`
        """

        # get a mapped list of sources that belong to this catalog
        mapped_sources = list(map(lambda source: source.id, self.sources))

        # loop through the list of datasets in this catalog object
        for dataset in self.datasets:
            remove_dataset_sources = [] # holds the list of dataset sources to be removed
            # loop through the list of sources in each dataset
            for dataset_source in dataset.source:
                # check if this dataset source is in the list of Sources within this catalog
                if dataset_source.id not in mapped_sources: # dataset source not in catalog sources
                    # check if this validation error should be fixed
                    if pls_fix is False: # do not fix
                        return False # validation failed
                    elif pls_fix is True: # try to fix
                        # flag/collect the 'failed' dataset_source for removal/unlinking
                        remove_dataset_sources.append(dataset_source)
                    else:
                        raise TypeError("wrong type for parameter 'pls_fix'. expecting bool")
            # after looping through dataset sources, check if there are any dataset sources within the catalog that need to be deleted
            if len(remove_dataset_sources) > 0:
                # remove invalid dataset sources for this catalog
                for remove_dataset_source in remove_dataset_sources:
                    try:
                        dataset.source.remove(remove_dataset_source)
                    except:
                        pass
        return True # validation completed
    
    def validate_dataset_collections(self, pls_fix: bool = True):
        """
        function validates the relationship between a catalog
        `collections` attribute and the Collections contained within a catalog `datasets`
        attribute.
        function uses the same schema as `catalog.validate_catalog()`.

        Parameters and return value for this function are the same as
        `catalog.validate_catalog()`
        """

        # get a mapped list of collections that belong to this catalog
        mapped_collections = list(map(lambda collection: collection.id, self.collections))

        # loop through the list of datasets in this catalog object
        for dataset in self.datasets:
            remove_dataset_collections = [] # holds the list of dataset collections to be removed
            # loop through the list of collections in each dataset
            for dataset_collection in dataset.collection:
                # check if this dataset collection is in the list of Collections within this catalog
                if dataset_collection.id not in mapped_collections: # dataset collection not in catalog collections
                    # check if this validation error should be fixed
                    if pls_fix is False: # do not fix
                        return False # validation failed
                    elif pls_fix is True: # try to fix
                        # flag/collect the 'failed' dataset_source for removal/unlinking
                        remove_dataset_collections.append(dataset_collection)
                    else:
                        raise TypeError("wrong type for parameter 'pls_fix'. expecting bool")
            # after looping through dataset collections,
            # check if there are any dataset collections within the catalog that need to be deleted
            if len(remove_dataset_collections) > 0:
                # remove invalid dataset collections for this catalog
                for remove_dataset_collection in remove_dataset_collections:
                    try:
                        dataset.collection.remove(remove_dataset_collection)
                    except:
                        pass
        return True # validation completed


class Source():
    
    id = str()
    url = str()
    title = str()

    def to_dict(self):
        
        source_dict = {}

        if self.id:
            source_dict['id'] = self.id
        
        if self.title:
            source_dict['title'] = self.title

        if self.url:
            source_dict['scraped_from'] = self.url
        
        return source_dict

class Collection():

    id = str()
    url = str()
    title = str()
    sources = list()

    def __init__(self):
        self.sources = list()

    def to_dict(self):

        collection_dict = {}
        
        if self.id:
            collection_dict['id'] = self.id
        
        if self.title:
            collection_dict['title'] = self.title

        if self.url:
            collection_dict['scraped_from'] = self.url
        
        if len(self.sources) > 0:
            collection_dict['source'] = self.dump_sources()
        
        return collection_dict
    
    def dump_sources(self):
        
        sources_list = []
        for source in self.sources:
            sources_list.append(source.id)
        return sources_list


class Dataset():
    
    dataset_type = str()
    title = str()
    description = str()
    keyword = list()
    modified = None
    scraped_from = str()
    publisher = Organization()
    contactPoint = dict()
    identifier = str()
    accessLevel = str()
    bureauCode = list()
    programCode = list()
    dataset_license = str()
    spatial = str()
    temporal = str()
    theme = list()
    distribution = list() # resources list
    levelOfData = str()
    source = list() # list of Sources
    collection = list() # list of Collections

    def __init__(self):
        
        self.dataset_type = "dcat:Dataset"
        self.accessLevel = "public"
        # set license to cc-zero
        self.dataset_license = "https://creativecommons.org/publicdomain/zero/1.0/"
        #self.dataset_license = "notspecified"
        self.spatial = "United States"
        self.description = "n/a"
        self.modified = datetime.now().strftime("%Y-%m-%d")
        self.distribution = list()
        self.source = list()
        self.collection = list()

    def to_dict(self):

        dataset_dict = {}

        if self.dataset_type:
            dataset_dict["@type"] = self.dataset_type
        
        if self.title:
            dataset_dict["title"] = self.title
        
        if self.description:
            dataset_dict["description"] = self.description

        if len(self.keyword) > 0:
            dataset_dict["keyword"] = self.keyword

        if self.modified:
            dataset_dict["modified"] = self.modified

        if self.publisher.to_dict():
            dataset_dict["publisher"] = self.publisher.to_dict()

        if self.scraped_from:
            dataset_dict["scraped_from"] = self.scraped_from

        if self.contactPoint:
            dataset_dict["contactPoint"] = self.contactPoint

        if self.identifier:
            dataset_dict["identifier"] = self.identifier

        if self.accessLevel:
            dataset_dict["accessLevel"] = self.accessLevel

        if len(self.bureauCode) > 0:
            dataset_dict["bureauCode"] = self.bureauCode

        if len(self.programCode) > 0:
            dataset_dict["programCode"] = self.programCode

        if self.dataset_license:
            dataset_dict["license"] = self.dataset_license

        if self.spatial:
            dataset_dict["spatial"] = self.spatial

        if self.temporal:
            dataset_dict["temporal"] = self.temporal

        if len(self.theme) > 0:
            dataset_dict["theme"] = self.theme

        if len(self.distribution) > 0:
            dataset_dict["distribution"] = self.dump_resources()
        
        if self.levelOfData:
            dataset_dict['levelOfData'] = self.levelOfData
        
        if len(self.source) > 0:
            dataset_dict['source'] = self.dump_sources()
        
        if len(self.collection) > 0:
            dataset_dict['collection'] = self.dump_collections()

        return dataset_dict

    def dump_resources(self):

        resources_lst = []

        for resource in self.distribution:
            resources_lst.append(resource.to_dict())

        return resources_lst
    
    def dump_sources(self):
        sources_list = []

        for source in self.source:
            sources_list.append(source.id)
        return sources_list
    
    def dump_collections(self):
        collections_list = []

        for collection in self.collection:
            collections_list.append(collection.id)
        return collections_list
            

class Resource():

    resource_type = str()
    description = str()
    title = str()
    resource_format = str()
    mediaType = str()
    accessURL = str()
    downloadURL = str()
    headerMetadata = dict()

    def __init__(self):    
        self.resource_type = "dcat:Distribution"
        self.description = "n/a"
        self.resource_format = "txt"
        self.mediaType = h.get_media_type(self.resource_format)
        self.headerMetadata = dict()

    def to_dict(self):

        resource_dict = {}

        if self.resource_type:
            resource_dict["@type"] = self.resource_type

        if self.title:
            resource_dict["title"] = self.title
        
        if self.description:
            resource_dict["description"] = self.description

        if self.downloadURL:
            resource_dict["downloadURL"] = self.downloadURL

        if self.accessURL:
            resource_dict["accessURL"] = self.accessURL

        if self.resource_format:
            resource_dict["format"] = self.resource_format

        if self.mediaType:
            resource_dict["mediaType"] = self.mediaType
        
        if len(list(self.headerMetadata.keys())) > 0:
            resource_dict["headerMetadata"] = self.headerMetadata

        return resource_dict
