# torrent_peer.py

import socket
import threading
import time
import random
import os
import logging

from protocol import (
    make_handshake, unpack_message,
    msg_interested, msg_have, msg_symbol, unpack_symbol,
    bdecode
)
from storage import TorrentMeta, write_block
from raptorqp2p import FileEncoder, FileDecoder, BlockDecoder, SymbolScheduler

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')


class Peer:
    def __init__(self, mode, torrent_file, download_dir, peer_id, tracker_url):
        self.mode = mode            # '--seed' or '--leech'
        self.meta = TorrentMeta(torrent_file)
        self.download_dir = download_dir
        self.peer_id = peer_id.encode('latin-1')
        self.tracker = tracker_url

        self.encoder = FileEncoder(torrent_file)
        self.decoder = FileDecoder(None)
        self.block_decoders = {}
        self.scheduler = {}

    def start(self):
        # 1) Start listening for incoming peer connections
        srv = socket.socket()
        srv.bind(('', 0))
        srv.listen(5)
        self.listen_port = srv.getsockname()[1]
        logging.info(f"Peer listening on {self.listen_port}")

        # 2) Announce to tracker and get peer list
        import requests
        params = {
            'info_hash': self.meta.info_hash.decode('latin-1'),
            'peer_id':   self.peer_id.decode('latin-1'),
            'port':      self.listen_port
        }
        r = requests.get(self.tracker + '/announce', params=params)
        resp = bdecode(r.content)
        peer_bytes = resp[b'peers']

        peers = []
        # peers payload is 6-byte entries: 4×IP + 2×port
        for i in range(0, len(peer_bytes), 6):
            ip = '.'.join(str(b) for b in peer_bytes[i:i+4])
            port = int.from_bytes(peer_bytes[i+4:i+6], 'big')
            # skip ourselves
            if port != self.listen_port:
                peers.append((ip, port))

        # 3) Outbound connect to each peer
        for ip, port in peers:
            try:
                sock = socket.socket()
                sock.connect((ip, port))
                logging.info(f"Connected to peer {ip}:{port}")
                self._setup_peer(sock)
            except Exception as e:
                logging.warning(f"Could not connect to {ip}:{port}: {e}")

        # 4) Accept any remaining incoming connections
        while True:
            conn, _ = srv.accept()
            self._setup_peer(conn)

    def _setup_peer(self, sock):
        # Perform handshake
        sock.send(make_handshake(self.meta.info_hash, self.peer_id))
        sock.recv(68)

        # Express interest
        sock.send(msg_interested())

        # Assign a scheduler slot for this connection
        self.scheduler[sock] = SymbolScheduler(8, len(self.scheduler))

        # Start reader & writer threads
        threading.Thread(target=self._reader, args=(sock,), daemon=True).start()
        threading.Thread(target=self._writer, args=(sock,), daemon=True).start()

    def _reader(self, sock):
        while True:
            m = unpack_message(sock)
            if not m:
                break
            if m['id'] == 7:  # symbol message
                bid, sid, data = unpack_symbol(m['payload'])
                # get or create the per-block decoder
                bd = self.block_decoders.setdefault(bid, BlockDecoder(None))
                bd.add_symbol(sid, data)
                # record that we’ve received this symbol
                self.scheduler[sock].update_received(bid, sid)
                if bd.complete:
                    blk = bd.decode()
                    write_block(self.download_dir, bid, blk)
                    self.decoder.add_block(bid, blk)
                    sock.send(msg_have(bid))
                    if self.decoder.complete:
                        # reassemble full file
                        full = self.decoder.decode()
                        os.makedirs(self.download_dir, exist_ok=True)
                        out_path = f"{self.download_dir}/{self.meta.name}"
                        with open(out_path, 'wb') as f:
                            f.write(full)
                        logging.info("File-level decode complete")
                        break

    def _writer(self, sock):
        if self.mode == '--seed':
            # Push every symbol of every block
            for bid in self.encoder.get_block_ids():
                syms = self.encoder.get_block_encoder(bid)
                for sid, dat in enumerate(syms):
                    sock.send(msg_symbol(bid, sid, dat))
                    # slight throttle
                    time.sleep(0.005)
        else:
            # Leecher does not push: wait for incoming symbols
            pass


if __name__ == '__main__':
    import sys

    if len(sys.argv) != 3 or sys.argv[1] not in ('--seed', '--leech'):
        print("Usage: python torrent_peer.py [--seed|--leech] <torrent_file>")
        sys.exit(1)

    mode = sys.argv[1]
    torrent = sys.argv[2]
    peer_id = '-' + str(random.randint(1000, 9999)) + '-P2P'
    tracker = 'http://localhost:8000'

    p = Peer(mode, torrent, 'downloads', peer_id, tracker)
    p.start()

    # keep main thread alive
    while True:
        time.sleep(1)
