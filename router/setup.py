import setuptools

setuptools.setup(
    name='ditef_router',
    version='0.0.1',
    packages=[
        'ditef_router',
        'ditef_router_tester',
    ],
    entry_points={
        'console_scripts': [
            'ditef-router = ditef_router:main',
            'ditef-router-tester = ditef_router_tester:main',
        ],
    },
    install_requires=[
        'aiohttp>=3.6.2',
        'click>=7.1.2',
    ],
)
