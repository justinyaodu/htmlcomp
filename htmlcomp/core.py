__all__ = ["Element", "component", "html_name_to_python", "python_name_to_html"]

import re
from keyword import iskeyword
from html.parser import HTMLParser
from xml.etree import ElementTree


class Element:
    subclasses = {}
    void = False

    def __init_subclass__(cls, /, void = None, **kwargs):
        if void is not None:
            cls.void = void
        Element.subclasses[cls.__name__.lower()] = cls

    def __new__(cls, *args, **kwargs):
        element = super().__new__(Element)

        if cls is not Element:
            element.name = cls.__name__.lower()
        else:
            element.name = args[0].lower()
            args = args[1:]

        element.attributes = {}
        element.children = []
        element(*args, **kwargs)

        return element

    def __call__(self, *children, **attributes):
        self.children.extend(children)
        self.attributes.update(attributes)
        return self

    def render(*children, **attributes):
        pass

    def _render(self):
        current = self
        while True:
            subclass = Element.subclasses[current.name]
            rendered = subclass.render(*current.children, **current.attributes)
            if rendered is None:
                break
            current = rendered

        for i, child in enumerate(current):
            if isinstance(child, Element):
                current[i] = child._render()

        return current

    def _proxy(self, key):
        if isinstance(key, str):
            return self.attributes
        elif isinstance(key, (int, slice)):
            return self.children
        else:
            msg = f"Expected str, int, or slice; got {type(key).__name__}"
            raise TypeError(msg)

    def __getitem__(self, key):
        return self._proxy(key)[key]

    def __setitem__(self, key, value):
        self._proxy(key)[key] = value

    def __delitem__(self, key):
        del self._proxy(key)[key]

    def __iter__(self):
        return iter(self.children)

    def __len__(self):
        return len(self.children)

    def __contains__(self, key):
        if isinstance(key, str):
            return key in self.attributes
        else:
            msg = f"Expected str; got {type(key).__name__}"

    def __eq__(self, other):
        if not isinstance(other, Element):
            return NotImplemented
        return (self.name == other.name
                and self.attributes == other.attributes
                and self.children == other.children)

    def __repr__(self):
        if self.attributes:
            attributes = f", **{self.attributes}"
        else:
            attributes = ""

        if self.children:
            children = f"({', '.join(repr(child) for child in self.children)})"
        else:
            children = ""

        return f"{type(self).__name__}({repr(self.name)}{attributes}){children}"

    @staticmethod
    def parse(data):
        parser = Parser()
        parser.feed(data)
        parser.close()
        return parser.root

    def _add_to_builder(self, builder):
        rendered = self._render()
        subclass = Element.subclasses[rendered.name]

        attributes = {}
        for name, value in rendered.attributes.items():
            to_str = getattr(subclass, f"str_{name}", None)
            if to_str is not None:
                value = to_str(value)
            else:
                value = str(value)

            attributes[python_name_to_html(name)] = value

        builder.start(rendered.name, attributes)

        for child in rendered:
            if isinstance(child, Element):
                child._add_to_builder(builder)
            else:
                builder.data(str(child))

        builder.end(rendered.name)

    def __str__(self):
        builder = ElementTree.TreeBuilder()
        self._add_to_builder(builder)
        root = builder.close()
        return ElementTree.tostring(root, encoding="unicode", method="html")

    def parse__class(_class):
        return set(_class.split())

    def str__class(_class):
        return " ".join(sorted(_class))


def component(render_or_name, /, **kwargs):
    if isinstance(render_or_name, str):
        render_func = None
        name = render_or_name
    else:
        render_func = render_or_name
        name = render_func.__name__

    if render_func is not None:
        class_dict = dict(render=render_func)
    else:
        class_dict = {}

    return type(name, (Element,), class_dict, **kwargs)


def html_name_to_python(name):
    name = name.replace("-", "_")
    if iskeyword(name):
        name = "_" + name
    return name


def python_name_to_html(name):
    if name.startswith("_") and iskeyword(name[1:]):
        name = name[1:]
    name = name.replace("_", "-")
    return name


class Parser(HTMLParser):
    def reset(self):
        super().reset()
        self.root = None
        self.stack = []

    def add(self, value):
        if self.stack:
            self.stack[-1](value)
            return

        if isinstance(value, Element):
            if self.root is None:
                self.root = value
            else:
                raise ValueError("Multiple root elements")
        else:
            if not re.match(r"\s*", value):
                raise ValueError("Text outside of root element")

    def open_tag(self, tag, attributes, self_closing):
        subclass = Element.subclasses[tag]

        attributes = {html_name_to_python(k): v for k, v in attributes}
        for name in attributes:
            from_str = getattr(subclass, f"parse_{name}", None)
            if from_str is not None:
                attributes[name] = from_str(attributes[name])

        element = subclass(**attributes)

        self.add(element)
        self.stack.append(element)

        if subclass.void or self_closing:
            self.close_tag()

    def close_tag(self):
        self.stack.pop()

    def handle_starttag(self, tag, attrs):
        self.open_tag(tag, attrs, False)

    def handle_endtag(self, tag):
        # Handle implicitly closed tags.
        while self.stack and self.stack[-1].name != tag:
            self.close_tag()

        if self.stack:
            self.close_tag()
        else:
            raise ValueError("Unpaired end tag")

    def handle_startendtag(self, tag, attrs):
        self.open_tag(tag, attrs, True)

    def handle_data(self, data):
        self.add(data)
