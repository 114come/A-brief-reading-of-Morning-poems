import json
import re


def render_template(template: str, context: dict) -> str:
    """Replace {{ node_id.output.field }} placeholders with values from context.

    The context dict is expected to have an "outputs" key mapping node IDs to
    their output dicts.  Nested paths are traversed via dot notation after
    stripping the optional "output" prefix segment.  If a path cannot be
    resolved, the original placeholder is kept unchanged.
    """

    def _replacer(m: re.Match) -> str:
        path = m.group(1).strip().split(".")
        if len(path) < 2:
            return m.group(0)

        node_id, *remaining = path
        # Skip optional "output" segment so both {{ n1.output }} and
        # {{ n1.output.field }} work intuitively.
        if remaining and remaining[0] == "output":
            remaining = remaining[1:]

        outputs = context.get("outputs", {})
        if node_id not in outputs:
            return m.group(0)
        value = outputs[node_id]
        for k in remaining:
            if isinstance(value, dict):
                value = value.get(k, m.group(0))
            else:
                return m.group(0)

        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)

    return re.sub(r"\{\{(.*?)\}\}", _replacer, template)
