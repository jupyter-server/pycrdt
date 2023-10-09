[![Build Status](https://github.com/davidbrochart/pycrdt/workflows/test/badge.svg)](https://github.com/davidbrochart/pycrdt/actions)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

# pycrdt

CRDTs based on [Yrs](https://github.com/y-crdt/y-crdt).

## Install

```console
pip install pycrdt
```

## Usage

`pycrdt` offers the following shared data types:
- `Text`: a type similar to a `str`.
- `Array`: a type similar to a `list`.
- `Map`: a type similar to a `dict`.

You can initialize them with their Python built-in counterparts:

```py
from pycrdt import Text, Array, Map

text0 = Text("Hello")
array0 = Array([0, "foo"])
map0 = Map({"key0": "value0"})
```

But they are pretty useless on their own. They are just placeholders waiting to be inserted in a shared document. Only then do they really become useful:

```py
from pycrdt import Doc

doc = Doc()
doc["text0"] = text0
doc["array0"] = array0
doc["map0"] = map0
```

Now you can operate on them as you would expect, for instance:

```py
text0 += ", World!"
array0.append("bar")
map0["key1"] = "value1"
```

Note that an `Array` and a `Map` can hold other shared data types:

```py
map1 = Map({"foo": 1})
array1 = Array([5, 6, 7])

array0.append(map1)
map0["key2"] = array1
```

Every change to `doc` (a modified/added/deleted value) will generate an update in the form of some encoded binary data.
You can listen to these updates and send them on the wire, so that they can be applied to a remote document.

We say that `text0`, `array0` and `map0` are root types of `doc`.
When they got inserted into `doc`, we gave them a name. For instance, `text0` was inserted under `"text0"`.
This is how a remote document will retrieve the root types of the document, after applying the received updates:

```py
from pycrdt import Doc, Text, Array, Map

remote_doc = Doc()
remote_doc.apply_updates(updates)

text0 = Text()
array0 = Array()
map0 = Map()
remote_doc["text0"] = text0
remote_doc["array0"] = array0
remote_doc["map0"] = map0
```

You could say that there is nothing fancy here, it's just about encoding data changes so that they can be applied on another object.
But this is where the magic of CRDTs comes into play.
Their algorithm ensures that if some changes are done concurrently on different objects representing the same data (for instance on different machines), applying the changes will lead to the same data on all objects. Without such algorithms, this property doesn't hold due to the fact that changes depend on the order in which they are applied, and that they take time to travel on the wire.

The most common example is inserting a different character on a text editor on two machines.
Say we start with a blank page on both editors, and the user on machine A inserts "a" at the same time the user on machine B inserts "b".
After receiving the other user's update, if no special care is taken, machine A will show "ba" and machine B will show "ab".
In other words, their document states will diverge, and thus users won't collaborate on the same document anymore.
CRDTs ensure that documents don't diverge, their shared documents will eventually have the same state. It will arbitrary be "ab" or "ba", but it will be the same on both machines.
