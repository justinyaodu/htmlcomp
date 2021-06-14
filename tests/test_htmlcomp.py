import unittest

from htmlcomp import *
from htmlcomp.elements import *


@component
def RedBox(*children, **attributes):
    return div(*children, style="background-color: red;", **attributes)


class OrderedList(Element):
    def parse_items(items):
        return items.split(",")

    def transform(*, items, **attributes):
        return ol(*[li(item) for item in items], **attributes)


class TestHtmlComp(unittest.TestCase):
    def _test_html(self, html):
        root = Element.parse(html)
        self.assertEqual(html, str(root))
        self.assertEqual(root, eval(repr(root)))

    def test_div(self):
        self._test_html('<div id="greeting" class="apple banana">Hello, <strong>world</strong>!</div>')

    def test_void_element(self):
        self._test_html('<div>Look, <img src="apple.png" alt="Photo of a green apple"> apple!</div>')

    def test_erroneous_self_closing_void_element(self):
        self.assertEqual(
            Element.parse('<div>Oops, <img src="banana.png"/> I did it again!</div>'),
            fragment(div("Oops, ", img(src="banana.png"), " I did it again!"))
        )

    def test_explicit_element_name(self):
        element_text = "The quick brown fox jumps over the lazy dog"
        element_id = "pangram"
        self.assertEqual(
            Element("p", element_text, id=element_id),
            p(element_text, id=element_id)
        )

    def test_callable(self):
        animals = ul(li("cat"))

        new_animals = animals(li("dog"), id="animals")
        self.assertIs(animals, new_animals)

        animals(li("fish"))

        self.assertEqual(
            ul(li("cat"), li("dog"), li("fish"), id="animals"),
            animals
        )

    def test_attribute(self):
        element = div()
        self.assertFalse("_class" in element)

        element(_class=set(["foo"]))
        self.assertTrue("_class" in element)

        del element["_class"]
        self.assertFalse("_class" in element)

        element["_class"] = set(["bar"])
        self.assertTrue("_class" in element)

        self.assertEqual(element["_class"], set(["bar"]))

    def test_children(self):
        element = p(strong("Lorem ipsum"), " ", em("dolor sit amet"), ".")

        self.assertEqual(len(element), 4)
        self.assertEqual(element[1:5:2], [" ", "."])

        del element[2]
        self.assertEqual(len(element), 3)
        self.assertEqual(element[2], ".")
        self.assertEqual(element[-1], ".")

    def test_function_component(self):
        element = RedBox(p("some text"), "stuff", blockquote("That's pretty rad!"), id="content")
        self.assertEqual(
            Element.parse(str(element)),
            fragment(div(id="content", style="background-color: red;")(
                p("some text"),
                "stuff",
                blockquote("That's pretty rad!"),
            ))
        )

    def test_class_component(self):
        element = Element.parse('<orderedlist items="alpha,beta,gamma" id="greek-letters"/>')
        self.assertEqual(
            Element.parse(str(element)),
            Element.parse("".join([
                '<ol id="greek-letters">',
                '<li>alpha</li>',
                '<li>beta</li>',
                '<li>gamma</li>',
                '</ol>'
            ]))
        )

        element = Element.parse('<orderedlist items="hi">oops!</orderedlist>')
        with self.assertRaises(TypeError):
            str(element)

        element[0][:] = []
        self.assertEqual(
            Element.parse(str(element)),
            fragment(ol(li("hi")))
        )

    def test_shallow_normalize(self):
        element = div(
            "a",
            fragment("b", "c", div(), fragment("d"), "e"),
            "f",
            div(),
            "",
            div(),
        )
        element.shallow_normalize()
        self.assertEqual(
            element,
            div(
                "abc",
                div(),
                fragment("d"),
                "ef",
                div(),
                div(),
            )
        )

    def test_normalize(self):
        element = div(
            "a",
            fragment(
                "b",
                fragment(
                    "",
                    "c",
                    div(),
                    "d",
                    "",
                ),
                "e",
                fragment(
                    "f",
                    div(),
                    "",
                    div(),
                ),
                "",
                div(),
                "g"
            ),
            "h"
        )
        element.normalize()
        self.assertEqual(
            element,
            div(
                "abc",
                div(),
                "def",
                div(),
                div(),
                div(),
                "gh"
            )
        )

    def test_mismatched_tags(self):
        with self.assertRaises(ParseError):
            Element.parse("<div></p>")

    def test_extra_closing_tag(self):
        with self.assertRaises(ParseError):
            Element.parse("<p></p></div>")

    def test_contains(self):
        element = p("hello", _class=set(), id="greeting")

        self.assertTrue("_class" in element)
        self.assertFalse("class" in element)

        self.assertTrue("id" in element)

        self.assertFalse("hello" in element)

        with self.assertRaises(TypeError):
            0 in element

        with self.assertRaises(TypeError):
            [] in element

    def test_getitem(self):
        element = p("hello", "there", _class=set(), id="greeting")

        self.assertEqual(element[0], "hello")
        self.assertEqual(element[1], "there")
        self.assertEqual(element[-1], "there")

        with self.assertRaises(IndexError):
            element[2]

        with self.assertRaises(IndexError):
            element[-3]

        self.assertEqual(element[-1::-1], ["there", "hello"])

        self.assertEqual(element["_class"], set())
        self.assertEqual(element["id"], "greeting")

        with self.assertRaises(KeyError):
            element["class"]

        with self.assertRaises(TypeError):
            element[None]
