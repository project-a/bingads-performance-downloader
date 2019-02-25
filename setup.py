from setuptools import setup, find_packages

setup(
    name='bingads-performance-downloader',

    version='2.3.0',

    description="Downloads data from the BingAds Api to local files for usage in a data warehouse",

    install_requires=[
        'bingads==11.12.2',
        'click>=6.0'
    ],

    packages=find_packages(),

    author='Mara contributors',
    license='MIT',

    entry_points={
        'console_scripts': [
            'download-bingsads-performance-data=bingads_downloader.cli:download_data',
            'refresh-bingsads-api-oauth2-token=bingads_downloader.cli:refresh_oauth2_token'
        ]
    },
    python_requires='>=3.6'
)
