import setuptools
import os

#REQUIREMENTS_FILE = "requirements.txt"
REQUIRED_PACKAGES = []
# REQUIRED_PACKAGES = [
#     "Faker==4.0.3",
#    "pyyaml==5.3.1",
# ]

#Load the required packages from requirements file
# if os.path.exists(REQUIREMENTS_FILE):
#     with open(REQUIREMENTS_FILE) as fp:
#         REQUIRED_PACKAGES = fp.read().splitlines()


setuptools.setup(
    name='prod_deployment',
    author='name',
    author_email='name@domain.com',
    url="www.domain.com",
    version='0.0.1',
    install_requires=REQUIRED_PACKAGES,
    packages=setuptools.find_packages(),
)

