#!/usr/bin/env python

import os
import sys

from codecs import open

from setuptools import setup


here = os.path.abspath(os.path.dirname(__file__))

packages = ['grabstats']

requires = [
    'arrow',
    'beautifulsoup4',
    'click',
    'lxml',
    'pandas',
    'pyyaml',
]

# test_requirements = []

about = {}
with open(os.path.join(here, 'grabstats', '__version__.py'), 'r', 'utf-8') as f:
    exec(f.read(), about)

with open('README.md', 'r', 'utf-8') as f:
    readme = f.read()

setup(
    name=about['__title__'],
    version=about['__version__'],
    description=about['__description__'],
    long_description=readme,
    long_description_content_type='text/markdown',
    author=about['__author__'],
    author_email=about['__author_email__'],
    url=about['__url__'],
    packages=packages,
    # package_data={},
    package_dir={'grabstats': 'grabstats'},
    include_package_data=True,
    # python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*",
    install_requires=requires,
    license=about['__license__'],
    zip_safe=False,
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
    ],
    entry_points={
        'console_scripts': [
            'grabstats = grabstats.cli:main',
        ],
    },
    # cmdclass={},
    # tests_require=test_requirements,
    # extra_require={},
)


# 'setup.py publish' shortcut.
if sys.argv[-1] == 'publish':
    os.system('python setup.py sdist bdist_wheel')
    os.system('twine upload dist/*')
    sys.exit()
