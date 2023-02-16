import pathlib
import setuptools

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text()

# call to setup()
setuptools.setup(
    name="scipper",
    version="0.1.6",
    description="Easy access to scpi measurement devices",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/MitchiLaser/scipper",
    author="Michael Hohenstein",
    author_email="michael@hohenste.in",
    license="MPL-2.0",
    classifiers=[
        "Topic :: Education",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Physics",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Operating System :: OS Independent",
        "Intended Audience :: Education",
        "Intended Audience :: Science/Research",
        "Typing :: Typed"
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    include_package_data=True,
    install_requires=[
        "numpy",
        "pyvisa"
    ],
    keywords=("SCPI oscilloscope measurement lab laboratory practical courses physics"),
)

