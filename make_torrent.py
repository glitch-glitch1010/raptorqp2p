import os
import hashlib
import bencodepy
import argparse

def make_torrent(file, announce, piece_length, output):
    size = os.path.getsize(file)
    pieces = b''
    with open(file, 'rb') as f:
        while True:
            chunk = f.read(piece_length)
            if not chunk:
                break
            pieces += hashlib.sha1(chunk).digest()
    info = {
        b'name': file.encode(),
        b'piece length': piece_length,
        b'length': size,
        b'pieces': pieces
    }
    meta = {
        b'announce': announce.encode(),
        b'info': info
    }
    with open(output, 'wb') as out:
        out.write(bencodepy.encode(meta))
    print(f"Created torrent: {output}")

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('file')
    p.add_argument('-a', '--announce', default='http://localhost:8000/announce')
    p.add_argument('-l', '--piece-length', type=int, default=2**20)
    p.add_argument('-o', '--output', default='out.torrent')
    args = p.parse_args()
    make_torrent(args.file, args.announce, args.piece_length, args.output)