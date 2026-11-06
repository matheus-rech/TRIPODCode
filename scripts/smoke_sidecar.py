"""Black-box sidecar startup, authenticated demo, persistence and shutdown smoke test."""
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
import time
import urllib.request
def main():
 parser=argparse.ArgumentParser();parser.add_argument('binary');args=parser.parse_args()
 with tempfile.TemporaryDirectory() as directory:
  token=secrets.token_hex(32)
  def launch():
   child=subprocess.Popen([args.binary,'--desktop','--data-dir',directory],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
       stderr=subprocess.PIPE,text=True,env={**os.environ,'TRIPOD_SESSION_TOKEN':token})
   session=Path(directory)/'session.json'
   for _ in range(200):
    if child.poll() is not None:raise AssertionError('Backend exited before readiness')
    if session.exists():
     try:port=json.loads(session.read_text())['port'];return child,port
     except (ValueError,KeyError):pass
    time.sleep(.1)
   child.kill();raise AssertionError('Readiness timeout')
  child,port=launch()
  def request(path,body=None):
   data=None if body is None else json.dumps(body).encode()
   req=urllib.request.Request(f'http://127.0.0.1:{port}/api'+path,data=data,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
   return json.load(urllib.request.urlopen(req,timeout=5))
  try:
   for _ in range(100):
    try:request('/health');break
    except OSError:time.sleep(.1)
   dataset=request('/datasets/demo',{})
   job=request('/jobs',{'dataset_id':dataset['id']})
   for _ in range(200):
    state=request('/jobs/'+job['id'])
    if state['state'] not in ('queued','running'):break
    time.sleep(.05)
   assert state['state']=='incomplete' and state['progress']==6
   assert len(request('/jobs/'+job['id']+'/export')['results'])==6
   child.communicate('shutdown\n',timeout=10);assert child.returncode==0
   child,port=launch()
   for _ in range(100):
    try:request('/health');break
    except OSError:time.sleep(.1)
   assert request('/jobs/'+job['id'])['progress']==6
   child.communicate('shutdown\n',timeout=10);assert child.returncode==0
   print('Sidecar startup, demo, export, persistence and shutdown passed')
  finally:
   if child.poll() is None:child.kill();child.wait()
if __name__=='__main__':main()
