import argparse
import os
import shutil
import tempfile
import zipfile
from datetime import date, datetime
from crypto import Crypt
from gitScript import GitScript
from setSettings import loadConfig
from synchronize import IGNORED_DIRS, Synchronize


class Main:

    def __init__(self):
        config = loadConfig()
        self.storage = os.path.abspath(config["storage"]["absolutePath"])
        self.encrypted = bool(config["crypt"]["encrypted"])
        if not os.path.isdir(self.storage):
            raise RuntimeError(f"storage '{self.storage}' doesn't exist")
        self.git = GitScript(config["repo"]["link"])
        self.sync = Synchronize(self.storage)


    @staticmethod
    def _pack(src, archive):
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
            for dirpath, dirnames, filenames in os.walk(src):
                dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
                for name in filenames:
                    full = os.path.join(dirpath, name)
                    zf.write(full, os.path.relpath(full, src))


    @staticmethod
    def _printReport(report):
        for kind, files in report.items():
            for rel in files:
                print(f"  {kind:<9} {rel}")
        if report["conflicts"]:
            print("conflicts: remote versions saved next to local files, resolve them manually")


    def _mergeLatest(self, tmp):
        archive = self.git.latestArchive()
        if archive is None:
            return None
        zipPath = os.path.join(tmp, "incoming.zip")
        if archive.endswith(".enc"):
            Crypt().decryptFile(archive, zipPath)
        else:
            shutil.copy(archive, zipPath)
        unpacked = os.path.join(tmp, "incoming")
        with zipfile.ZipFile(zipPath) as zf:
            zf.extractall(unpacked)
        print(f"merging {os.path.basename(archive)} into {self.storage}")
        report = self.sync.merge(unpacked)
        Main._printReport(report)
        return report


    def fetch(self):
        self.git.prepare()
        with tempfile.TemporaryDirectory() as tmp:
            if self._mergeLatest(tmp) is None:
                print("repo has no archives yet")


    def send(self):
        self.git.prepare()
        name = date.today().isoformat() + (".zip.enc" if self.encrypted else ".zip")
        with tempfile.TemporaryDirectory() as tmp:
            # сначала вливаем то, что уже есть в репо, чтобы не затереть чужие изменения
            self._mergeLatest(tmp)
            zipPath = os.path.join(tmp, "outgoing.zip")
            Main._pack(self.storage, zipPath)
            target = os.path.join(self.git.path, name)
            if self.encrypted:
                Crypt().encryptFile(zipPath, target)
            else:
                shutil.copy(zipPath, target)
        self.git.push(name, f"sync {datetime.now():%Y-%m-%d %H:%M:%S}")
        self.sync.saveState(Synchronize.snapshot(self.storage))
        print(f"pushed {name}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="obsidian vault sync via git")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("-s", "--send", action="store_true", help="archive, encrypt and push vault")
    mode.add_argument("-f", "--fetch", action="store_true", help="pull, decrypt and merge vault")
    args = parser.parse_args()

    try:
        main = Main()
        main.send() if args.send else main.fetch()
    except RuntimeError as e:
        raise SystemExit(f"error: {e}")
