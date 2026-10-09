import os
import re
import subprocess
from setSettings import BASE_DIR

ARCHIVE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}\.zip(\.enc)?$")


class GitScript:

    def __init__(self, link, path=os.path.join(BASE_DIR, "repo")):
        self.link = link
        self.path = path


    def _run(self, *args, cwd=None):
        result = subprocess.run(["git", *args], cwd=cwd or self.path, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed:\n{result.stderr.strip()}")
        return result.stdout.strip()


    def _remoteHasCommits(self):
        return bool(self._run("ls-remote", "--heads", "origin"))


    def prepare(self):
        """Клонирует репо при первом запуске, иначе подтягивает свежие коммиты."""
        if not os.path.isdir(os.path.join(self.path, ".git")):
            self._run("clone", self.link, self.path, cwd=BASE_DIR)
        elif self._remoteHasCommits():
            self._run("pull", "--rebase")


    def push(self, fileName, message):
        # архив за ту же дату, но с другим расширением (.zip / .zip.enc) больше не нужен
        stem = fileName.split(".")[0]
        for name in os.listdir(self.path):
            if name != fileName and name.split(".")[0] == stem and ARCHIVE_PATTERN.match(name):
                self._run("rm", "-q", "--", name)
        self._run("add", "--", fileName)
        self._run("commit", "-m", message)
        self._run("push", "-u", "origin", "HEAD")


    def latestArchive(self):
        archives = sorted(name for name in os.listdir(self.path) if ARCHIVE_PATTERN.match(name))
        return os.path.join(self.path, archives[-1]) if archives else None
