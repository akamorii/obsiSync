import os
import art
import yaml
from dotenv import dotenv_values, set_key

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.yml")
ENV_FILE = os.path.join(BASE_DIR, ".env")


def loadConfig():
    if not os.path.isfile(CONFIG_FILE):
        raise RuntimeError("config.yml not found, run setSettings.py first")
    with open(CONFIG_FILE) as f:
        data = yaml.safe_load(f) or {}
    for field, subfield in (("crypt", "encrypted"), ("repo", "link"), ("storage", "absolutePath")):
        if data.get(field, {}).get(subfield) is None:
            raise RuntimeError(f"'{field}.{subfield}' missing in config.yml, run setSettings.py")
    return data


class SetSettings:

    @staticmethod
    def _readConfig():
        if not os.path.isfile(CONFIG_FILE):
            return {}
        with open(CONFIG_FILE) as f:
            return yaml.safe_load(f) or {}


    @staticmethod
    def _writeConfig(data):
        with open(CONFIG_FILE, "w") as f:
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)


    @staticmethod
    def _setCryptKey():
        if not os.path.isfile(ENV_FILE):
            open(ENV_FILE, "w").close()
        if dotenv_values(ENV_FILE).get("SECRET_KEY"):
            return
        key = ""
        while not key:
            key = input("input encrypt key -> ").strip()
        set_key(ENV_FILE, "SECRET_KEY", key)


    @staticmethod
    def _set2yml(data, field, subfield, prompt, check=None):
        section = data.setdefault(field, {}) or {}
        data[field] = section
        if section.get(subfield) not in (None, ""):
            return
        while True:
            value = input(f"{prompt} -> ").strip()
            error = check(value) if check else None
            if value and not error:
                break
            print(error or "value can't be empty")
        section[subfield] = value


    @staticmethod
    def _checkStorage(path):
        if not os.path.isabs(path):
            return "absolute path expected"
        if not os.path.isdir(path):
            return f"directory '{path}' doesn't exist"


    def __init__(self):
        data = SetSettings._readConfig()
        data.setdefault("crypt", {}).setdefault("encrypted", True)
        SetSettings._setCryptKey()
        SetSettings._set2yml(data, "repo", "link", "input git repo link")
        SetSettings._set2yml(data, "storage", "absolutePath", "input absolute path to vault",
                             check=SetSettings._checkStorage)
        SetSettings._writeConfig(data)
        print(f"settings saved to {CONFIG_FILE}")


if __name__ == '__main__':
    print(art.text2art("Sync"))
    start = SetSettings()
