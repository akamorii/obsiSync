import os
import re
import shutil
import subprocess
from setSettings import BASE_DIR

ARCHIVE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class GitScript:
    """
    Работает с репо как с хранилищем архивов: shallow-клон (только последний коммит),
    partial clone без содержимого файлов и sparse-checkout, который скачивает
    только нужную папку с датой.
    """

    def __init__(self, link, path=os.path.join(BASE_DIR, "repo")):
        self.link = link
        self.path = path
        self.remoteBranch = None


    def _run(self, *args, cwd=None):
        result = subprocess.run(["git", *args], cwd=cwd or self.path, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed:\n{result.stderr.strip()}")
        return result.stdout.strip()


    def _isPartialClone(self):
        if not os.path.isdir(os.path.join(self.path, ".git")):
            return False
        try:
            return bool(self._run("config", "remote.origin.partialclonefilter"))
        except RuntimeError:
            return False


    def prepare(self):
        """Обновляет локальную копию до последнего коммита, не скачивая содержимое архивов."""
        if not self._run("ls-remote", "--heads", self.link, cwd=BASE_DIR):
            # пустой репо: клонировать нечего, просто готовим папку для первого push
            if not os.path.isdir(os.path.join(self.path, ".git")):
                shutil.rmtree(self.path, ignore_errors=True)
                self._run("init", "-q", self.path, cwd=BASE_DIR)
                self._run("remote", "add", "origin", self.link)
            self.remoteBranch = None
            return
        if not self._isPartialClone():
            shutil.rmtree(self.path, ignore_errors=True)
            self._run("clone", "-q", "--depth", "1", "--filter=blob:none", "--no-checkout",
                      self.link, self.path, cwd=BASE_DIR)
        self._run("fetch", "-q", "--depth", "1", "--prune", "origin")
        self.remoteBranch = self._run("rev-parse", "--abbrev-ref", "origin/HEAD")


    def checkout(self, *folders):
        """Оставляет в рабочей папке только указанные папки, скачивая лишь их содержимое."""
        self._run("sparse-checkout", "set", "--no-cone", *(f"/{f}/" for f in folders))
        if self.remoteBranch:
            self._run("reset", "-q", "--hard", self.remoteBranch)
        self._run("clean", "-fdq")


    def latestArchive(self):
        if not self.remoteBranch:
            return None
        names = self._run("ls-tree", "--name-only", self.remoteBranch).splitlines()
        archives = sorted(name for name in names if ARCHIVE_PATTERN.match(name))
        return archives[-1] if archives else None


    def push(self, folder, message):
        self._run("add", "-A", "--", folder)
        self._run("commit", "-q", "-m", message)
        try:
            self._run("push", "-q", "-u", "origin", "HEAD")
        except RuntimeError as e:
            raise RuntimeError(f"{e}\nrepo was updated by another device, run the command again")
