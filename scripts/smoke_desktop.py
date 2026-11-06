"""Launch the built macOS bundle and verify native sidecar lifecycle."""
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
import time
import urllib.request

bundle = Path(sys.argv[1]).resolve()
info = plistlib.loads((bundle / 'Contents/Info.plist').read_bytes())
binary = bundle / 'Contents/MacOS' / info['CFBundleExecutable']
with tempfile.TemporaryDirectory(prefix='tripod-native-') as root:
    child = subprocess.Popen([str(binary)], env={**os.environ, 'TRIPOD_DATA_DIR': root})
    session = Path(root) / 'session.json'
    try:
        for _ in range(600):
            if child.poll() is not None:
                raise AssertionError('Desktop exited before backend readiness')
            if session.exists():
                try:
                    connection = json.loads(session.read_text())
                    request = urllib.request.Request(
                        f"http://127.0.0.1:{connection['port']}/api/health",
                        headers={'Authorization': 'Bearer ' + connection['token']})
                    with urllib.request.urlopen(request, timeout=1) as response:
                        assert json.load(response)['ready']
                    break
                except (OSError, ValueError):
                    pass
            time.sleep(.1)
        else:
            raise AssertionError('Desktop backend readiness timed out')
        # AppleScript quit exercises the native application exit callback.
        subprocess.run(['osascript', '-e', 'tell application id "org.tripodcode.workspace" to quit'],
                       check=True, timeout=15)
        assert child.wait(timeout=15) == 0
        assert not session.exists(), 'Backend session survived desktop shutdown'
        print('Native app launch, bundled backend readiness and shutdown passed')
    finally:
        if child.poll() is None:
            child.terminate()
            try: child.wait(timeout=5)
            except subprocess.TimeoutExpired: child.kill(); child.wait()
