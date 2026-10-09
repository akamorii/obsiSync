import hashlib
import json
import os
import shutil
from datetime import datetime
from setSettings import BASE_DIR

STATE_FILE = os.path.join(BASE_DIR, ".sync_state.json")
IGNORED_DIRS = {".git"}


class Synchronize:
    """
    Трёхсторонний merge: локальная папка, распакованный архив и base -
    снимок хэшей на момент последней синхронизации (.sync_state.json).
    Изменение с одной стороны применяется, локальные правки не затираются,
    при конфликте удалённая версия сохраняется рядом как *.conflict-<дата>.
    """

    def __init__(self, storage, stateFile=STATE_FILE):
        self.storage = storage
        self.stateFile = stateFile


    @staticmethod
    def _hash(path):
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()


    @staticmethod
    def snapshot(root):
        result = {}
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
            for name in filenames:
                full = os.path.join(dirpath, name)
                result[os.path.relpath(full, root).replace(os.sep, "/")] = Synchronize._hash(full)
        return result


    def loadState(self):
        if not os.path.isfile(self.stateFile):
            return None
        with open(self.stateFile) as f:
            return json.load(f).get(self.storage)


    def saveState(self, snapshot):
        data = {}
        if os.path.isfile(self.stateFile):
            with open(self.stateFile) as f:
                data = json.load(f)
        data[self.storage] = snapshot
        with open(self.stateFile, "w") as f:
            json.dump(data, f, indent=1)


    def _copy(self, incoming, rel, dstRel=None):
        dst = os.path.join(self.storage, dstRel or rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(os.path.join(incoming, rel), dst)


    def _remove(self, rel):
        path = os.path.join(self.storage, rel)
        os.remove(path)
        parent = os.path.dirname(path)
        while parent != self.storage and not os.listdir(parent):
            os.rmdir(parent)
            parent = os.path.dirname(parent)


    @staticmethod
    def _conflictName(rel):
        root, ext = os.path.splitext(rel)
        return f"{root}.conflict-{datetime.now():%Y-%m-%d_%H%M%S}{ext}"


    def merge(self, incoming):
        base = self.loadState()
        local = Synchronize.snapshot(self.storage)
        remote = Synchronize.snapshot(incoming)
        report = {"added": [], "updated": [], "deleted": [], "conflicts": []}

        for rel in sorted(set(local) | set(remote)):
            l, r = local.get(rel), remote.get(rel)
            b = base.get(rel) if base is not None else None
            if l == r:
                continue
            if r is None:
                # удалён в архиве и не менялся локально -> удаляем; иначе это новый/изменённый локальный файл
                if b is not None and b == l:
                    self._remove(rel)
                    report["deleted"].append(rel)
            elif l is None:
                # удалён локально, а в архиве не менялся -> оставляем удалённым
                if b is not None and b == r:
                    continue
                self._copy(incoming, rel)
                report["added"].append(rel)
            elif l == b:
                self._copy(incoming, rel)
                report["updated"].append(rel)
            elif r == b:
                continue
            else:
                conflict = Synchronize._conflictName(rel)
                self._copy(incoming, rel, conflict)
                report["conflicts"].append(conflict)

        self.saveState(remote)
        return report
