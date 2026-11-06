"""Launch a single loopback-only backend; never log keys or session tokens."""
import argparse
import json
import os
from pathlib import Path
import secrets
import socket
import sys
import threading
import uvicorn
from filelock import FileLock
from .api import create_app

def default_root():
    if sys.platform == 'darwin':
        return Path.home()/'Library'/'Application Support'/'TRIPODCode'
    return Path(os.environ.get('XDG_DATA_HOME', Path.home()/'.local/share'))/'tripodcode'

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--data-dir',type=Path,default=Path(os.environ.get('TRIPOD_DATA_DIR',default_root())))
    parser.add_argument('--port',type=int,default=0)
    parser.add_argument('--desktop',action='store_true')
    args=parser.parse_args()
    args.data_dir.mkdir(parents=True,exist_ok=True,mode=0o700)
    token=os.environ.pop('TRIPOD_SESSION_TOKEN',None) or secrets.token_urlsafe(48)
    with FileLock(str(args.data_dir/'workspace.lock'),timeout=0):
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as sock:
            sock.bind(('127.0.0.1',args.port)); sock.listen(128)
            port=sock.getsockname()[1]
            app=create_app(args.data_dir,token)
            server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,access_log=False,log_level='warning'))
            session=args.data_dir/'session.json'
            descriptor=os.open(session,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
            with os.fdopen(descriptor,'w') as stream: json.dump({'port':port,'token':token},stream)
            if args.desktop:
                def listen():
                    for line in sys.stdin:
                        if line.strip()=='shutdown':
                            server.should_exit=True
                            return
                    server.should_exit=True
                threading.Thread(target=listen,daemon=True).start()
            print(json.dumps({'port':port,'event':'listening'}),flush=True)
            try: server.run(sockets=[sock])
            finally: session.unlink(missing_ok=True)
if __name__=='__main__': main()
