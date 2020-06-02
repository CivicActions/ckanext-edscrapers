import sys
import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

if sys.version_info < (3,7):
    sys.exit('Sorry, Python < 3.7 is not supported')

setuptools.setup(
    name="edscrapers",
    version="1.0.0",
    author="Datopian",
    author_email="contact@datopian.com",
    description="Scrapers and transformers for U.S. Dept. of Ed. data",
    long_description=long_description,
    long_description_content_type="text/markdown",
    # url="https://github.com/pypa/sampleproject",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
    install_requires=[
        'Click'
    ],
    entry_points='''
        [console_scripts]
        eds=edscrapers.cli:cli
    '''
)
