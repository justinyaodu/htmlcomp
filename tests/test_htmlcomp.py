import unittest

from htmlcomp import *
from htmlcomp.elements import *


@component
def RedBox(*children, **attributes):
    return div(*children, style="background-color: red;", **attributes)


class OrderedList(Element):
    def parse_items(items):
        return items.split(",")

    def render(*, items, **attributes):
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
            div("Oops, ", img(src="banana.png"), " I did it again!")
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
            div(id="content", style="background-color: red;")(
                p("some text"),
                "stuff",
                blockquote("That's pretty rad!"),
            )
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

        element[:] = []
        self.assertEqual(
            Element.parse(str(element)),
            ol(li("hi"))
        )

    def test_implicitly_closed_tag(self):
        self.assertEqual(
            # div is implicitly closed
            Element.parse("<table><tr><td><div>hello</td></tr></table>"),
            table(tr(td(div("hello"))))
        )
