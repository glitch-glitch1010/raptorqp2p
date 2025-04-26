import threading, logging
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")

def run_in_thread(fn):
    t = threading.Thread(target=fn, daemon=True)
    t.start()
    return t
