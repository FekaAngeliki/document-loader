from setuptools import setup, find_packages

setup(
    name="document-loader",
    version="0.1.1",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.11",
    install_requires=[
        "aiofiles>=24.1.0",
        "asyncpg>=0.30.0",
        "click>=8.2.0",
        "httpx>=0.28.1",
        "pydantic>=2.11.4",
        "pydapper>=0.12.0",
        "python-dotenv>=1.1.0",
        "pyyaml>=6.0.2",
    ],
    entry_points={
        "console_scripts": [
            "document-loader=document_loader.cli:main",
            "docloader=document_loader.cli:main",
        ],
    },
)