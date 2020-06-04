# -*- coding: utf-8 -*-
import os
import logging
import logging.config

# Scrapy
SCRAPY_SETTINGS = {
    'SPIDER_MODULES': [
        'edscrapers.scrapers.edgov.crawler',
        'edscrapers.scrapers.edgov.octae.crawler',
        'edscrapers.scrapers.edgov.oela.crawler',
        'edscrapers.scrapers.edgov.oese.crawler',
        'edscrapers.scrapers.edgov.ope.crawler',
        'edscrapers.scrapers.edgov.opepd.crawler',
        'edscrapers.scrapers.edgov.osers.crawler',
        'edscrapers.scrapers.ocr.crawler',
        'edscrapers.scrapers.nces.crawler',
        'edscrapers.scrapers.fsa.crawler',
        'edscrapers.scrapers.sites.crawler',
    ],
    'DOWNLOAD_DELAY': float(os.getenv('DOWNLOAD_DELAY', 1)),
    'DOWNLOADER_MIDDLEWARES': {
        'scrapy.downloadermiddlewares.httpcache.HttpCacheMiddleware': 1,
        'edscrapers.scrapers.base.middlewares.RegexOffsiteMiddleware': 2,
        'scrapy.spidermiddlewares.offsite.OffsiteMiddleware': 3,
    },
    'ITEM_PIPELINES': {
        'edscrapers.scrapers.base.pipelines.JsonWriterPipeline': 1,
        'edscrapers.scrapers.base.pipelines.GraphItemPipeline': 2,
    },
    'SPIDER_MIDDLEWARES': {
        'edscrapers.scrapers.base.middlewares.GraphMiddleWare': 1000
    },
    'SCHEDULER_PRIORITY_QUEUE': 'scrapy.pqueues.DownloaderAwarePriorityQueue',
    # 'REDIRECT_ENABLED': False,
    'RETRY_ENABLED': False,
    'COOKIES_ENABLED': False,

    # We have custom logging
    # 'LOG_ENABLED': False,

    # This is set by the CLI
    # 'HTTPCACHE_ENABLED': True,

    'AUTOTHROTTLE_ENABLED': True,
    'LOG_LEVEL': 'INFO',
    'DEPTH_LIMIT': 0
}
