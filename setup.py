"""Setuptools compatibility metadata; PEP 517 configuration is in pyproject.toml."""

from setuptools import find_packages, setup

from mux_lang._version import __version__


setup(
    name="mux-lang",
    version=__version__,
    description="Intérprete y herramientas para el lenguaje Mux",
    author="MushhX",
    author_email="mushhdev@gmail.com",
    url="https://github.com/MushhX/Mux",
    packages=find_packages(exclude=("tests", "tests.*")),
    entry_points={
        "console_scripts": [
            "mux=mux_lang.cli:main",
            "mux-pkg=mux_lang.package_manager:main",
        ],
    },
    install_requires=[],
    extras_require={
        "web": ["flask>=2.3,<4"],
        "discord": ["discord.py>=2.3,<3"],
        "telegram": ["python-telegram-bot>=20,<23"],
        "whatsapp": ["twilio>=8.10,<10"],
        "crypto": ["cryptography>=41,<47"],
        "build": ["pyinstaller>=6,<7", "Pillow>=9,<13"],
        "full": [
            "flask>=2.3,<4",
            "discord.py>=2.3,<3",
            "python-telegram-bot>=20,<23",
            "twilio>=8.10,<10",
            "cryptography>=41,<47",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
