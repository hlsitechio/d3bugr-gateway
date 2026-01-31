from flask import Flask, jsonify
import json
import os

app = Flask(__name__)

# ==================== LOAD EMBEDDED DOCS ====================

def load_docs():
    """Load all documentation from embedded JSON files"""
    docs_dir = os.path.join(os.path.dirname(__file__), 'docs')
    docs = {}
    for filename in os.listdir(docs_dir):
        if filename.endswith('.json'):
            with open(os.path.join(docs_dir, filename), 'r') as f:
                docs[filename.replace('.json', '')] = json.load(f)
    return docs

DOCS = load_docs()

# ==================== DOCUMENTATION ENDPOINTS ====================

@app.route('/', methods=['GET'])
def index():
    """Full documentation"""
    return jsonify({
        "meta": DOCS.get('meta', {}),
        "services": {k: v for k, v in DOCS.items() if k != 'meta'}
    })

@app.route('/meta', methods=['GET'])
def meta():
    """Meta info and LLM context"""
    return jsonify(DOCS.get('meta', {}))

@app.route('/context', methods=['GET'])
def context():
    """LLM context - what/why/when"""
    m = DOCS.get('meta', {})
    return jsonify({
        "llm_context": m.get('llm_context', {}),
        "workflow": m.get('workflow', {}),
        "gateway_usage": m.get('gateway_usage', {})
    })

@app.route('/workflow', methods=['GET'])
def workflow():
    """Hunting workflow phases"""
    return jsonify(DOCS.get('meta', {}).get('workflow', {}))

@app.route('/services', methods=['GET'])
def list_services():
    """List services with metadata"""
    services = {}
    for key, doc in DOCS.items():
        if 'service' in doc:
            services[doc['service']] = {
                "name": doc.get('name', ''),
                "category": doc.get('category', ''),
                "description": doc.get('description', ''),
                "endpoints": [ep.get('path') for ep in doc.get('endpoints', [])]
            }
    return jsonify(services)

@app.route('/services/<service>', methods=['GET'])
def service_detail(service):
    """Full documentation for a service"""
    for doc in DOCS.values():
        if doc.get('service') == service:
            return jsonify(doc)
    return jsonify({'error': f'{service} not found'}), 404

@app.route('/endpoints', methods=['GET'])
def all_endpoints():
    """All endpoints across services"""
    eps = []
    for doc in DOCS.values():
        if 'service' in doc:
            for ep in doc.get('endpoints', []):
                eps.append({
                    "service": doc['service'],
                    "method": ep.get('method', 'GET'),
                    "path": ep.get('path', ''),
                    "description": ep.get('description', '')
                })
    return jsonify(eps)

@app.route('/mcp', methods=['GET'])
def mcp():
    """MCP tool mappings"""
    tools = {}
    for doc in DOCS.values():
        if 'service' in doc and 'mcp_tools' in doc:
            tools[doc['service']] = doc['mcp_tools']
    return jsonify({
        "prefix": "mcp__d3bugr__",
        "by_service": tools,
        "all": [t for ts in tools.values() for t in ts]
    })

@app.route('/examples', methods=['GET'])
def examples():
    """Usage examples"""
    exs = []
    for doc in DOCS.values():
        if 'service' in doc:
            for ex in doc.get('examples', []):
                ex['service'] = doc['service']
                exs.append(ex)
    return jsonify(exs)

@app.route('/categories', methods=['GET'])
def categories():
    """Services by category"""
    cats = {}
    for doc in DOCS.values():
        if 'service' in doc:
            cat = doc.get('category', 'other')
            if cat not in cats:
                cats[cat] = []
            cats[cat].append(doc['service'])
    return jsonify(cats)

@app.route('/llm/full', methods=['GET'])
def llm_full():
    """Complete docs for LLM context"""
    return jsonify(DOCS)

@app.route('/llm/compact', methods=['GET'])
def llm_compact():
    """Compact reference"""
    compact = {}
    for doc in DOCS.values():
        if 'service' in doc:
            compact[doc['service']] = [
                f"{ep.get('method', 'GET')} {ep.get('path', '')}"
                for ep in doc.get('endpoints', [])
            ]
    return jsonify(compact)

@app.route('/health', methods=['GET'])
def health():
    return 'ok'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
