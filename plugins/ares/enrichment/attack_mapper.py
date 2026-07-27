from __future__ import annotations

CWE_TO_ATTACK: dict[str, dict] = {
    "CWE-22":  {"technique": "T1190", "tactic": "initial-access", "name": "Exploit Public-Facing Application"},
    "CWE-78":  {"technique": "T1059", "tactic": "execution", "name": "Command and Scripting Interpreter"},
    "CWE-79":  {"technique": "T1059", "tactic": "execution", "name": "Command and Scripting Interpreter"},
    "CWE-89":  {"technique": "T1190", "tactic": "initial-access", "name": "Exploit Public-Facing Application"},
    "CWE-94":  {"technique": "T1059", "tactic": "execution", "name": "Command and Scripting Interpreter"},
    "CWE-119": {"technique": "T1203", "tactic": "execution", "name": "Exploitation for Client Execution"},
    "CWE-125": {"technique": "T1203", "tactic": "execution", "name": "Exploitation for Client Execution"},
    "CWE-190": {"technique": "T1203", "tactic": "execution", "name": "Exploitation for Client Execution"},
    "CWE-200": {"technique": "T1005", "tactic": "collection", "name": "Data from Local System"},
    "CWE-269": {"technique": "T1078", "tactic": "privilege-escalation", "name": "Valid Accounts"},
    "CWE-287": {"technique": "T1078", "tactic": "initial-access", "name": "Valid Accounts"},
    "CWE-306": {"technique": "T1078", "tactic": "initial-access", "name": "Valid Accounts"},
    "CWE-311": {"technique": "T1557", "tactic": "credential-access", "name": "Adversary-in-the-Middle"},
    "CWE-327": {"technique": "T1557", "tactic": "credential-access", "name": "Adversary-in-the-Middle"},
    "CWE-352": {"technique": "T1189", "tactic": "initial-access", "name": "Drive-by Compromise"},
    "CWE-434": {"technique": "T1203", "tactic": "execution", "name": "Exploitation for Client Execution"},
    "CWE-502": {"technique": "T1059", "tactic": "execution", "name": "Command and Scripting Interpreter"},
    "CWE-611": {"technique": "T1059", "tactic": "execution", "name": "Command and Scripting Interpreter"},
    "CWE-682": {"technique": "T1068", "tactic": "privilege-escalation", "name": "Exploitation for Privilege Escalation"},
    "CWE-732": {"technique": "T1222", "tactic": "defense-evasion", "name": "File and Directory Permissions Modification"},
    "CWE-776": {"technique": "T1059", "tactic": "execution", "name": "Command and Scripting Interpreter"},
    "CWE-798": {"technique": "T1078", "tactic": "initial-access", "name": "Valid Accounts"},
    "CWE-862": {"technique": "T1190", "tactic": "initial-access", "name": "Exploit Public-Facing Application"},
    "CWE-863": {"technique": "T1190", "tactic": "initial-access", "name": "Exploit Public-Facing Application"},
    "CWE-918": {"technique": "T1190", "tactic": "initial-access", "name": "Exploit Public-Facing Application"},
    "CWE-939": {"technique": "T1190", "tactic": "initial-access", "name": "Exploit Public-Facing Application"},
    "CWE-1188": {"technique": "T1190", "tactic": "initial-access", "name": "Exploit Public-Facing Application"},
}


def map_cwe_to_attack(cwe_list: list[str]) -> list[dict]:
    results = []
    seen = set()
    for cwe in cwe_list:
        mapping = CWE_TO_ATTACK.get(cwe)
        if mapping and mapping["technique"] not in seen:
            seen.add(mapping["technique"])
            results.append({
                "technique": mapping["technique"],
                "tactic": mapping["tactic"],
                "name": mapping["name"],
            })
    return results
