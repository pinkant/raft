from log import Log
import logging

test_logger = logging.getLogger("Test")


def test_append_item():
    log = Log(test_logger)
    assert log.append_item(1, {'a': 1}) == 1
    assert log.append_item(1, {'a': 2}) == 2


def test_sync_at_item():
    log = Log(test_logger)
    # Test adding to a log with 0, 1, and 2 elements.
    assert log.sync_at_item(0, 0)
    assert log.append_item(1, {'a': 1}) == 1
    assert log.sync_at_item(1, 1)
    assert log.append_item(1, {'a': 2}) == 2
    assert log.sync_at_item(2, 1)
    assert log.append_item(1, {'a': 3}) == 3
    assert log.sync_at_item(3, 1)
    # Test rolling back a log to 2 and 0 elements.
    assert log.sync_at_item(2, 1)
    assert log.append_item(1, {'a': 4}) == 3
    assert log.sync_at_item(0, 0)
    assert log.append_item(1, {'a': 5}) == 1


def test_sync_at_item_too_big_index():
    log = Log(test_logger)
    # Test that sync will return False if the index too big.
    assert not log.sync_at_item(1, 1)
    assert log.append_item(1, {'a': 1}) == 1
    assert not log.sync_at_item(2, 1)
    assert log.append_item(1, {'a': 2}) == 2
    assert not log.sync_at_item(3, 1)


def test_sync_at_time_mismatch_terms():
    log = Log(test_logger)
    # Test when the term mismatches
    assert log.append_item(1, {'a': 1}) == 1
    assert log.sync_at_item(1, 2)
    assert log.append_item(1, {'a': 2}) == 1
    assert log.append_item(1, {'a': 3}) == 2
    assert not log.sync_at_item(2, 2)
    assert log.append_item(2, {'a': 4}) == 2


def test_get_item():
    log = Log(test_logger)
    assert log.get_item(1) is None
    log.append_item(1, {'a': 1})
    assert log.get_item(1) == {'a': 1}
    assert log.get_item(2) is None
