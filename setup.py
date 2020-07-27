from setuptools import setup

setup(
    name = 'Cubifier',
    version = '1.0',
    description = 'Postprocesses g-code to make it compatible with the Cube 2 system',
    author = 'spegelius, devincody',
    author_email = '',
    packages = ['CubePostprocessor'],
    include_package_data = True,
    scripts=['cubifier.py'],
)