from flask import Flask, jsonify, request
import requests
import os

app = Flask(__name__)

# Service registry - all Railway services
SERVICES = {
    # Recon
    "nmap": "https://nmap-production.up.railway.app",
    "argus-recon": "https://argus-recon-production.up.railway.app",
    "dns-tools": "https://dns-tools-api-production.up.railway.app",
    "theharvester": "https://theharvester-production.up.railway.app",
    # Scanning
    "nuclei": "https://nuclei-production-d931.up.railway.app",
    "sqlmap": "https://sqlmap-api-production.up.railway.app",
    "bhp": "https://bhp-api-production.up.railway.app",
    # OSINT
    "shodan": "https://divine-trust-production.up.railway.app",
}

# Full documentation
DOCS = {
    "meta": {
        "name": "Railway D3buGr API Gateway",
        "description": "Unified API to call all bug bounty tools",
        "version": "1.0.0",
        "gateway_endpoint": "/call/{service}/{endpoint}"
    },
    "context": {
        "what": "Cloud-based bug bounty hunting toolkit deployed on Railway. Security scanning, reconnaissance, and exploitation tools as HTTP APIs.",
        "why": [
            "Offload heavy scans - nmap, nuclei, sqlmap run on Railway servers",
            "Avoid detection - Scans originate from Railway IPs",
            "Parallel execution - Multiple scans simultaneously",
            "Persistence - Services run 24/7",
            "MCP Integration - Tools exposed via MCP for Claude Code / AI agents"
        ],
        "when": [
            "Bug bounty hunting - Authorized security testing",
            "Penetration testing - With written permission",
            "CTF competitions - Capture the flag challenges",
            "Security research - Vulnerability research on owned systems"
        ],
        "workflow": [
            "1. RECON: theharvester, dns-tools, argus-recon, nmap",
            "2. SCANNING: nuclei, sqlmap, bhp",
            "3. EXPLOITATION: D3buGr (MCP only)",
            "4. INTELLIGENCE: shodan"
        ]
    },
    "services": {
        "nmap": {
            "url": SERVICES["nmap"],
            "description": "Port scanning and service detection",
            "endpoints": [
                {"path": "/scan", "method": "POST", "params": {"target": "required", "args": "optional"}},
                {"path": "/quick", "method": "POST", "params": {"target": "required"}},
                {"path": "/version", "method": "GET"},
                {"path": "/health", "method": "GET"}
            ],
            "examples": [
                {"desc": "Full scan", "call": "/call/nmap/scan", "body": {"target": "example.com", "args": "-sV -p22,80,443"}},
                {"desc": "Quick scan", "call": "/call/nmap/quick", "body": {"target": "example.com"}}
            ]
        },
        "nuclei": {
            "url": SERVICES["nuclei"],
            "description": "Template-based vulnerability scanner",
            "endpoints": [
                {"path": "/scan", "method": "POST", "params": {"target": "required", "templates": "optional", "severity": "optional"}},
                {"path": "/quick", "method": "POST", "params": {"target": "required"}},
                {"path": "/cves", "method": "POST", "params": {"target": "required", "year": "optional"}},
                {"path": "/tech", "method": "POST", "params": {"target": "required"}},
                {"path": "/templates", "method": "GET"},
                {"path": "/health", "method": "GET"}
            ],
            "examples": [
                {"desc": "Quick vuln scan", "call": "/call/nuclei/quick", "body": {"target": "https://example.com"}},
                {"desc": "CVE scan", "call": "/call/nuclei/cves", "body": {"target": "https://example.com", "year": "2024"}}
            ]
        },
        "sqlmap": {
            "url": SERVICES["sqlmap"],
            "description": "SQL injection testing",
            "endpoints": [
                {"path": "/scan", "method": "POST", "params": {"url": "required", "level": "optional", "risk": "optional"}},
                {"path": "/quick", "method": "POST", "params": {"url": "required"}},
                {"path": "/status/{task_id}", "method": "GET"},
                {"path": "/result/{task_id}", "method": "GET"},
                {"path": "/health", "method": "GET"}
            ],
            "examples": [
                {"desc": "SQLi test", "call": "/call/sqlmap/quick", "body": {"url": "https://example.com/page?id=1"}}
            ]
        },
        "bhp": {
            "url": SERVICES["bhp"],
            "description": "XSS, SSRF, IDOR, encoding, payloads",
            "endpoints": [
                {"path": "/sqli/scan", "method": "POST", "params": {"url": "required"}},
                {"path": "/ssrf/scan", "method": "POST", "params": {"url": "required", "callback": "optional"}},
                {"path": "/takeover", "method": "POST", "params": {"domain": "required"}},
                {"path": "/dirbust", "method": "POST", "params": {"url": "required"}},
                {"path": "/idor", "method": "POST", "params": {"url": "required"}},
                {"path": "/payload/shell", "method": "POST", "params": {"ip": "required", "port": "required", "type": "optional"}},
                {"path": "/payload/xss", "method": "POST", "params": {"type": "optional"}},
                {"path": "/encode", "method": "POST", "params": {"data": "required", "type": "optional"}},
                {"path": "/decode", "method": "POST", "params": {"data": "required", "type": "optional"}},
                {"path": "/health", "method": "GET"}
            ]
        },
        "dns-tools": {
            "url": SERVICES["dns-tools"],
            "description": "DNS enumeration and zone transfers",
            "endpoints": [
                {"path": "/lookup", "method": "POST", "params": {"domain": "required", "types": "optional"}},
                {"path": "/zone-transfer", "method": "POST", "params": {"domain": "required"}},
                {"path": "/reverse", "method": "POST", "params": {"ip": "required"}},
                {"path": "/mx", "method": "POST", "params": {"domain": "required"}},
                {"path": "/dnssec", "method": "POST", "params": {"domain": "required"}},
                {"path": "/health", "method": "GET"}
            ]
        },
        "theharvester": {
            "url": SERVICES["theharvester"],
            "description": "Email and subdomain harvesting",
            "endpoints": [
                {"path": "/harvest", "method": "POST", "params": {"domain": "required", "source": "optional", "limit": "optional"}},
                {"path": "/emails", "method": "POST", "params": {"domain": "required"}},
                {"path": "/subdomains", "method": "POST", "params": {"domain": "required"}},
                {"path": "/sources", "method": "GET"},
                {"path": "/health", "method": "GET"}
            ]
        },
        "argus-recon": {
            "url": SERVICES["argus-recon"],
            "description": "Asset discovery and enumeration",
            "endpoints": [
                {"path": "/recon", "method": "POST", "params": {"target": "required", "depth": "optional"}},
                {"path": "/subdomains", "method": "POST", "params": {"target": "required"}},
                {"path": "/ports", "method": "POST", "params": {"target": "required"}},
                {"path": "/health", "method": "GET"}
            ]
        },
        "shodan": {
            "url": SERVICES["shodan"],
            "description": "Shodan + CVE database",
            "endpoints": [
                {"path": "/shodan/host/{ip}", "method": "GET"},
                {"path": "/shodan/search", "method": "POST", "params": {"query": "required"}},
                {"path": "/shodan/dns", "method": "POST", "params": {"domain": "required"}},
                {"path": "/shodan/honeypot/{ip}", "method": "GET"},
                {"path": "/cve/{cve_id}", "method": "GET"},
                {"path": "/cve/search", "method": "POST", "params": {"product": "optional"}},
                {"path": "/cve/recent", "method": "GET"},
                {"path": "/cve/kev", "method": "GET"},
                {"path": "/health", "method": "GET"}
            ]
        }
    },
    "mcp_integration": {
        "prefix": "mcp__d3bugr__",
        "examples": [
            "mcp__d3bugr__nmap_scan(target, args)",
            "mcp__d3bugr__nuclei_quick(target)",
            "mcp__d3bugr__sqlmap_test(url)",
            "mcp__d3bugr__hunt_jwts()",
            "mcp__d3bugr__full_recon()"
        ]
    }
}

# ==================== DOCUMENTATION ENDPOINTS ====================

@app.route('/', methods=['GET'])
def index():
    """Main docs - returns full documentation"""
    return jsonify(DOCS)

@app.route('/docs', methods=['GET'])
def docs():
    """Alias for main docs"""
    return jsonify(DOCS)

@app.route('/context', methods=['GET'])
def context():
    """LLM context - what/why/when/how"""
    return jsonify(DOCS['context'])

@app.route('/services', methods=['GET'])
def list_services():
    """List all available services"""
    return jsonify({name: {"url": svc["url"], "description": svc["description"]}
                    for name, svc in DOCS['services'].items()})

@app.route('/services/<service>', methods=['GET'])
def service_detail(service):
    """Get specific service documentation"""
    if service in DOCS['services']:
        return jsonify(DOCS['services'][service])
    return jsonify({'error': f'Service {service} not found', 'available': list(DOCS['services'].keys())}), 404

@app.route('/mcp', methods=['GET'])
def mcp():
    """MCP integration info"""
    return jsonify(DOCS['mcp_integration'])

@app.route('/workflow', methods=['GET'])
def workflow():
    """Typical workflow"""
    return jsonify({"workflow": DOCS['context']['workflow']})

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
    """Check status of all services"""
    results = {}
    for name, url in SERVICES.items():
        try:
            resp = requests.get(f"{url}/health", timeout=5)
            results[name] = {"status": "online" if resp.status_code == 200 else "error", "url": url}
        except:
            results[name] = {"status": "offline", "url": url}
    return jsonify(results)

@app.route('/health', methods=['GET'])
def health():
    return 'ok'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
