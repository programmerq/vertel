from setuptools import setup, find_packages

setup(
    name='vertel',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        line.strip() for line in open('requirements.txt') if line.strip()
    ],
    entry_points={
        'console_scripts': [
            'vertel-index=vertel.index_binary:main',
            'vertel-process=vertel.process:main'
        ]
    },
    include_package_data=True,
    description='CLI tool to analyze Go binary logs to identify the version that produced the logs',
    author='Jeff Anderson',
    author_email='jeff@goteleport.com',
    url='https://github.com/your-repo',  # Replace with your repository URL
    classifiers=[
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
    ],
)
