from flask import Flask, redirect
import logging
import socket

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("redirector")

app = Flask(__name__)

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    # Determine Hostname or IP to redirect to
    # Ideally use the Host header from the request to preserve "silvasonic.local" vs IP
    from flask import request
    host = request.headers.get('Host', '').split(':')[0]
    if not host:
        host = get_ip()
    
    target = f"http://{host}:8080/{path}"
    logger.info(f"Redirecting to {target}")
    return redirect(target, code=302)

if __name__ == '__main__':
    # Run on Port 80
    app.run(host='0.0.0.0', port=80, debug=False)
