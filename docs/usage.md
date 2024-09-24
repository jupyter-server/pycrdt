## Quickstart

Pycrdt offers the following shared data types:

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
map1 = Map({"baz": 1})
array1 = Array([5, 6, 7])

array0.append(map1)
map0["key2"] = array1
```

Every change to `doc` (a modified/added/deleted value) will generate an update in the form of a binary encoded data.
You can listen to these updates and send them on the wire, so that they can be applied to a remote document.

You can also listen to changes on the individual shared data types (`text0`, `array1`, etc.) by registering callbacks,
that will be called with the change event(s), so that your application can react to data changes.

We say that `text0`, `array0` and `map0` are root types of `doc`.
When they got inserted into `doc`, we gave them a name. For instance, `text0` was inserted under `"text0"`.
This is how a remote document will retrieve the root types of the document, after applying the received updates:

```py
update = doc.get_update()

# the (binary) update could travel on the wire to a remote machine:

remote_doc = Doc()
remote_doc.apply_update(update)

remote_doc["text0"] = text0 = Text()
remote_doc["array0"] = array0 = Array()
remote_doc["map0"] = map0 = Map()
```

You could say that there is nothing fancy here, it's just about encoding data changes so that they can be applied on another object.
But this is where the magic of CRDTs comes into play.
Their algorithm ensures that if some changes are done concurrently on different objects representing the same data (for instance on different machines), applying the changes will lead to the same data on all objects. Without such algorithms, this property doesn't hold due to the fact that changes depend on the order in which they are applied, and that they take time to travel on the wire.

The most common example is inserting a different character on a text editor on two machines.
Say we start with a blank page on both editors, and the user on machine A inserts "a" at the same time the user on machine B inserts "b".
After receiving the other user's update, if no special care is taken, machine A will show "ba" and machine B will show "ab".
In other words, their document states will diverge, and thus users won't collaborate on the same document anymore.
CRDTs ensure that documents don't diverge, their shared documents will eventually have the same state. It will arbitrary be "ab" or "ba", but it will be the same on both machines.

## Transactions

Every change to a shared data happens in a document transaction, and there can only be one transaction at a time. Pycrdt offers two methods for creating transactions:

- `doc.transaction()`: used with a context manager, this will create a new transaction if there is no current one, or use the current transaction. This method will never block, and should be used most of the time.
- `doc.new_transaction()`: used with a context manager or an async context manager, this will always try to create a new transaction. This method can block, waiting for a transaction to be released.

### Non-blocking transactions

When no current transaction exists, an implicit transaction is created.
Grouping multiple changes in a single transaction makes them atomic: they will appear as done simultaneously rather than sequentially.

```py
with doc.transaction():
    text0 += ", World!"
    array0.append("bar")
    map0["key1"] = "value1"
```

Transactions can be nested: when a transaction is created inside another one, changes will be made in the outer transaction.
In the following example, all changes are made in transaction `t0`.

```py
with doc.transaction() as t0:
    text0 += ", World!"
    with doc.transaction() as t1:
        array0.append("bar")
        with doc.transaction() as t2:
            map0["key1"] = "value1"
```

### Blocking transactions

#### Multithreading

When used with a (non-async) context manager, the `new_transaction()` method will block the current thread waiting to acquire a transaction, with an optional timeout:

```py
from threading import Thread
from pycrdt import Doc

doc = Doc(allow_multithreading=True)

def create_new_transaction():
    with doc.new_transaction(timeout=3):
        ...

t0 = Thread(target=create_new_transaction)
t1 = Thread(target=create_new_transaction)
t0.start()
t1.start()
t0.join()
t1.join()
```

#### Asynchronous programming

When used with an async context manager, the `new_transaction()` method will yield to the event loop until a transaction is acquired:

```py
from anyio import create_task_group, run
from pycrdt import Doc

doc = Doc()

async def create_new_transaction():
    async with doc.new_transaction(timeout=3):
        ...

async def main():
    async with create_task_group() as tg:
        tg.start_soon(create_new_transaction)
        tg.start_soon(create_new_transaction)

run(main)
```

## Events

### Shared data events

Changes to shared data can be observed in order to react on them. For instance, if a character is inserted in a `Text` data,
a text editor should insert the character in the text shown to the user. This is done by registering callbacks.

```py
from pycrdt import TextEvent

def handle_changes(event: TextEvent):
    # process the event
    ...

text0_subscription_id = text0.observe(handle_changes)
```

The subscription ID can be used to unregister the callback later.

```py
text0.unobserve(text0_subscription_id)
```

For container data types like `Array` and `Map`, it can be useful to observe changes that are deeply nested in the hierarchy.
For instance, you may want to observe all changes that happen in `array0`, including changes in `map1`:

```yaml
array0:
  - 0
  - "foo"
  - "bar"
  - map1:
    "baz": 1
```

Using the `observe` method will only notify for changes happening at the top-level of the container, for instance when the value
at index 2 is deleted, but not for changes happening in `map1`. Use the `observe_deep` method instead, with a callback that accepts
a list of events.

```py
from pycrdt import ArrayEvent

def handle_deep_changes(events: list[ArrayEvent]):
    # process the events
    ...

array0_subscription_id = array0.observe_deep(handle_deep_changes)
```

Unregistering the callback is done with the same `unobserve` method.

### Document events

Observing changes made to a document is mostly meant to send the changes to another document, usually over the wire to a remote machine.
Changes can be serialized to binary by getting the event's `update`:

```py
from pycrdt import TransactionEvent

def handle_doc_changes(event: TransactionEvent):
    update: bytes = event.update
    # send binary update on the wire

doc.observe(handle_doc_changes)
```

Changes can be applied to a remote document at the other end of the wire:

```py
# receive binary update from e.g. a WebSocket
update: bytes

remote_doc.apply_update(update)
```

## Undo manager

An undo manager allows to undo/redo changes to a set of shared types belonging to a document:

```py
from pycrdt import Doc, Text, UndoManager

doc = Doc()

text = doc.get("text", type=Text)
text += "Hello"

undo_manager = UndoManager(doc=doc)
undo_manager.expand_scope(text)

text += ", World!"
print(str(text))
# prints: "Hello, World!"

undo_manager.undo()
print(str(text))
# prints: "Hello"

undo_manager.redo()
print(str(text))
# prints: "Hello, World!"
```

Undoing a change doesn't remove the change from the document's history, but applies a change that is the opposite of the previous change.
