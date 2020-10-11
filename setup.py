import sys
from pathlib import Path

__dir__ = Path(__file__).absolute().parent
# Remove current dir from sys.path, otherwise setuptools will peek up our
# module instead of system's.
sys.path.pop(0)
from setuptools import setup

sys.path.append(".")
import sdist_upip

setup(
    name='micropython-socks',
    py_modules=['socks'],
    version='1.0.1',
    description='MicroPython library implementing SOCKS server.',
    long_description='This library lets you start SOCKS server.',
    keywords='socks server proxy micropython',
    url='https://github.com/kost/micropython-socks',
    author='Vlatko Kosturjak',
    author_email='kost@linux.hr',
    maintainer='Vlatko Kosturjak',
    maintainer_email='kost@linux.hr',
    license='MIT',
    cmdclass={'sdist': sdist_upip.sdist},
    project_urls={
        'Bug Reports': 'https://github.com/kost/micropython-socks/issues',
        'Documentation': 'https://github.com/kost/micropython-socks/blob/master/README.md',
        'Source': 'https://github.com/kost/micropython-socks',
    },
    classifiers = [
        'Development Status :: 5 - Production/Stable',
        'Programming Language :: Python :: Implementation :: MicroPython',
        'License :: OSI Approved :: MIT License',
    ],
)
