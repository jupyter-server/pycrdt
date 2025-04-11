import gc

import pytest


@pytest.fixture(scope="function", autouse=True)
def collect_gc(request):
    request.addfinalizer(gc.collect)
