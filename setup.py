from setuptools import setup

setup(
    name = 'CubePostprocessor',
    version = '1.0',
    description = 'Postprocesses g-code to make it compatible with the Cube 2 system',
    author = 'spegelius, devincody',
    author_email = '',
    packages = ['CubePostprocessor'],
    include_package_data = True,
    entry_points={
        'console_scripts': ['cubifier = cubifier:main'],
    }
)