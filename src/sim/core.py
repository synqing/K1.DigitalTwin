import os
import threading
import time

class TwinEngine:
    def __init__(self, assets_dir="00_Engineering_Source"):
        self.assets_dir = assets_dir
        self.tick_count = 0
        self.assets_count = 0
        self._lock = threading.Lock()
        self._running = False

    def load_assets(self):
        if not os.path.isdir(self.assets_dir):
            self.assets_count = 0
            return
        try:
            self.assets_count = len([f for f in os.listdir(self.assets_dir) if not f.startswith(".")])
        except Exception:
            self.assets_count = 0

    def state(self):
        with self._lock:
            return {"tick": self.tick_count, "assets": self.assets_count}

    def tick(self):
        with self._lock:
            self.tick_count += 1

    def run(self, interval=0.5):
        self._running = True
        while self._running:
            self.tick()
            time.sleep(interval)

    def stop(self):
        self._running = False
