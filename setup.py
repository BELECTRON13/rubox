import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

requirements = [
    'aiohttp'
]

setuptools.setup(
    name="rubox",
    version="0.1.0",
    author="mohammadali",
    author_email="mohammadhoseinpoor167@gmail.com",
    description="A powerful library designed for building bots on the Rubika platform.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/BELECTRON13/rubox",
    install_requires = requirements,
    packages=setuptools.find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)