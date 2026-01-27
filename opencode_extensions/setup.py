from setuptools import setup, find_packages

setup(
    name="opencode_extensions",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        "opencode.plugins": [
            "sound = opencode_extensions.plugins.sound:SoundPlugin",
            "voice = opencode_extensions.plugins.voice:VoicePlugin",
        ]
    },
)
