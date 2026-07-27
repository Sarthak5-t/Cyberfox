from __future__ import annotations


def calculate_priority(
    cvss: float | None,
    epss: float | None,
    in_kev: bool,
    has_exploit: bool,
) -> dict:
    cvss_val = cvss if cvss is not None else 5.0
    epss_val = epss if epss is not None else 0.1

    kev_mult = 0.3 if in_kev else 1.0
    exploit_mult = 0.5 if has_exploit else 1.5

    score = (11 - cvss_val) * (1 - epss_val) * kev_mult * exploit_mult
    normalized = min(max(score * (100 / 16.5), 0), 100)

    if normalized < 10:
        tier = "CRITICAL"
    elif normalized < 25:
        tier = "HIGH"
    elif normalized < 50:
        tier = "MEDIUM"
    else:
        tier = "LOW"

    return {
        "priority_score": round(normalized, 2),
        "priority_tier": tier,
        "cvss": cvss_val,
        "epss": epss_val,
        "in_kev": in_kev,
        "has_exploit": has_exploit,
    }
