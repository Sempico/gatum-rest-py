from setuptools import setup, find_packages

setup(
    name="gatum-rest-py",
    version="1.0.0",

    description='Python library for interacting with Gatum REST API',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='Sempico Solutions Group LTD',
    author_email='support@sempico.solutions',
    download_url='https://github.com/Sempico/gatum-rest-py',
    license='MIT License',
    classifiers=[
        "Development Status :: 4 - Beta",
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
    ],
    install_requires=["requests"],
    packages=find_packages(),
)
