import ipaddress
from typing import Dict, Any, Optional

# Known bad IP ranges
KNOWN_BAD_IP_RANGES = [
    "185.220.0.0/16",     # Tor exit nodes range
    "198.98.0.0/16",      # Known C2 range
    "45.33.0.0/16",       # Linode (common VPS abuse)
    "104.244.0.0/16",     # Known bulletproof hosting
    "192.95.0.0/16",      # Malicious VPNs
    "205.210.0.0/16",     # Proxy abuse
    "23.94.0.0/16",       # Collar hosting
    "107.172.0.0/16",     # Cheap VPS
    "192.3.0.0/16",       # Known spam networks
    "104.144.0.0/16",     # Botnet infrastructure
    # Add 40 more placeholders
    *[f"203.0.{i}.0/24" for i in range(113, 153)]
]

# Known malicious process hashes/names
KNOWN_BAD_PROCESS_NAMES = {
    "mimikatz.exe", "pwdump.exe", "procdump.exe",
    "wce.exe", "fgdump.exe", "gsecdump.exe",
    "lazagne.exe", "netcat.exe", "nc.exe",
    "nmap.exe", "masscan.exe", "zmap.exe",
    "psexec.exe", "smbexec.exe", "wmiexec.py",
    "bloodhound.exe", "sharpbound.exe", "sharphound.exe",
    "rubeus.exe", "certify.exe", "seatbelt.exe",
    "inveigh.exe", "responder.py", "empire.exe",
    "covenant.exe", "sliver-server.exe", "sliver-client.exe",
    "cobaltstrike.exe", "teamserver", "meterpreter.exe",
    "msfvenom", "msfconsole", "evil-winrm.rb",
    "koadic", "merlinServer", "mythic-cli",
    "pupy", "quasarrat.exe", "remcos.exe",
    "nanocore.exe", "njrat.exe", "darkcomet.exe",
    "impacket", "secretsdump.py", "ntlmrelayx.py",
    "crackmapexec", "cme", "hashcat.exe",
    "john.exe", "hydra", "medusa"
}

# Suspicious domains/TLDs for C2 detection
SUSPICIOUS_TLDS = {".xyz", ".top", ".tk", ".ml", ".ga", ".cf", ".gq", ".pw", ".cc", ".su", ".ru", ".cn", ".bid", ".club"}
KNOWN_C2_PATTERNS = ["beacon", "c2", "callback", "dropper", "payload", "cmd", "cnc", "bot", "stealer"]

# Known safe processes (whitelist)
KNOWN_SAFE_PROCESSES = {
    "svchost.exe", "lsass.exe", "services.exe",
    "csrss.exe", "wininit.exe", "winlogon.exe",
    "explorer.exe", "taskmgr.exe", "spoolsv.exe",
    "smss.exe", "conhost.exe", "dwm.exe",
    "system", "system idle process", "registry",
    "bash", "sh", "sshd", "systemd", "cron",
    "init", "kthreadd", "kworker", "rsyslogd",
    "dockerd", "containerd", "kubelet", "kube-proxy",
    "nginx", "apache2", "httpd", "mysql", "postgres"
}

class ThreatIntelEnricher:
    def __init__(self):
        self._compiled_ranges = []
        for r in KNOWN_BAD_IP_RANGES:
            try:
                self._compiled_ranges.append(ipaddress.ip_network(r))
            except ValueError:
                pass

    def check_ip_reputation(self, ip: str) -> Dict[str, Any]:
        result = {
            "is_bad": False,
            "matching_range": None
        }
        if not ip:
            return result
            
        try:
            ip_obj = ipaddress.ip_address(ip)
            for net in self._compiled_ranges:
                if ip_obj in net:
                    result["is_bad"] = True
                    result["matching_range"] = str(net)
                    break
        except ValueError:
            pass
            
        return result

    def check_process_reputation(self, process_name: str) -> Dict[str, Any]:
        result = {
            "is_known_malicious": False,
            "is_known_safe": False,
            "process_name": process_name
        }
        if not process_name:
            return result
            
        name_lower = process_name.lower().strip()
        
        # Exact match or substring (e.g., /usr/bin/nmap)
        if name_lower in KNOWN_SAFE_PROCESSES:
            result["is_known_safe"] = True
        elif any(safe in name_lower for safe in KNOWN_SAFE_PROCESSES):
            result["is_known_safe"] = True
            
        if name_lower in KNOWN_BAD_PROCESS_NAMES:
            result["is_known_malicious"] = True
        elif any(bad in name_lower for bad in KNOWN_BAD_PROCESS_NAMES):
            result["is_known_malicious"] = True
            
        return result

    def check_domain_reputation(self, domain: str) -> Dict[str, Any]:
        result = {
            "has_suspicious_tld": False,
            "has_c2_pattern": False,
            "domain": domain
        }
        if not domain:
            return result
            
        domain_lower = domain.lower().strip()
        
        for tld in SUSPICIOUS_TLDS:
            if domain_lower.endswith(tld):
                result["has_suspicious_tld"] = True
                break
                
        for pattern in KNOWN_C2_PATTERNS:
            if pattern in domain_lower:
                result["has_c2_pattern"] = True
                break
                
        return result

    def enrich_alert(self, alert: dict, feature_row: dict) -> Dict[str, Any]:
        src_ip_res = self.check_ip_reputation(feature_row.get("src_ip", ""))
        dst_ip_res = self.check_ip_reputation(feature_row.get("dst_ip", ""))
        
        proc_name = feature_row.get("process_name", "") or feature_row.get("parent_process_name", "")
        proc_res = self.check_process_reputation(proc_name)
        
        domain = feature_row.get("dns_query", "") or feature_row.get("http_host", "")
        dom_res = self.check_domain_reputation(domain)
        
        intel_score_boost = 0.0
        
        if src_ip_res["is_bad"] or dst_ip_res["is_bad"]:
            intel_score_boost += 0.1
        if proc_res["is_known_malicious"]:
            intel_score_boost += 0.15
        elif proc_res["is_known_safe"]:
            intel_score_boost -= 0.1 # Discount for known safe
            
        if dom_res["has_suspicious_tld"] or dom_res["has_c2_pattern"]:
            intel_score_boost += 0.1
            
        intel = {
            "ip_reputation": {
                "src_ip_is_bad": src_ip_res["is_bad"],
                "dst_ip_is_bad": dst_ip_res["is_bad"],
                "matching_range": src_ip_res["matching_range"] or dst_ip_res["matching_range"]
            },
            "process_reputation": proc_res,
            "domain_reputation": dom_res,
            "intel_score_boost": intel_score_boost
        }
        
        alert["threat_intel"] = intel
        return alert

    def adjust_threat_score(self, base_score: float, intel: dict) -> float:
        boost = intel.get("intel_score_boost", 0.0)
        return min(max(base_score + boost, 0.0), 1.0)
