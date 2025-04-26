import struct
import bencodepy

# ——— BitTorrent handshake & messages ———
BT = b"BitTorrent protocol"

def make_handshake(info_hash: bytes, peer_id: bytes) -> bytes:
    return (
        struct.pack(">B", len(BT)) +
        BT +
        b"\x00" * 8 +
        info_hash +
        peer_id
    )

def parse_handshake(data: bytes):
    p = data[0]
    assert data[1:1+p] == BT
    return {
        "info_hash": data[1+p+8:1+p+8+20],
        "peer_id": data[-20:]
    }


def pack_message(msg_id: int, payload: bytes = b"") -> bytes:
    length = 1 + len(payload)
    return (
        struct.pack(">I", length) +
        struct.pack(">B", msg_id) +
        payload
    )


def unpack_message(sock):
    header = sock.recv(4)
    if not header:
        return None
    length = struct.unpack(">I", header)[0]
    if length == 0:
        return {"id": None, "payload": b""}
    body = sock.recv(length)
    return {"id": body[0], "payload": body[1:]}

# standard messages
msg_choke       = lambda: pack_message(0)
msg_unchoke     = lambda: pack_message(1)
msg_interested  = lambda: pack_message(2)
msg_not_interested = lambda: pack_message(3)
msg_have        = lambda idx: pack_message(4, struct.pack(">I", idx))
msg_bitfield    = lambda bf: pack_message(5, bf)
msg_request     = lambda idx, b, l: pack_message(6, struct.pack(">III", idx, b, l))
msg_piece       = lambda idx, b, blk: pack_message(7, struct.pack(">II", idx, b) + blk)

# extended: symbol carries full block or symbol data
msg_symbol      = lambda bid, sid, data: pack_message(7, struct.pack(">II", bid, sid) + data)
unpack_symbol   = lambda p: (struct.unpack(">II", p[:8]) + (p[8:],))

# bencode helpers
bencode = bencodepy.encode
bdecode = bencodepy.decode