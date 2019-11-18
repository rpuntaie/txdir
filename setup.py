from setuptools import setup


with open("README.rst") as f:
    readme = f.read()


setup(
    name="txdir",
    version="1.0.0",
    description="Creating file tree from text tree and vice versa",
    long_description=readme,
    long_description_content_type='text/x-rst',
    license="MIT",
    author="Roland Puntaier",
    author_email="roland.puntaier@gmail.com",
    url="https://github.com/rpuntaie/txdir",
    py_modules=["txdir"],
    data_files=[("man/man1", ["txdir.1"])],
    python_requires='>=3.6',
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Environment :: Console",
        "Topic :: Utilities",
    ],
    entry_points="""
       [console_scripts]
       txdir=txdir:main
       """
)
