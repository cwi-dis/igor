"""A setuptools based setup module.

See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""
# Enable coverage if installed and enabled through COVERAGE_PROCESS_START environment var
try:
    import coverage
    coverage.process_startup()
except ImportError:
    pass
# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path
import os
import sys

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Get the version number from the igor module
with open(path.join(here, 'igor', '_version.py')) as f:
    exec(f.read())
    
#
# We need some helpers to determine the package_data, because we want to
# recursively include the plugins
#
def package_files(directory):
    paths = []
    for (path, directories, filenames) in os.walk(directory):
        for filename in filenames:
            paths.append(os.path.join('..', path, filename))
    return paths


package_data={
    'igor': 
        package_files('igor/static')+
        package_files('igor/template')+ 
        package_files('igor/bootScripts') +
        package_files('igor/plugins') +
        package_files('igor/std-plugins') +
        package_files('igor/ca') +
        package_files('igor/igorDatabase.empty')
}

setup(
    name='igor-iot',

    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version=VERSION,

    description='REST-like IoT server',
    long_description=long_description,
    long_description_content_type="text/markdown",
    
    # The project's main homepage.
    url='https://github.com/cwi-dis/igor',
    # Other URLs
    project_urls={
        'Documentation': 'https://igor-iot.readthedocs.io',
        'Issue tracker': 'https://github.com/cwi-dis/igor/issues',
    },

    # Author details
    author='Jack Jansen',
    author_email='Jack.Jansen@cwi.nl',

    # Choose your license
    license='MIT',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 4 - Beta',
        'Framework :: Flask',
        # Indicate who your project is intended for
        'Intended Audience :: End Users/Desktop',
        'Topic :: Database',
        'Topic :: Home Automation',

        # Pick your license as you wish (should match "license" above)
        "License :: OSI Approved :: MIT License",

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
    ],

    # What does your project relate to?
    #keywords='sample setuptools development',

    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    packages=["igor", "igor.access"],

    # Alternatively, if you want to distribute just a my_module.py, uncomment
    # this:
       py_modules=["igorVar", "igorControl", "igorSetup", "igorCA", "igorServlet"],

    # List run-time dependencies here.  These will be installed by pip when
    # your project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires= ["future", "httplib2", "requests", "flask", "gevent", "python-dateutil", "py-dom-xpath-six", "passlib", "pyjwt", "pyopenssl", "markdown"],

    # List additional groups of dependencies here (e.g. development
    # dependencies). You can install these using the following syntax,
    # for example:
    # $ pip install -e .[dev,test]
    #extras_require={
    #    'dev': ['check-manifest'],
    #    'test': ['coverage'],
    #},

    # If there are data files included in your packages that need to be
    # installed, specify them here.  If using Python 2.6 or less, then these
    # have to be included in MANIFEST.in as well.
    package_data=package_data,
    include_package_data=True,
    # Although 'package_data' is the preferred approach, in some case you may
    # need to place data files outside of your packages. See:
    # http://docs.python.org/3.4/distutils/setupscript.html#installing-additional-files # noqa
    # In this case, 'data_file' will be installed into '<sys.prefix>/my_data'
    #data_files=[('my_data', ['data/data_file'])],

    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # pip to create the appropriate form of executable for the target platform.
    entry_points={
        'console_scripts': [
            'igorServer=igor.__main__:main',
            'igorVar=igorVar:main',
            'igorControl=igorControl:main',
            'igorSetup=igorSetup:main',
            'igorCA=igorCA:main'
        ],
    },
    # And the test suite
    test_suite="test",
)
