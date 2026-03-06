from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="codex-guardian",
    version="0.1.0",
    author="Jithendra Nara",
    author_email="your.email@example.com",
    description="Protect your Codex CLI sessions from runaway token burn",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/JithendraNara/codex-guardian",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Monitoring",
    ],
    python_requires=">=3.10",
    install_requires=[
        "click>=8.1.7",
        "rich>=13.7.0",
        "requests>=2.31.0",
        "python-telegram-bot>=20.7",
        "aiohttp>=3.9.0",
    ],
    entry_points={
        "console_scripts": [
            "codex-guardian=codex_guardian.cli:cli",
        ],
    },
)
