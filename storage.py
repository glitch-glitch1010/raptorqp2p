import os
import hashlib
from protocol import bdecode, bencode

class TorrentMeta:
    def __init__(self, torrent_file: str):
        data = bdecode(open(torrent_file, "rb").read())
        info = bencode(data[b"info"])
        self.info_hash = hashlib.sha1(info).digest()
        self.name = data[b"info"][b"name"].decode()
        self.plen = data[b"info"][b"piece length"]
        self.length = data[b"info"][b"length"]


def write_block(download_dir: str, block_id: int, data: bytes):
    os.makedirs(download_dir, exist_ok=True)
    with open(f"{download_dir}/block_{block_id}.blk", "wb") as f:
        f.write(data)