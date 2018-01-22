class LogEntry:
    """Represents the Raft log entry."""
    def __init__(self, term, entry):
        self.term = term
        self.entry = entry


class Log:
    """Represent the Raft log."""

    def __init__(self, logger):
        self.log = []
        self.logger = logger

    def append_item(self, term, entry):
        """
        Appends the entry at the end of the log.
        :param term: The current term.
        :param entry: The log entry.
        :return: The log index of the added entry.
        """
        # ToDo Add logic that ignores a new item if it is already in the log.
        self.log.append(LogEntry(term, entry))
        return len(self.log)

    def sync_at_item(self, index, term):
        """
        Syncs up the log with the given leader server log.

        Removes the all elements starting from the given index if the element
        with the given index has different term than on the server.

        :param index: The index of an element in the leader server log.
        :param term: The term of an element in the leader server log.
        :return: True if the log contains an item with the same term at a given index, otherwise False.
        """
        if self.len() < index:
            self.logger.info(f"Responding to the server that the logs are not in sync because "
                             f"the log does not contain an entry at {index} index.")
            return False
        if self.get_item_term(index) != term:
            self.logger.info(f"Removing all elements from the log starting from {index} because "
                             f"that record term {self.get_item_term(index)} does not match "
                             f"the server's term {term}.")
            self.log = self.log[:index - 1]
            # Only tell it to try again if there is something else
            # in the log that can conflict.
            return self.len() == 0
        self.log = self.log[:index]
        return True

    def len(self):
        """Returns the number of elements in the log."""
        return len(self.log)

    def get_item_term(self, index):
        """
        Returns the term of an item with the given index.

        :param index: 1-based index of an element.
        :return: The term of the item, or 0 if the index pointing at the position right
                 before the first element.
        """
        return self.log[index - 1].term if index else 0

    def get_item(self, index):
        """
        Returns the element of the log with a given index.

        Returns None if the given index is pointing at the position right
        after the last element.

        :param index: 1-based element index
        """
        return None if len(self.log) + 1 == index else self.log[index - 1].entry
