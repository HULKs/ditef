import setuptools

setuptools.setup(
    name='ditef_worker',
    version='0.0.1',
    packages=[
        'ditef_worker',
    ],
    entry_points={
        'console_scripts': [
            'ditef-worker = ditef_worker:main',
        ],
    },
    install_requires=[
        'click>=7.1.2',
        'requests>=2.24.0',
    ],
)
