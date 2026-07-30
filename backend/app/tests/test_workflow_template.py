from app.services.ai.workflow.template import render_template


def test_simple_replacement() -> None:
    """{{ node_id.output }} resolves to the node's output value directly."""
    context = {"outputs": {"greeting": "hello"}}
    assert render_template("{{ greeting.output }}", context) == "hello"


def test_nested_path() -> None:
    """{{ node_id.output.field }} resolves to a field inside the node output."""
    context = {"outputs": {"n1": {"nested": "deep"}}}
    assert render_template("{{ n1.output.nested }}", context) == "deep"


def test_missing_path_keeps_placeholder() -> None:
    """An unresolvable path leaves the original placeholder unchanged."""
    context = {"outputs": {}}
    result = render_template("{{ missing.output }}", context)
    assert result == "{{ missing.output }}"


def test_deeply_nested_path() -> None:
    """{{ node_id.output.a.b.c }} traverses multiple levels inside a node output."""
    context = {"outputs": {"n1": {"a": {"b": {"c": "leaf"}}}}}
    assert render_template("{{ n1.output.a.b.c }}", context) == "leaf"


def test_no_placeholders() -> None:
    """Plain text without placeholders is returned as-is."""
    assert render_template("plain text", {}) == "plain text"


def test_multiple_placeholders() -> None:
    """Multiple placeholders in one template are all replaced."""
    context = {
        "outputs": {
            "a": "A",
            "b": "B",
        }
    }
    result = render_template("{{ a.output }} and {{ b.output }}", context)
    assert result == "A and B"


def test_output_prefix_optional() -> None:
    """Paths that omit the 'output' segment still work.

    This tests the edge case where someone writes {{ n1.field }}
    instead of {{ n1.output.field }}.
    """
    context = {"outputs": {"n1": {"field": "val"}}}
    assert render_template("{{ n1.field }}", context) == "val"


def test_dict_value_serialized() -> None:
    """Placeholders that resolve to dict/list are JSON-serialized."""
    context = {"outputs": {"n1": {"a": 1, "b": 2}}}
    result = render_template("{{ n1.output }}", context)
    assert result == '{"a": 1, "b": 2}'


def test_partial_nested_output() -> None:
    """Path that stops mid-nesting returns a JSON-serialized sub-dict."""
    context = {"outputs": {"n1": {"a": {"x": 1}}}}
    assert render_template("{{ n1.output.a }}", context) == '{"x": 1}'
