import os
import time
import urllib.request
for attempt in range(100):
    try:
        request=urllib.request.Request('http://127.0.0.1:8765/api/health',
            headers={'Authorization':'Bearer '+os.environ['TRIPOD_SESSION_TOKEN']})
        with urllib.request.urlopen(request,timeout=1) as response:
            if response.status==200:break
    except OSError:time.sleep(.1)
else:raise SystemExit('Backend did not become ready')
