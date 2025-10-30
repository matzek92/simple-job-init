"""
Setup-Konfiguration für Simple Job Init.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="sji",
    version="0.2.0",
    author="matzek92",
    author_email="matthias@kasperidus.de",
    description="SJI - Eine einfache Python-Bibliothek für Job-Initialisierung",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/matzek92/simple-job-init",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[],
)
