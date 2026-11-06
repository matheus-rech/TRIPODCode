"""PyInstaller entry point; configure the bundled tokenizer before imports."""
import os
from pathlib import Path
import sys
if getattr(sys,'frozen',False):
    os.environ['TIKTOKEN_CACHE_DIR']=str(Path(sys._MEIPASS)/'tiktoken_cache')
from backend.main import main
if __name__=='__main__': main()
