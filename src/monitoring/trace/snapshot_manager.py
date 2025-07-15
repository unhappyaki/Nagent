import os
import json
from datetime import datetime

class SnapshotManager:
    def __init__(self, save_dir="snapshots"):
        self.save_dir = save_dir
        os.makedirs(save_dir, exist_ok=True)
        self.snapshots = {}  # {name: snapshot_data}

    def save_snapshot(self, name, data):
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        filename = f"{name}_{timestamp}.json"
        path = os.path.join(self.save_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self.snapshots[name] = data
        return path

    def load_snapshot(self, filename):
        path = os.path.join(self.save_dir, filename)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data

    def list_snapshots(self):
        return [f for f in os.listdir(self.save_dir) if f.endswith(".json")]

    def get_snapshot(self, name):
        return self.snapshots.get(name) 