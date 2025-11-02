from setuptools import find_packages,setup

setup(
    name='chatapp',
    version='0.0.1',
    author='Shreyas R P',
    author_email='shreyasrpshreyas@gmail.com',
    install_requires=["openai","langchain","langchain-openai","python-dotenv"],
    packages=find_packages()
)
