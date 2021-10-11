from setuptools import find_packages, setup


def get_install_requires():
    with open("requirements.txt", "r") as f:
        return [line.strip() for line in f.readlines() if not line.startswith("-")]


setup(
    name="gdsfactory",
    url="https://github.com/gdsfactory/gdsfactory",
    version="3.3.9",
    author="gdsfactory community",
    scripts=["gdsfactory/gf.py"],
    description="python libraries to generate GDS layouts",
    packages=find_packages(),
    include_package_data=True,
    install_requires=get_install_requires(),
    python_requires=">=3.7",
    license="MIT",
    entry_points="""
        [console_scripts]
        gf=gdsfactory.gf:gf
    """,
)
