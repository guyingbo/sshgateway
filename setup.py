try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
import os.path
import re
VERSION_RE = re.compile(r'''__version__ = ['"]([0-9.]+)['"]''')
BASE_PATH = os.path.dirname(__file__)


with open(os.path.join(BASE_PATH, 'sshgateway.py')) as f:
    try:
        version = VERSION_RE.search(f.read()).group(1)
    except IndexError:
        raise RuntimeError('Unable to determine version.')


setup(
    name='sshgateway',
    description='A ssh gateway server',
    license='MIT',
    version=version,
    author='Yingbo Gu',
    author_email='tensiongyb@gmail.com',
    maintainer='Yingbo Gu',
    maintainer_email='tensiongyb@gmail.com',
    url='https://github.com/guyingbo/sshgateway',
    py_modules=['sshgateway'],
    install_requires=[
        'pytoml>=0.1.14',
        'asyncssh>=1.10.1',
    ],
    entry_points={
        'console_scripts': [
            'sshgateway = sshgateway:main',
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3.6',
    ],
)
