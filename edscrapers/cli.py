import os
import sys
import click
import importlib

from scrapy.crawler import CrawlerProcess
from loguru import logger
from pathlib import Path

from edscrapers.scrapers.base import config as scrape_config
from edscrapers.scrapers.base import helpers as scrape_base
from edscrapers.scrapers.base import helpers as scrape_helpers

from tools.compare import compare as compare_cli
from tools.dashboard.app import app as dash_app

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

global_options=[
    click.option('-v', '--verbose', 'verbosity', count=True, help='Show INFO and DEBUG messages.'),
    click.option('-q', '--quiet', is_flag=True, default=False, help='Do not show anything.'),
    click.option('-o', '--output', 'file_path', type=click.Path(), default=None,
                 help='If specified, pipe the output to both STDOUT and the file specified.')
]

def add_options(options):
    def _add_options(func):
        for option in reversed(options):
            func = option(func)
        return func
    return _add_options

def setup_logger(quiet, verbosity, name):
    log_levels = {'0': 'WARNING', '1': 'INFO', '2': 'DEBUG'}
    logger.remove()

    if not os.getenv('ED_OUTPUT_PATH'):
        print('Environment variable ED_OUTPUT_PATH not set! Aborting.')
        sys.exit(1)
    else:
        log_dir = os.path.join(os.getenv('ED_OUTPUT_PATH'), 'logs')

    if not quiet:
        # Not quiet, so we can log to STDOUT
        logger.add(sys.stdout,
                   colorize=True,
                   level=log_levels[str(verbosity)],
                   # filter="edscrapers",
                   format="<level>{message}</level>",
                   backtrace=True,
                   diagnose=True)


    logger.add(os.path.join(log_dir, 'log_{time}.log'),
               format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
               filter="edscrapers",
               level=log_levels[str(verbosity)],
               # filter="edscrapers",
               enqueue=True,
               rotation="1 GB",
               backtrace=True,
               diagnose=True)

    return True


@click.group()
def cli():
    pass


@cli.command(context_settings=CONTEXT_SETTINGS)
@click.option('--cache/--no-cache', default=True, help='Do not use Scrapy cache (i.e. "live" scrape)')
@click.option('--resume/--no-resume', default=False, help='Resume a previously interrupted scrape')
@add_options(global_options)
@click.argument('name')
def scrape(cache, resume, name, **kwargs):
    '''Run a Scrapy pipeline for crawling / parsing / dumping output'''

    # Prepare conf dict
    conf = scrape_helpers.get_variables(scrape_config, str.isupper)

    # Get the crawler & start the scrape
    crawler = importlib.import_module(f'edscrapers.scrapers.{name}').Crawler

    if not cache:
        conf['SCRAPY_SETTINGS']['HTTPCACHE_ENABLED'] = False
    else:
        conf['SCRAPY_SETTINGS']['HTTPCACHE_ENABLED'] = True

    if resume:
        if not os.getenv('ED_OUTPUT_PATH'):
            logger.error('ED_OUTPUT_PATH env var not set!')
            return False
        else:
            conf['SCRAPY_SETTINGS']['JOBDIR'] = os.path.join(os.getenv('ED_OUTPUT_PATH'), '.jobs')
            Path(os.path.join(os.getenv('ED_OUTPUT_PATH'), '.jobs')).mkdir(exist_ok=True)

    setup_logger(kwargs['quiet'], kwargs['verbosity'], name)

    process = CrawlerProcess(conf['SCRAPY_SETTINGS'])
    process.crawl(crawler)
    process.start()


@cli.command(context_settings=CONTEXT_SETTINGS)
@click.option('-i', '--input', 'file_path', type=click.Path(exists=True), default=None,
              help=''' Input file, if used by requested transformer (e.g. datajson transformer
              can use a dedup output) If a directory will be provided instead, it will be
              traversed recursivelly to obtain the list of files.''')
@click.option('-n', '--name', default=None,
              help='''If specified, the transformer will only act on the mentioned output (i.e. a scraper's name)''')
@click.argument('transformer')
@add_options(global_options)
def transform(file_path, name, transformer, **kwargs):
    '''Run a transformer on a scraper output to generate data in a format useful for other applications'''
    transformer = importlib.import_module(f"edscrapers.transformers.{transformer}.transform")
    transformer.transform(name)


@cli.command(context_settings=CONTEXT_SETTINGS)
@click.option('-f', '--format', default=None, type=click.Choice(['ascii', 'json'], case_sensitive=False),
              help='Format of the output.')
@add_options(global_options)
def compare(format, **kwargs):
    ''' Run a comparison algorhitm against AIR's resources. '''
    compare_cli()


@cli.command(context_settings=CONTEXT_SETTINGS)
@click.option('-n', '--name', default=None,
              help='Optionally, run the stats just for a specific output pipeline, identified by name (e.g. nces)')
@add_options(global_options)
def stats(name, **kwargs):
    ''' Run a statistics algorhitm on the data extracted to provide more insights about the output.
    This does not compare against AIR. '''
    click.echo('Making stats')


@cli.command(context_settings=CONTEXT_SETTINGS)
@click.option('-d', 'detached', is_flag=True, default=False, help='Run the server in a detached process')
@click.option('--debug', 'debug', is_flag=True, default=False, help='Flag for turning debug mode on')
@click.option('-p', '--port', 'port', type=click.INT, default=8050, help='Change the server port (default is 8050)')
@click.option('-h', '--host', 'host', default='0.0.0.0', help='Change the server host (default is 0.0.0.0)')
@add_options(global_options)
def dash(detached, port, host, debug, **kwargs):
    ''' Run the dash server for displaying HTML statistics. '''
    if detached:
        logger.warn('Dash app detached mode not yet implemented!')
        logger.info('Falling back to non-detached mode.')
    dash_app.run_server(debug=debug, dev_tools_hot_reload=debug, host=host)



if __name__ == '__main__':
    cli()
