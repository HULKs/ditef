import setuptools

setuptools.setup(
    name='ditef_producer_genetic_algorithm_sliding',
    version='0.0.1',
    packages=[
        'ditef_producer_genetic_algorithm_sliding',
    ],
    entry_points={
        'console_scripts': [
            'ditef-producer-genetic-algorithm-sliding = ditef_producer_genetic_algorithm_sliding:main',
        ],
    },
    install_requires=[
        'aiohttp>=3.6.2',
        'click>=7.1.2',
        'numpy>=1.19.1',
        'pandas>=1.1.4',
        'ruamel.yaml>=0.16.10',
        'simplejson>=3.17.2',
    ],
)
