import os
from dataclasses import dataclass
from dotenv import load_dotenv
load_dotenv()


@dataclass
class Env:
    local_path: str
    log_level: str
    verbose: bool
    chunk_size: int
    process_pages_limit: int

    def __init__(self):
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.local_path = os.getenv("LOCAL_PATH", "./")
        self.verbose = self.log_level == "DEBUG"
        self.chunk_size = int(os.getenv("CHUNK_SIZE", "2000"))
        self.process_pages_limit = int(os.getenv("PROCESS_PAGES_LIMIT", "20"))


env = Env()
