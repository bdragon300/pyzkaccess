import pytest


@pytest.fixture
def generator_sends_collector():
    """
    Collect all values sent by generator.send(value) to a given list
    Typical usage:

        def test_pytest_fixture(generator_sends_collector):
            items = []
            test_function(callback=generator_sends_collector(items))
            assert items == [1, 2, 3]
    """
    def w(collect_list):
        def collector(*a, **kw):
            item = yield
            while item is not None:
                collect_list.append(item)
                item = yield
            collect_list.append(item)

        return collector

    return w
