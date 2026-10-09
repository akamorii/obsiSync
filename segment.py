import hashlib
import json
import os

MANIFEST = "manifest.json"


class Segment:
    """Режет файл на части фиксированного размера и собирает обратно с проверкой sha256."""

    @staticmethod
    def split(src, dstDir, size):
        os.makedirs(dstDir, exist_ok=True)
        name = os.path.basename(src)
        h = hashlib.sha256()
        parts = []
        with open(src, "rb") as f:
            while chunk := f.read(size):
                part = f"{name}.{len(parts):03d}"
                with open(os.path.join(dstDir, part), "wb") as p:
                    p.write(chunk)
                h.update(chunk)
                parts.append(part)
        manifest = {"file": name, "size": os.path.getsize(src), "sha256": h.hexdigest(), "parts": parts}
        with open(os.path.join(dstDir, MANIFEST), "w") as f:
            json.dump(manifest, f, indent=1)
        return parts


    @staticmethod
    def join(srcDir, dstDir):
        manifestPath = os.path.join(srcDir, MANIFEST)
        if not os.path.isfile(manifestPath):
            raise RuntimeError(f"'{MANIFEST}' not found in '{os.path.basename(srcDir)}'")
        with open(manifestPath) as f:
            manifest = json.load(f)
        missing = [p for p in manifest["parts"] if not os.path.isfile(os.path.join(srcDir, p))]
        if missing:
            raise RuntimeError(f"missing segments: {', '.join(missing)}")

        dst = os.path.join(dstDir, os.path.basename(manifest["file"]))
        h = hashlib.sha256()
        with open(dst, "wb") as out:
            for part in manifest["parts"]:
                with open(os.path.join(srcDir, part), "rb") as p:
                    chunk = p.read()
                h.update(chunk)
                out.write(chunk)
        if h.hexdigest() != manifest["sha256"]:
            raise RuntimeError("assembled archive checksum mismatch, segments are corrupted")
        return dst
