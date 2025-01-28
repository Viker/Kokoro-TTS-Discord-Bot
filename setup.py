from setuptools import setup, find_packages

setup(
    name="kokoro-bot",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "discord.py>=2.0.0",
        "pyyaml>=6.0",
        "numpy>=1.21.0",
        "soundfile>=0.10.3",
        "kokoro_onnx",
    ],
    python_requires=">=3.8",
)