from collections import defaultdict
from jinja2 import Template

class PromptManager:
    def __init__(self):
        # {name: {version: {"template": str, "meta": dict}}}
        self.templates = defaultdict(dict)

    def register_template(self, name, template_str, version="default", meta=None):
        self.templates[name][version] = {"template": template_str, "meta": meta or {}}

    def get_template(self, name, version="default"):
        return self.templates.get(name, {}).get(version, None)

    def render_template(self, name, context, version="default"):
        entry = self.get_template(name, version)
        if not entry:
            raise ValueError(f"Template '{name}' (version: {version}) not found")
        tpl = Template(entry["template"])
        return tpl.render(**context)

    def list_templates(self):
        return {name: list(vers.keys()) for name, vers in self.templates.items()}

    def get_meta(self, name, version="default"):
        entry = self.get_template(name, version)
        return entry["meta"] if entry else None

prompt_manager = PromptManager() 