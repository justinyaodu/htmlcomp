# htmlcomp

`htmlcomp` provides a concise Python API for parsing, manipulating, and generating HTML. It also supports rendering of custom components, similar to [React](https://reactjs.org).

## Examples

### Creating HTML

Nested elements with attributes can be created concisely:

```python
>>> from htmlcomp.elements import *
>>> content = div(
...     h1("Hello world!"),
...     p(
...         "I like to read ",
...         a("Wikipedia", href="https://en.wikipedia.org/")
...     )
... )
>>>
```

To get the corresponding HTML, simply use `str`:

```
>>> raw_html = str(content)
>>> print(raw_html)
<div><h1>Hello world!</h1><p>I like to read <a href="https://en.wikipedia.org/">Wikipedia</a></p></div>
>>>
```

The element classes in `htmlcomp.elements` accept child nodes as positional arguments and attributes as keyword arguments. Element instances can also be called (as if they were functions) to add more children or attributes. This allows children to be put after attributes for improved readability:

```python
>>> banner = div(id="banner")(
...     img(src="logo.png"),
...     p("Lorem ipsum dolor sit amet"),
... )
>>> print(banner)
<div id="banner"><img src="logo.png"><p>Lorem ipsum dolor sit amet</p></div>
>>>
```

This strategy can also be used to append children to an existing element:

```python
>>> animals = ul()
>>> animals(li("cat"))
Element('ul', **{'_class': set()})(Element('li', **{'_class': set()})('cat'))
>>> animals(li("dog"))
Element('ul', **{'_class': set()})(Element('li', **{'_class': set()})('cat'), Element('li', **{'_class': set()})('dog'))
>>> print(animals)
<ul><li>cat</li><li>dog</li></ul>
>>>
```

When an existing element is called, it returns itself, which explains the `repr` output on the console. The `repr` output reveals that any element can be created by passing the element name as an argument to the `Element` class, along with the children and attributes as usual:

```python
>>> from htmlcomp import Element
>>> print(Element("div", Element("p", style="color: blue;")))
<div><p style="color: blue;"></p></div>
>>>
```

The `repr` output also shows that every element has a `_class` attribute, which is an empty set by default. (This corresponds to the `class` attribute in HTML, but the name is prefixed with an underscore to avoid conflicting with the Python keyword.) To add custom classes, pass a set as the `_class` keyword argument:

```python
>>> terminal = code("echo 'I am a cow' | cowsay", _class=set(["green-text", "black-background"]))
>>> terminal
Element('code', **{'_class': {'green-text', 'black-background'}})("echo 'I am a cow' | cowsay")
>>> print(terminal)
<code class="black-background green-text">echo 'I am a cow' | cowsay</code>
>>>
```

### Manipulating Elements

Elements can be explored and modified using their `name`, `children`, and `attributes`:

```python
>>> terminal.name
'code'
>>> terminal.children
["echo 'I am a cow' | cowsay"]
>>> terminal.attributes
{'_class': {'green-text', 'black-background'}}
>>> terminal.name = "pre"
>>> terminal.children.append(" && echo 'goodbye' | cowsay")
>>> terminal.attributes["data-language"] = "bash"
>>> print(terminal)
<pre class="black-background green-text" data-language="bash">echo 'I am a cow' | cowsay &amp;&amp; echo 'goodbye' | cowsay</pre>
>>>
```

If accessing the `children` list and `attributes` dictionary feels too verbose, square brackets can be used on the element itself:

```python
>>> terminal[0]
"echo 'I am a cow' | cowsay"
>>> terminal[0] = "echo 'Take me to your leader' | cowsay"
>>> terminal[-1::-1]
[" && echo 'goodbye' | cowsay", "echo 'Take me to your leader' | cowsay"]
>>> terminal["_class"]
{'green-text', 'black-background'}
>>> del terminal["data-language"]
>>> print(terminal)
<pre class="black-background green-text">echo 'Take me to your leader' | cowsay &amp;&amp; echo 'goodbye' | cowsay</pre>
>>>
```

The `in` operator tests for the presence of an attribute:

```python
>>> "_class" in terminal
True
>>> "id" in terminal
False
>>>
```

Iterating over an element will iterate over children:

```python
>>> for child in terminal:
...     print(child)
... 
echo 'Take me to your leader' | cowsay
 && echo 'goodbye' | cowsay
>>>
```

Lastly, the `normalize` method combines adjacent strings and discards empty strings:

```python
>>> terminal.normalize()
>>> for child in terminal:
...     print(child)
... 
echo 'Take me to your leader' | cowsay && echo 'goodbye' | cowsay
>>>
```

### Parsing HTML

HTML strings can be parsed with the static method `Element.parse`:

```python
>>> parsed = Element.parse('<p class="foo bar">Hi there!</p><p>How are you?</p>')
>>>
```

A piece of HTML might have multiple nodes at the top level, like the example above which has two `p`s. Thus, `Element.parse` returns all of the top level nodes, enclosed in a special type of element called a fragment. This is essentially an invisible tag whose only purpose is to contain other tags:

```python
>>> parsed.name
''
>>> for child in parsed:
...     print(child)
... 
<p class="bar foo">Hi there!</p>
<p>How are you?</p>
>>> print(parsed)
<p class="bar foo">Hi there!</p><p>How are you?</p>
>>>
```

The aforementioned `normalize` method also "disassembles" fragments below the top level by replacing them with their children:

```python
>>> wrapper = div(parsed)
>>> wrapper[0].name
''
>>> wrapper.normalize()
>>> wrapper[0].name
'p'
>>> wrapper[1].name
'p'
>>>
```

### Defining Custom Components

The heart of a custom component is the transform function, which takes the element's children and attributes and returns another element. The simplest way to create a custom component is to use the `component` decorator on a transform function:

```python
>>> from htmlcomp import component
>>> @component
... def Excited(*children, excitement=1, **attributes):
...     return strong(*children, "!" * excitement, **attributes)
... 
>>> 
```

Specifying the `excitement` attribute as a keyword argument allows it to be accessed directly instead of using `attributes["excitement"]`, and also allows a default value to be provided. Now that the component is defined, it can be instantiated in the same way as the built-in elements:

```python
>>> chocolate = Excited("I love chocolate", excitement=3, style="color: red;")
>>> chocolate
Element('excited', **{'_class': set(), 'excitement': 3, 'style': 'color: red;'})('I love chocolate')
>>>
```

To actually render the component using the transform function, use the `render` method:

```python
>>> rendered = chocolate.render()
>>> rendered
Element('strong', **{'_class': set(), 'style': 'color: red;'})('I love chocolate!!!')
>>> print(rendered)
<strong style="color: red;">I love chocolate!!!</strong>
>>>
```

Using `str` on a custom component will also render it:

```python
>>> print(chocolate)
<strong style="color: red;">I love chocolate!!!</strong>
>>>
```

Custom components can be parsed just like normal elements:

```python
>>> parsed = Element.parse('<Excited excitement="2">The weather is nice today</Excited>')
>>> parsed
Element('', **{'_class': set()})(Element('excited', **{'_class': set(), 'excitement': '2'})('The weather is nice today'))
>>> print(parsed)
Traceback (most recent call last):
  ...
TypeError: can't multiply sequence by non-int of type 'str'
>>>
```

Oops! It looks like the `excitement` attribute was parsed as a string, but the component expects an integer. To get custom parsing, it is necessary to convert the component to an Element subclass:

```python
>>> class Excited(Element):
...     @staticmethod
...     def parse_excitement(excitement):
...         return int(excitement)
...     @staticmethod
...     def transform(*children, excitement, **attributes):
...         return strong(*children, "!" * excitement, **attributes)
...     @staticmethod
...     def default_attributes():
...         return dict(excitement=1)
... 
>>>
```

Any method that starts with `parse_` will be used for attribute parsing, so `parse_excitement` will be used to parse the `excitement` attribute. Also, the default value for `excitement` is now provided by the `default_attributes` method instead of the transform function. This makes the default value visible in the element's attributes, which can be desirable in some cases. Now the parsing will work as expected:

```python
>>> parsed = Element.parse('<Excited excitement="2">The weather is nice today</Excited>')
>>> print(parsed)
<strong>The weather is nice today!!</strong>
>>>
```

Components can be nested arbitrarily, and can also return fragments:

```python
>>> @component
... def ExcitedParagraphs(*children, **attributes):
...     return fragment(*[Excited(child, **attributes) for child in children])
... 
>>> paragraphs = ExcitedParagraphs("Wonderful", "Amazing", "Excellent", excitement=4)
>>> print(paragraphs)
<strong>Wonderful!!!!</strong><strong>Amazing!!!!</strong><strong>Excellent!!!!</strong>
>>> 
```

Components can also be abused to implement recursive algorithms (with lazy evaluation, no less):

```python
>>> @component
... def Factorial(*, n, product=1, **attributes):
...     if n <= 1:
...         return product
...     else:
...         return Factorial(n=(n - 1), product=(product * n))
... 
>>> thunk = Factorial(n=5)
>>> thunk
Element('factorial', **{'_class': set(), 'n': 5})
>>> result = thunk.render()
>>> result
Element('', **{'_class': set()})(120)
>>> print(result)
120
>>>
```

This example illustrates that components can actually return arbitrary data, which is then converted to a string.

## Sources of Inspiration

* [React](https://reactjs.org): function and class components, using attributes like props, and fragments
* [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/) and [dominate](https://github.com/Knio/dominate): using indexing to access an element's attributes and children
* W3C DOM: `normalize` method for consolidating text nodes
