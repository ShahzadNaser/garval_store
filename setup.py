from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in garval_store/__init__.py
from garval_store import __version__ as version

setup(
	name="garval_store",
	version=version,
	description="garval_store",
	author="ShahzadNaser",
	author_email="shahzadnaser1122@gmail.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
