#!/usr/bin/env python

import setuptools

pypi_package_name = 'unifi-video'

with open('unifi_video/_version.py', 'r') as f:
    exec(f.read())

with open('README.md', 'r') as fh:
    readme = fh.read()

setuptools.setup(
    name=pypi_package_name,
    version=__version__,
    author='yuppity',
    author_email='yuppity_pypi@wubbalubba.com',
    description='Python API for UniFi Video',
    long_description=readme,
    long_description_content_type='text/markdown',
    url='https://github.com/yuppity/unifi-video-api',
    packages=['unifi_video'],
    classifiers=[
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
    ],
    python_requires='>=2.7',
)
