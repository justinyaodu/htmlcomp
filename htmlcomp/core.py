__all__ = [
    "Element",
    "component",
    "html_name_to_python",
    "python_name_to_html",
    "ParseError"
]

from typing import *
from keyword import iskeyword
from inspect import getmembers
from html.parser import HTMLParser
from xml.etree import ElementTree


def prefixed_attributes(obj, prefix):
    return {k[len(prefix):]: v
            for k, v in getmembers(obj) if k.startswith(prefix)}


class Element:
    """Represent an HTML element or custom component.

    Note that all elements are instances of ``Element``, even if the
    element is created by calling a subclass. All subclass-specific
    functionality is handled by finding the subclass corresponding to
    the element name and calling the corresponding static methods. This
    allows the type of an element to be changed by changing the
    element's ``name`` attribute.
    """

    subclasses: ClassVar[dict[str, type]] = {}
    """Subclasses of Element, indexed by lowercase element names."""

    void: ClassVar[bool] = False
    """Whether this element is a void element."""

    name: str
    """The name of this element (e.g. ``div``, ``p``, ``span``)."""

    attributes: dict[str, Any]
    """This element's attributes.

    Attribute names use underscores instead of dashes, so the
    ``accept-charset`` attribute is accessed with the
    ``"accept_charset"`` key. Attribute names that conflict with Python
    keywords are prefixed with an underscore, so the ``class`` attribute
    is accessed with the ``"_class"`` key. These conversions ensure that
    attribute names are always valid Python identifiers, allowing them
    to be provided as keyword arguments.
    """

    children: list[Any]
    """This element's children.

    Children are typically elements (including components and fragments)
    or strings, but they can be arbitrary values.
    """

    def __init_subclass__(cls, /, void: Optional[bool] = None):
        """
        Initialize an Element subclass.

        The name of the class is converted to lowercase and used as the
        element name.

        Static methods on the subclass can be used to customize
        attribute parsing and serialization. If a HTML string contains
        an element with a name matching a subclass, the element has a
        ``foo`` attribute (for example), and a static method named
        ``parse_foo`` exists on the subclass, then that method will be
        used to parse the value of the ``foo`` attribute.

        Similarly, a static method named ``str_foo`` could be used to
        convert the attribute back to a string when generating HTML.

        :param void: Whether this element is a void element (in other
            words, whether this element should not have closing tags)
        """
        if void is not None:
            cls.void = void
        cls.parse_funcs = prefixed_attributes(cls, "parse_")
        cls.str_funcs = prefixed_attributes(cls, "str_")
        Element.subclasses[cls.__name__.lower()] = cls

    def __new__(cls, *args, **attributes):
        element = super().__new__(Element)

        if cls is Element:
            name = args[0].lower()
            children = args[1:]
        else:
            name = cls.__name__.lower()
            children = args

        element.name = name
        element.attributes = Element.subclasses[name].default_attributes()
        element.children = []
        element(*children, **attributes)

        return element

    def __init__(self, *args, **attributes):
        """
        Create a new element.

        This method doesn't actually do anything, because ``__new__``
        initializes the object instance.

        :param args: The name of the element if calling the ``Element``
            class directly, followed by any children to add.
        :param attributes: Any attributes to add.
        """
        pass

    def __call__(self, *children, **attributes) -> "Element":
        """Add children and add or modify attributes.

        :param children: Children to add.
        :param attributes: Attributes to add or modify. Hyphens in
            attribute names should be replaced with underscores, and
            attribute names that conflict with Python keywords should
            be prefixed with an underscore.
        :return: This element.
        """
        self.children.extend(children)
        self.attributes.update(attributes)
        return self

    def copy(self) -> "Element":
        """Return a shallow copy of this element."""
        return Element(self.name, *self.children, **self.attributes)

    def shallow_normalize(self) -> None:
        """Normalize this element's children.

        Consolidate adjacent strings, remove empty strings, and replace
        fragments with the fragments' children.

        To normalize this element's entire subtree, use ``normalize``
        instead.
        """
        flattened = []
        for child in self:
            if isinstance(child, Element) and not child.name:
                flattened.extend(child)
            else:
                flattened.append(child)

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

    def normalize(self) -> None:
        """Recursively normalize this element's subtree."""
        for child in self:
            if isinstance(child, Element):
                child.shallow_normalize()
        self.shallow_normalize()

    @staticmethod
    def transform(*children, **attributes) -> Any:
        """Transform a component of this type for rendering.

        :param children: The component's children.
        :param attributes: The component's attributes.
        :return: A partially rendered value. This is typically an
            element, a fragment, another component, or a string, but it
            can be any value. Use ``None`` to indicate that no
            transformation is necessary. Use an empty string or empty
            fragment to return nothing.
        """
        return None

    def render(self) -> "Element":
        """Recursively transform this component and its children.

        :return: The transformed and normalized result.
        """
        # Transform recursively until None is returned, indicating that
        # no more transformations are necessary.
        subclass = Element.subclasses[self.name]
        transformed = subclass.transform(*self.children, **self.attributes)
        if isinstance(transformed, Element):
            return transformed.render()
        elif transformed is not None:
            # Wrap non-Element results in a fragment.
            return Element("", transformed)

        rendered = self.copy()

        # Render all children.
        for i, child in enumerate(rendered):
            if isinstance(child, Element):
                rendered[i] = child.render()

        rendered.shallow_normalize()
        return rendered

    def _container_proxy(self, key: Union[str, int, slice]):
        if isinstance(key, str):
            return self.attributes
        elif isinstance(key, (int, slice)):
            return self.children
        else:
            raise TypeError(
                    "Expected str, int, or slice; "
                    f"got {type(key).__name__}")

    def __getitem__(self, key: Union[str, int, slice]) -> Any:
        """Get an attribute, a child, or a slice of children."""
        return self._container_proxy(key)[key]

    def __setitem__(self, key: Union[str, int, slice], value: Any) -> None:
        """Replace an attribute, a child, or a slice of children."""
        self._container_proxy(key)[key] = value

    def __delitem__(self, key: Union[str, int, slice]) -> None:
        """Delete an attribute, a child, or a slice of children."""
        del self._container_proxy(key)[key]

    def __iter__(self):
        """Iterate over this element's children."""
        return iter(self.children)

    def __len__(self):
        """Return the number of children that this element has."""
        return len(self.children)

    def __contains__(self, key: str) -> bool:
        """Return whether this element has an attribute."""
        if isinstance(key, str):
            return key in self.attributes
        else:
            raise TypeError(f"Expected str; got {type(key).__name__}")

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

        return f"Element({repr(self.name)}{attributes}){children}"

    @staticmethod
    def parse(data: str) -> "Element":
        """Parse HTML and return the parsed nodes in a fragment."""
        parser = Parser()
        parser.feed(data)
        return parser.close()

    def _add_to_builder(self, builder: ElementTree.TreeBuilder) -> None:
        subclass = Element.subclasses[self.name]

        attributes = {}
        for name, value in self.attributes.items():
            if name in subclass.str_funcs:
                value = subclass.str_funcs[name](value)
                if value is None:
                    continue
            else:
                value = str(value)
            attributes[python_name_to_html(name)] = value

        builder.start(self.name, attributes)

        for child in self:
            if isinstance(child, Element):
                child._add_to_builder(builder)
            else:
                builder.data(str(child))

        builder.end(self.name)

    def __str__(self):
        """Render this element and convert it to an HTML string."""
        rendered = self.render()

        builder = ElementTree.TreeBuilder()
        rendered._add_to_builder(builder)
        root = builder.close()

        string = ElementTree.tostring(root, encoding="unicode", method="html")
        if not rendered.name:
            # Remove fragment start and end tags.
            string = string[2:-3]
        return string

    @staticmethod
    def default_attributes() -> dict[str, Any]:
        """Return a dictionary of default attributes for this type of
        element.
        """
        return dict(_class=set())

    @staticmethod
    def parse__class(_class):
        return set(_class.split())

    @staticmethod
    def str__class(_class):
        if _class:
            return " ".join(sorted(_class))
        else:
            return None


def component(transform_or_name: Union[str, Callable], /, **kwargs) -> type:
    """Create a new component type from a transform function or string.

    If a transform function is provided, the function name is used as
    the element name. If a string is provided, then that string is used
    as the element name, and the component is not transformed.

    All keyword arguments are passed to ``Element.__init_subclass__()``.
    """
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


def html_name_to_python(name: str) -> str:
    name = name.replace("-", "_")
    if iskeyword(name):
        name = "_" + name
    return name


def python_name_to_html(name: str) -> str:
    if name.startswith("_") and iskeyword(name[1:]):
        name = name[1:]
    name = name.replace("_", "-")
    return name


class Parser(HTMLParser):
    def reset(self):
        super().reset()
        self.root = Element("")
        self.stack = [self.root]

    def close(self):
        super().close()
        unclosed_tags = len(self.stack) - 1
        if unclosed_tags > 0:
            raise ParseError(f"{unclosed_tags} unclosed tag(s)")
        return self.root

    def add(self, value):
        self.stack[-1](value)

    def open_tag(self, tag, attributes, self_closing):
        subclass = Element.subclasses[tag]

        attributes = {html_name_to_python(k): v for k, v in attributes}
        for name, value in attributes.items():
            if name in subclass.parse_funcs:
                attributes[name] = subclass.parse_funcs[name](value)

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
            if start_tag:
                raise ParseError(
                        f"End tag {repr(tag)} "
                        f"does not match start tag {repr(start_tag)}")
            else:
                raise ParseError(
                        f"End tag {repr(tag)} has no matching start tag")

    def handle_startendtag(self, tag, attrs):
        self.open_tag(tag, attrs, True)

    def handle_data(self, data):
        self.add(data)


class ParseError(Exception):
    pass
