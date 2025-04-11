import gc

import pytest


@pytest.fixture(scope="session", autouse=True)
def disable_gc(request):
    gc.disable()
    request.addfinalizer(gc.enable)


@pytest.fixture(scope="function", autouse=True)
def collect_gc(request):
    request.addfinalizer(gc.collect)
