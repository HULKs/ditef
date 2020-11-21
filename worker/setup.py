import setuptools

setuptools.setup(
    name='ditef_worker',
    version='0.0.1',
    packages=[
        'worker',
    ],
    entry_points={
        'console_scripts': [
            'ditef-worker = worker:main',
        ],
    },
    install_requires=[
        'click>=7.1.2',
        'requests>=2.24.0',
    ],
)
