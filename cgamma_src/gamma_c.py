import struct
from pathlib import Path

import cgamma

_MAGIC = b"GAMM"

encode_postings = cgamma.encode_postings
decode_postings = cgamma.decode_postings


def write_cgamma_file(index: dict, path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "wb") as file:
        file.write(_MAGIC)
        file.write(struct.pack("<I", len(index)))

        for rule_name, classifications in index.items():
            rule_bytes = rule_name.encode("utf-8")
            file.write(struct.pack("<H", len(rule_bytes)))
            file.write(rule_bytes)
            file.write(struct.pack("<B", len(classifications)))

            for cls_name, postings in classifications.items():
                encoded = (
                    cgamma.encode_postings(sorted(postings))
                    if isinstance(postings, (list, tuple))
                    else postings
                )
                cls_bytes = cls_name.encode("utf-8")
                file.write(struct.pack("<B", len(cls_bytes)))
                file.write(cls_bytes)
                file.write(struct.pack("<I", len(encoded)))
                file.write(encoded)


def read_cgamma_file(path) -> dict:
    with open(Path(path), "rb") as file:
        if file.read(4) != _MAGIC:
            raise ValueError("bad magic")

        (num_rules,) = struct.unpack("<I", file.read(4))
        index = {}

        for _ in range(num_rules):
            (rule_name_len,) = struct.unpack("<H", file.read(2))
            rule_name = file.read(rule_name_len).decode("utf-8")

            (num_cls,) = struct.unpack("<B", file.read(1))
            classifications = {}

            for _ in range(num_cls):
                (cls_name_len,) = struct.unpack("<B", file.read(1))
                cls_name = file.read(cls_name_len).decode("utf-8")
                (encoded_len,) = struct.unpack("<I", file.read(4))
                classifications[cls_name] = file.read(encoded_len)

            index[rule_name] = classifications

    return index