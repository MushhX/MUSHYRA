"""
Mux Programming Language - Setup
Creador: MushhX
"""

from setuptools import setup, find_packages

setup(
    name='mux-lang',
    version='1.0.0',
    description='Lenguaje de programación moderno, accesible y ligero',
    author='MushhX',
    author_email='mushhdev@gmail.com',
    url='https://github.com/MushhX/Mux',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'mux=mux_lang.cli:main',
            'mux-pkg=mux_lang.package_manager:main',
        ],
    },
    install_requires=[
        'requests>=2.31.0',
        'colorama>=0.4.6',
    ],
    extras_require={
        'web': ['flask>=3.0.0', 'jinja2>=3.1.2'],
        'discord': ['discord.py>=2.3.0'],
        'telegram': ['python-telegram-bot>=20.0'],
        'whatsapp': ['twilio>=8.10.0'],
        'full': [
            'flask>=3.0.0',
            'jinja2>=3.1.2',
            'discord.py>=2.3.0',
            'python-telegram-bot>=20.0',
            'twilio>=8.10.0',
            'pyinstaller>=6.0.0',
        ],
    },
    python_requires='>=3.8',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
)
