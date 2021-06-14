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

    def copy(self):
        return Element(self.name, *self.children, **self.attributes)

    def shallow_normalize(self):
        # Flatten fragments.
        flattened = []
        for child in self:
            if isinstance(child, Element) and not child.name:
                flattened.extend(child)
            else:
                flattened.append(child)

        # Normalize text nodes.
        normalized = []
        for child in flattened:
            if isinstance(child, str):
                if not child:
                    # Remove empty strings.
                    continue
                elif normalized and isinstance(normalized[-1], str):
                    # Combine adjacent strings.
                    normalized[-1] += child
                else:
                    normalized.append(child)
            else:
                normalized.append(child)

        self.children = normalized

    def normalize(self):
        for child in self:
            if isinstance(child, Element):
                child.shallow_normalize()
        self.shallow_normalize()

    def transform(*children, **attributes):
        pass

    def render(self):
        # Transform recursively until None is returned, indicating that
        # no more transformations are necessary.
        subclass = Element.subclasses[self.name]
        transformed = subclass.transform(*self.children, **self.attributes)
        if transformed is not None:
            return transformed.render()

        rendered = self.copy()
        for i, child in enumerate(rendered):
            if isinstance(child, Element):
                rendered[i] = child.render()

        rendered.shallow_normalize()
        return rendered

    def _container_proxy(self, key):
        if isinstance(key, str):
            return self.attributes
        elif isinstance(key, (int, slice)):
            return self.children
        else:
            raise TypeError(
                    "Expected str, int, or slice; "
                    f"got {type(key).__name__}")

    def __getitem__(self, key):
        return self._container_proxy(key)[key]

    def __setitem__(self, key, value):
        self._container_proxy(key)[key] = value

    def __delitem__(self, key):
        del self._container_proxy(key)[key]

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
        rendered = self.render()
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

        string = ElementTree.tostring(root, encoding="unicode", method="html")
        if not self.name:
            # Remove fragment start and end tags.
            string = string[2:-3]
        return string

    def parse__class(_class):
        return set(_class.split())

    def str__class(_class):
        return " ".join(sorted(_class))


def component(transform_or_name, /, **kwargs):
    if isinstance(transform_or_name, str):
        transform = None
        name = transform_or_name
    elif callable(transform_or_name):
        transform = transform_or_name
        name = transform.__name__
    else:
        raise TypeError(
                "Expected str or callable; "
                f"got {type(transform_or_name).__name__}")

    if transform is not None:
        class_dict = dict(transform=transform)
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
        self.root = Element("")
        self.stack = [self.root]

    def add(self, value):
        self.stack[-1](value)

    def open_tag(self, tag, attributes, self_closing):
        subclass = Element.subclasses[tag]

        attributes = {html_name_to_python(k): v for k, v in attributes}
        for name in attributes:
            from_str = getattr(subclass, f"parse_{name}", None)
            if from_str is not None:
                attributes[name] = from_str(attributes[name])

        element = subclass(**attributes)
        self.add(element)

        if not subclass.void and not self_closing:
            self.stack.append(element)

    def close_tag(self):
        self.stack.pop()

    def handle_starttag(self, tag, attrs):
        self.open_tag(tag, attrs, False)

    def handle_endtag(self, tag):
        start_tag = self.stack[-1].name
        if tag == start_tag:
            self.close_tag()
        else:
            raise ValueError(
                    f"End tag {repr(tag)} "
                    f"does not match start tag {repr(start_tag)}")


    def handle_startendtag(self, tag, attrs):
        self.open_tag(tag, attrs, True)

    def handle_data(self, data):
        self.add(data)
