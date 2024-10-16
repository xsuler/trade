# storage/storage.py

import json
import os
import logging
from typing import Dict
from config.config import PORTFOLIO_FILE

class Storage:
    def __init__(self, filepath: str = PORTFOLIO_FILE):
        self.filepath = filepath
        self.data = self.load()

    def load(self) -> Dict:
        if os.path.exists(self.filepath):
            with open(self.filepath, 'r') as f:
                try:
                    data = json.load(f)
                    return data
                except json.JSONDecodeError:
                    logging.warning("持仓文件格式错误，初始化新的持仓。")
                    return {}
        else:
            logging.info("持仓文件不存在，初始化新的持仓。")
            return {}

    def save(self, data: Dict):
        with open(self.filepath, 'w') as f:
            json.dump(data, f, indent=4)