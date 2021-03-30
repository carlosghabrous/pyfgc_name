"""
setup.py for pyfgc-name.

For reference see
https://packaging.python.org/guides/distributing-packages-using-setuptools/

"""
from pathlib import Path
from setuptools import setup, find_packages


HERE = Path(__file__).parent.absolute()
with (HERE / 'README.md').open('rt') as fh:
    LONG_DESCRIPTION = fh.read().strip()


REQUIREMENTS: dict = {
    'core': [
        'pyfgc_const'
    ],
    'test': [
        'pytest',
    ],
    'dev': [
        # 'requirement-for-development-purposes-only',
    ],
    'doc': [
        'sphinx',
    ],
}


setup(
    name='pyfgc-name',
    version="1.3.2",

    author='Carlos Ghabrous Larrea, Marc Magrans de Abril, Joao Afonso',
    author_email='carlos.ghabrous@cern.ch',
    description='FGC name, group and subdevices parsers and more',
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
   	url='https://gitlab.cern.ch/ccs/fgc/tree/master/sw/clients/python/pyfgc_name',


    packages=find_packages(),
    python_requires='>=3.6, <4',
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],

    install_requires=REQUIREMENTS['core'],
    extras_require={
        **REQUIREMENTS,
        # The 'dev' extra is the union of 'test' and 'doc', with an option
        # to have explicit development dependencies listed.
        'dev': [req
                for extra in ['dev', 'test', 'doc']
                for req in REQUIREMENTS.get(extra, [])],
        # The 'all' extra is the union of all requirements.
        'all': [req for reqs in REQUIREMENTS.values() for req in reqs],
    },
)
