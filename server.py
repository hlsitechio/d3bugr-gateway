from flask import Flask, jsonify, request
import requests
import json
import os

app = Flask(__name__)

# ==================== LOAD EMBEDDED DOCS ====================
# All docs loaded from JSON at startup - no external network calls

def load_docs():
    """Load all documentation from embedded JSON files"""
    docs_dir = os.path.join(os.path.dirname(__file__), 'docs')
    docs = {}

    for filename in os.listdir(docs_dir):
        if filename.endswith('.json'):
            filepath = os.path.join(docs_dir, filename)
            with open(filepath, 'r') as f:
                key = filename.replace('.json', '')
                docs[key] = json.load(f)

    return docs

DOCS = load_docs()

# Service registry - extracted from docs
SERVICES = {
    doc['service']: doc['url']
    for doc in DOCS.values()
    if 'service' in doc and 'url' in doc
}

# ==================== DOCUMENTATION ENDPOINTS ====================

@app.route('/', methods=['GET'])
def index():
    """Full documentation - all services, meta, and context"""
    return jsonify({
        "meta": DOCS.get('meta', {}),
        "services": {k: v for k, v in DOCS.items() if k != 'meta'},
        "service_urls": SERVICES
    })

@app.route('/docs', methods=['GET'])
def docs():
    """Alias for full docs"""
    return index()

@app.route('/meta', methods=['GET'])
def meta():
    """Meta information and LLM context"""
    return jsonify(DOCS.get('meta', {}))

@app.route('/context', methods=['GET'])
def context():
    """LLM context - what/why/when/workflow"""
    meta = DOCS.get('meta', {})
    return jsonify({
        "llm_context": meta.get('llm_context', {}),
        "workflow": meta.get('workflow', {}),
        "gateway_usage": meta.get('gateway_usage', {})
    })

@app.route('/workflow', methods=['GET'])
def workflow():
    """Hunting workflow phases"""
    meta = DOCS.get('meta', {})
    return jsonify(meta.get('workflow', {}))

@app.route('/services', methods=['GET'])
def list_services():
    """List all available services with URLs and descriptions"""
    services = {}
    for key, doc in DOCS.items():
        if 'service' in doc:
            services[doc['service']] = {
                "name": doc.get('name', ''),
                "url": doc.get('url', ''),
                "category": doc.get('category', ''),
                "description": doc.get('description', ''),
                "endpoints_count": len(doc.get('endpoints', []))
            }
    return jsonify(services)

@app.route('/services/<service>', methods=['GET'])
def service_detail(service):
    """Get complete documentation for a specific service"""
    for key, doc in DOCS.items():
        if doc.get('service') == service:
            return jsonify(doc)
    return jsonify({
        'error': f'Service {service} not found',
        'available': list(SERVICES.keys())
    }), 404

@app.route('/endpoints', methods=['GET'])
def all_endpoints():
    """List all endpoints across all services"""
    endpoints = []
    for key, doc in DOCS.items():
        if 'service' in doc and 'endpoints' in doc:
            for ep in doc['endpoints']:
                endpoints.append({
                    "service": doc['service'],
                    "path": ep.get('path', ''),
                    "method": ep.get('method', ''),
                    "description": ep.get('description', ''),
                    "gateway_path": f"/call/{doc['service']}/{ep.get('path', '').lstrip('/')}"
                })
    return jsonify(endpoints)

@app.route('/mcp', methods=['GET'])
def mcp():
    """MCP tool mappings for all services"""
    mcp_tools = {}
    for key, doc in DOCS.items():
        if 'service' in doc and 'mcp_tools' in doc:
            mcp_tools[doc['service']] = doc['mcp_tools']
    return jsonify({
        "prefix": "mcp__d3bugr__",
        "tools_by_service": mcp_tools,
        "all_tools": [tool for tools in mcp_tools.values() for tool in tools]
    })

@app.route('/examples', methods=['GET'])
def examples():
    """All usage examples across services"""
    all_examples = []
    for key, doc in DOCS.items():
        if 'service' in doc and 'examples' in doc:
            for ex in doc['examples']:
                ex['service'] = doc['service']
                all_examples.append(ex)
    return jsonify(all_examples)

@app.route('/categories', methods=['GET'])
def categories():
    """Services grouped by category"""
    cats = {}
    for key, doc in DOCS.items():
        if 'service' in doc:
            cat = doc.get('category', 'other')
            if cat not in cats:
                cats[cat] = []
            cats[cat].append({
                "service": doc['service'],
                "name": doc.get('name', ''),
                "description": doc.get('description', '')
            })
    return jsonify(cats)

# ==================== GATEWAY ENDPOINTS ====================

@app.route('/call/<service>/<path:endpoint>', methods=['GET', 'POST'])
def call_service(service, endpoint):
    """
    Gateway to call any service endpoint

    Usage:
        POST /call/nmap/scan         -> calls nmap /scan
        POST /call/nuclei/quick      -> calls nuclei /quick
        GET  /call/shodan/cve/CVE-2024-1234 -> calls shodan /cve/CVE-2024-1234
    """
    if service not in SERVICES:
        return jsonify({
            'error': f'Service {service} not found',
            'available': list(SERVICES.keys())
        }), 404

    base_url = SERVICES[service]
    target_url = f"{base_url}/{endpoint}"

    try:
        if request.method == 'POST':
            data = request.json or {}
            resp = requests.post(target_url, json=data, timeout=600)
        else:
            resp = requests.get(target_url, params=request.args, timeout=60)

        # Try to return JSON, fallback to text
        try:
            return jsonify(resp.json()), resp.status_code
        except:
            return resp.text, resp.status_code

    except requests.Timeout:
        return jsonify({'error': 'Service timeout', 'service': service, 'endpoint': endpoint}), 504
    except requests.ConnectionError:
        return jsonify({'error': 'Service unavailable', 'service': service, 'endpoint': endpoint}), 503
    except Exception as e:
        return jsonify({'error': str(e), 'service': service, 'endpoint': endpoint}), 500

@app.route('/status', methods=['GET'])
def status():
    """Check health status of all services"""
    results = {}
    for name, url in SERVICES.items():
        try:
            resp = requests.get(f"{url}/health", timeout=5)
            results[name] = {
                "status": "online" if resp.status_code == 200 else "error",
                "url": url
            }
        except:
            results[name] = {"status": "offline", "url": url}
    return jsonify(results)

@app.route('/health', methods=['GET'])
def health():
    return 'ok'

# ==================== LLM-OPTIMIZED ENDPOINTS ====================

@app.route('/llm/full', methods=['GET'])
def llm_full():
    """Complete documentation dump optimized for LLM context loading"""
    return jsonify({
        "meta": DOCS.get('meta', {}),
        "services": {k: v for k, v in DOCS.items() if k != 'meta'},
        "quick_reference": {
            "gateway_pattern": "POST /call/{service}/{endpoint}",
            "available_services": list(SERVICES.keys()),
            "status_check": "GET /status",
            "service_docs": "GET /services/{service}"
        }
    })

@app.route('/llm/compact', methods=['GET'])
def llm_compact():
    """Compact reference for token-limited contexts"""
    compact = {
        "gateway": "/call/{service}/{endpoint}",
        "services": {}
    }
    for key, doc in DOCS.items():
        if 'service' in doc:
            compact["services"][doc['service']] = {
                "url": doc.get('url', ''),
                "endpoints": [
                    f"{ep.get('method', 'GET')} {ep.get('path', '')}"
                    for ep in doc.get('endpoints', [])
                ]
            }
    return jsonify(compact)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
