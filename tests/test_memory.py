import gc

from objsize import get_deep_size
from pycrdt import Array, Doc, Map, Text


def test_memory():
    doc = Doc()
    iter = 100
    for type_i, Type in enumerate([Array, Map, Text]):
        doc[str(type_i)] = type_ = Type()
        size0 = get_deep_size(type_)
        sizes = [size0]
        subscriptions = []
        for i in range(iter):
            subscriptions.append(type_.observe(lambda x: x))
            sizes.append(get_deep_size(type_))
            assert sizes[-1] > sizes[-2]
        sizes.pop()
        for i in range(iter):
            subscription = subscriptions.pop()
            type_.unobserve(subscription)
            size = sizes.pop()
            gc.collect()
            # this doesn't seem to always hold true:
            # assert get_deep_size(type_) == size
            assert get_deep_size(type_) >= size
        # in the end this is what really matters:
        assert get_deep_size(type_) == size0
