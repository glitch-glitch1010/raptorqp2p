from flask import Flask, request, Response
import bencodepy

app = Flask(__name__)
swarms = {}

@app.route('/announce')
def announce():
    ih = request.args.get('info_hash').encode('latin-1')
    port = int(request.args.get('port'))
    peer = (request.remote_addr, port)
    swarms.setdefault(ih, set()).add(peer)
    peers = b''
    for ip, p in swarms[ih]:
        octs = [int(x).to_bytes(1, 'big') for x in ip.split('.')]
        peers += b''.join(octs) + p.to_bytes(2, 'big')
    resp = {b'interval': 120, b'peers': peers}
    return Response(bencodepy.encode(resp), mimetype='text/plain')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)