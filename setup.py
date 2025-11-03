from setuptools import find_packages,setup

setup(
    name='chatapp',
    version='0.0.1',
    # author_email intentionally omitted for public repo privacy
    install_requires=["openai","langchain","langchain-openai","python-dotenv"],
    packages=find_packages()
)
