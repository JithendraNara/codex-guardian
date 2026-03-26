from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="codex-guardian",
    version="0.2.0",
    author="Jithendra Nara",
    author_email="jithendra.n@gmail.com",
    description="Protect your Codex CLI sessions from runaway token burn",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/JithendraNara/codex-guardian",
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
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
    extras_require={
        "dev": [
            "pytest>=8.0.0",
            "pytest-mock>=3.12.0",
            "pytest-cov>=4.1.0",
            "flake8>=7.0.0",
            "black>=24.0.0",
            "mypy>=1.8.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "codex-guardian=codex_guardian.cli:cli",
        ],
    },
)
