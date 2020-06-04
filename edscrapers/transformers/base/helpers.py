import os
import json
from pathlib import Path
import re

from slugify import slugify
from urllib.parse import urlparse
from urllib.parse import urljoin

from edscrapers.cli import logger

OUTPUT_DIR = os.getenv('ED_OUTPUT_PATH')

map_office_name = {
    'edgov': 'Department of Education',
    'ocr': 'Office for Civil Rights',
    'octae': 'Office of Career, Technical and Adult Education',
    'ope': 'Office of Postsecondary Education',
    'oela': 'Office of English Language Acquisition',
    'osers': 'Office of Special Education and Rehabilitative Services',
    'opepd': 'Office of Planning, Evaluation and Policy Development',
    'oese': 'Office of Elementary and Secondary Education',
    'oese': 'Office of Elementary and Secondary Education',
    'nces': 'National Center for Education Statistics',
    'fsa': 'Federal Student Aid'
}

map_media_type = {
    'zip' : "application/zip",
    'txt' : "text/plain",
    'pdf' : "application/pdf",
    'xls' : "application/vnd.ms-excel",
    'xlsx' : "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    'csv' : "text/csv",
    'sas': 'application/sas-syntax-file',
    'dat': 'text/generic-data-file',
    'spss': 'application/spss-syntax',  # This may be an incorrect extension, but we will continue to search for it
    'db.': 'application/generic-data-base',
    'sql': 'text/structured-query-language-file',
    'xml': 'application/xml',
    'sps': 'application/spss-syntax',
    'sav': 'application/spss-data',
    'do': 'application/stata-syntax',
    'r': 'text/r-script',
    'rdata': 'text/r-data',
    'rda': 'text/r-data',
    'sd2': 'application/sas-data',
    'sd7': 'application/sas-data',
    'sas7bdat': 'application/sas-data'
}

# KEY/VAUE PAIR FOR STATE NAMES (CURRENTLY US STATES).
# THIS IS USED TO DETERMINE 'level_of_data'
COUNTRY_STATES = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AS": "American Samoa",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "DC": "District Of Columbia",
    "FM": "Federated States Of Micronesia",
    "FL": "Florida",
    "GA": "Georgia",
    "GU": "Guam",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MH": "Marshall Islands",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "MP": "Northern Mariana Islands",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PW": "Palau",
    "PA": "Pennsylvania",
    "PR": "Puerto Rico",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VI": "Virgin Islands",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming"
}

def get_country_states(state_key=None):
    """ returns the name of a State, using the 2-letter state_keys.
    if state_key is None, then a list of all the State names is returned.
    if the state_key provided does not exist, None is returned """

    if state_key is None:
        return list(COUNTRY_STATES.values())

    return COUNTRY_STATES.get(state_key, None)


def get_office_name(target_dept):
    return map_office_name.get(target_dept, 'all')

def get_media_type(format):
    return map_media_type.get(format)

def traverse_output(target=None):
    if target is None:
        results = Path(os.path.join(OUTPUT_DIR, 'scrapers')).rglob('*.json')
    else:
        if target in ['oese', 'osers', 'oela', 'octae', 'ope', 'opepd']:
            results = Path(os.path.join(OUTPUT_DIR, 'scrapers', 'edgov', target)).glob('**/*.json')
        else:
            results = Path(os.path.join(OUTPUT_DIR, 'scrapers', target)).glob('**/*.json')

    files_list = [f for f in results
                  if 'print' not in str(f).split('/')[-1].split('-')]
    return files_list

def read_file(file_path):
    with open(file_path, 'r') as fl:
        data = json.load(fl)
        return data


def write_file(file_path, data, mode='w'):
    """ write data to a file as json """

    with open(file_path, mode) as fl:
        json.dump(data, fl, indent=2)



def transform_keywords(tags_string):

    """ transform a string of tags to a list using common delimeters"""

    # TODO: REMOVE THE COMMENT CODE BELOW
    """keywords = list()
    for tag in tags_string.split(';'):
        tag = tag.strip()
        tag = tag.lower()
        tag = tag.replace(' ','-')
        if tag:
            keywords.append(tag)
    return keywords"""

    # split keywords using regex
    keywords = re.split(r'[,;]+', tags_string, flags=re.IGNORECASE)
    keywords = set(keywords) # remove duplicates
    keywords.discard('') # remove any empty strings from the set
    
    keywords = list(keywords)

    for index in range(0, len(keywords)):
        keywords[index] = keywords[index].strip().replace(' ', '-').lower()

    return keywords



def transform_dataset_title(title, url):

    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    path = parsed_url.path

    slug = slugify(domain + path)
    new_title = slug

    if title:
        new_title = title + ' (' + slug + ')'
    
    return new_title
        

def transform_dataset_identifier(title, url):

    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    path = parsed_url.path

    if title:
        return slugify(title + '-' + domain + path)
    else:
        return slugify(domain + path)

def extract_resource_format_from_url(url):
    
    parsed_url = urlparse(url)
    base = os.path.basename(parsed_url.geturl())

    ### rsplit on base name to support multiple periods
    base_name_lst = base.rsplit('.', 1)

    if len(base_name_lst) == 0:
        ### return a default format
        return 'txt'
    
    extension = base_name_lst[-1]

    ### accepting only 5 char extensions
    if len(extension) < 6:
        return extension
    else:
        ### return a default format
        return 'txt'

def extract_resource_name_from_url(url):
    
    parsed_url = urlparse(url)
    base = os.path.basename(parsed_url.geturl())

    ### rsplit on base name to support multiple periods
    base_name_lst = base.rsplit('.', 1)
    
    if len(base_name_lst) == 0:
        ### return a default name
        ### slugify the url and return as a name
        return slugify(parsed_url.geturl())

    name = base_name_lst[0]

    if name:
        return name
    else:
        ### return a default name
        ### slugify the url and return as a name
        return slugify(parsed_url.geturl())

def upload_to_s3_if_configured(file_path, file_name):
    if os.getenv('S3_ACCESS_KEY') and os.getenv('S3_SECRET_KEY'):
        S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'us-ed-scraping')
        S3_ACCESS_KEY = os.getenv('S3_ACCESS_KEY')
        S3_SECRET_KEY = os.getenv('S3_SECRET_KEY')

        from botocore.client import Config
        from boto3.session import Session
        from botocore.handlers import set_list_objects_encoding_type_url

        session = Session(aws_access_key_id=S3_ACCESS_KEY,
                        aws_secret_access_key=S3_SECRET_KEY,
                        region_name="US-CENTRAL1")

        session.events.unregister('before-parameter-build.s3.ListObjects', set_list_objects_encoding_type_url)

        s3 = session.resource('s3', endpoint_url='https://storage.googleapis.com',
                            config=Config(signature_version='s3v4'))

        bucket = s3.Bucket(S3_BUCKET_NAME)
        with open(file_path, 'rb') as file_obj:
            response = bucket.put_object(Key=f'{file_name}',
                                         Body=file_obj,
                                         CacheControl='no-cache')
        logger.info(f'File uploaded to https://storage.googleapis.com/us-ed-scraping/{file_name}')
        return response
    else:
        return False

def get_output_path(name):
    output_path = os.path.join(OUTPUT_DIR, 'transformers', name)
    Path(output_path).mkdir(parents=True, exist_ok=True)

    return output_path
