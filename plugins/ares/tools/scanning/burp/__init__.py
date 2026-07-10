from plugins.ares.tools.scanning.burp.burp_scan import register_tools as register_burp_scan
from plugins.ares.tools.scanning.burp.burp_spider import register_tools as register_burp_spider
from plugins.ares.tools.scanning.burp.burp_repeater import register_tools as register_burp_repeater


def register_tools(ctx) -> None:
    register_burp_scan(ctx)
    register_burp_spider(ctx)
    register_burp_repeater(ctx)
