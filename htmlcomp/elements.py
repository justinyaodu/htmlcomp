from .core import component, html_name_to_python


# Taken from the HTML spec:
# https://html.spec.whatwg.org/multipage/indices.html#elements-3
ALL_ELEMENTS = (
    "a", "abbr", "address", "area", "article", "aside", "audio", "b", "base",
    "bdi", "bdo", "blockquote", "body", "br", "button", "canvas", "caption",
    "cite", "code", "col", "colgroup", "data", "datalist", "dd", "del",
    "details", "dfn", "dialog", "div", "dl", "dt", "em", "embed", "fieldset",
    "figcaption", "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5",
    "h6", "head", "header", "hgroup", "hr", "html", "i", "iframe", "img",
    "input", "ins", "kbd", "label", "legend", "li", "link", "main", "map",
    "mark", "math", "menu", "meta", "meter", "nav", "noscript", "object", "ol",
    "optgroup", "option", "output", "p", "param", "picture", "pre", "progress",
    "q", "rp", "rt", "ruby", "s", "samp", "script", "section", "select",
    "slot", "small", "source", "span", "strong", "style", "sub", "summary",
    "sup", "svg", "table", "tbody", "td", "template", "textarea", "tfoot",
    "th", "thead", "time", "title", "tr", "track", "u", "ul", "var", "video",
    "wbr"
)


# Taken from the HTML spec:
# https://html.spec.whatwg.org/multipage/syntax.html#void-elements
VOID_ELEMENTS = (
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
    "param", "source", "track", "wbr"
)


fragment = component("")


__all__ = ["fragment"]
for element in ALL_ELEMENTS:
    cls = component(element, void=(element in VOID_ELEMENTS))
    name = html_name_to_python(element)
    globals()[name] = cls
    __all__.append(name)
