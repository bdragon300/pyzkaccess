import pytest


@pytest.fixture
def generator_sends_collector(collect_list):
    """
    Collect all values sent by generator.send(value) to a given list
    :param collect_list: list where all items will be placed to
    :return:
    """
    def collector(*a, **kw):
        item = yield
        while item is not None:
            collect_list.append(item)
            item = yield
        collect_list.append(item)

    return collector
