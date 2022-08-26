from setuptools import find_packages, find_packages, setup

setup(
    name='logging_learning',
    version='0.0.1',
    description='Package to test and learn about logging',
    url='git@github.com/ocjr/joes-python-ideas.git',
    author='Joe OConnell',
    author_email='github@bravoindia.net',
    license='unlicense',
    packages=find_packages(),
    install_requires=[
        'logging'
    ],
    zip_safe=False
)
