import setuptools

setuptools.setup(
    name='ditef_router',
    version='0.0.1',
    packages=[
        'router',
    ],
    entry_points={
        'console_scripts': [
            'ditef-router = router:main',
        ],
    },
    install_requires=[
        'aiohttp>=3.6.2',
        'click>=7.1.2',
    ],
)
