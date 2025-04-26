class FileEncoder:
    def __init__(self, file_path, block_size=1_600_000, sym_size=16_000, repair_ratio=1.0):
        data = open(file_path, 'rb').read()
        # split file into S source blocks
        self.blocks = [data[i:i+block_size] for i in range(0, len(data), block_size)]
        self.S = len(self.blocks)
        self.R = int(self.S * repair_ratio)
        self.total_blocks = self.S + self.R
        self.sym_size = sym_size

    def get_block_ids(self):
        return list(range(self.total_blocks))

    def get_block(self, block_id):
        # repair blocks reuse source data modulo S
        return self.blocks[block_id % self.S]

    def get_block_encoder(self, block_id):
        blk = self.get_block(block_id)
        # split block into symbols of size sym_size
        syms = [blk[i:i+self.sym_size] for i in range(0, len(blk), self.sym_size)]
        return syms


class FileDecoder:
    def __init__(self, block_size=None):
        self.recv = {}

    def add_block(self, block_id, data):
        self.recv[block_id] = data

    @property
    def complete(self):
        if not self.recv:
            return False
        # complete when we have a contiguous set from 0 to max
        return len(self.recv) == max(self.recv.keys()) + 1

    def decode(self):
        return b"".join(self.recv[i] for i in sorted(self.recv))


class BlockDecoder:
    def __init__(self, sym_size=None):
        self.data = None

    def add_symbol(self, symbol_id, data):
        self.data = data

    @property
    def complete(self):
        return self.data is not None

    def decode(self):
        return self.data


class SymbolScheduler:
    def __init__(self, total_slots, slot_index):
        self.N = total_slots
        self.slot = slot_index
        self.max_symbol = {}

    def next_outgoing(self, block_id):
        ms = self.max_symbol.get(block_id, -1) + 1
        while ms % self.N != self.slot:
            ms += 1
        self.max_symbol[block_id] = ms
        return ms

    def update_received(self, block_id, symbol_id):
        self.max_symbol[block_id] = max(self.max_symbol.get(block_id, -1), symbol_id)