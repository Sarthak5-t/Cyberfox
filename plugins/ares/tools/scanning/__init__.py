from plugins.ares.tools.scanning.nuclei_templates import register_tools as register_nuclei_templates
from plugins.ares.tools.scanning.subjack import register_tools as register_subjack


def register_tools(ctx) -> None:
    register_nuclei_templates(ctx)
    register_subjack(ctx)
