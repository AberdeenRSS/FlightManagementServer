from setuptools import setup, find_packages

setup(
    name="flightmanagementserver",
    packages=find_packages(),
)

setup(
    name="amqtt-oauth",
    version="1.0.2",
    packages=['amqtt_oauth'],
    platforms='all',
    install_requires=[
        'amqtt',
    ],
    classifiers=[
        'Programming Language :: Python :: 3.10',
    ],
    entry_points={
        'hbmqtt.broker.plugins': [
            'oauth = amqtt_oauth:OAuthPlugin',
        ],
    }
)