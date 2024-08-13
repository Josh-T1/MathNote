
class TrackedString(str):
    """
    TrackedString tries to use 'duck typing' by implementing all behaviour associated with strings, with additional features such
    as storing souce data. This data could look like a file_path or the name of a callable that 'created' the string.


    --- Limitations:
        1. We give priority to left TrackedString. If string = TrackedString1(...) + TrackedString2(...) string.source_history will only contain
        the history of TrackedString1(...). This asserts there will always be exactly one 'root' source at the expense of tracking 'all' sources
        2. Speed most likley
    """

    def __new__(cls, string,  source_history=None):
        instance = super().__new__(cls, string)
        if isinstance(source_history, SourceHistory):
            pass
        elif isinstance(source_history, str):
            record = SourceRecord(source_history)
            source_history = SourceHistory()
            source_history.append(record)
        elif source_history is None:
            source_history = SourceHistory("None")
        else:
            raise TypeError(f"Invalid source_history type: {type(source_history)}")

        instance._source_history = source_history #type: ignore
        return instance

#    def __init__(self, string: str, source_history: SourceHistory) -> None:
#        self._source_history = source_history
#        assert isinstance(self._source_history, SourceHistory); print("print this is not wgoo")
    def join(self, iterable):
        if not iterable:
            return None # TODO

        joined_tex = self.__str__().join([str(tracked_string) for tracked_string in iterable])
        source_history = iterable[0].source_history
        for tracked_string in iterable[1:]:
            last_node = source_history.last_node()
#            print(source_history.last_node())
            tracked_string_root = tracked_string.source_history.root
            if last_node:
                last_node.child = tracked_string_root
            if tracked_string_root:
                tracked_string_root.parent = last_node
#        print(len(source_history))
        return TrackedString(joined_tex, source_history=source_history)


    @property
    def source_history(self): # TODO breaks everything
        source_history = SourceHistory()
        for record in self._source_history:
            source_history.append(record)
        return SourceHistory(source_history)

    def __getitem__(self, __key) -> 'TrackedString':
        new_source_history = self._source_history.append_and_copy(
                SourceRecord(f"__getitem__({__key})")
                )
        return TrackedString(super().__getitem__(__key), source_history=new_source_history)

    def modify_text(self, func: Callable[[str], str]):
        """ Method for using Trackedstring as argument for function: str -> str and using output to create new Trackedstring
        -- Params --
        func: function with str type param and str return type. functools.partial is helpfull here"""
        new_text = func(self.__str__())
        new_source_history = SourceRecord(func.__name__)
        return TrackedString(new_text,
                             source_history=self._source_history.append_and_copy(new_source_history)
                             )
    def sub(self, pattern: str, repl: str) -> "TrackedString":
        new_text = re.sub(pattern, repl, self.__str__())
        new_source = self._source_history.append_and_copy(SourceRecord(f"re.sub({pattern}, {repl}, {self.__str__()})"))
        return TrackedString(new_text, new_source)

    def __add__(self, other):
        """ Left add has priority. If result = TrackedString1(...) + TrackedString2(...), result.source_history.parent = TrackedString1(...) """
        if not isinstance(other, str):
            raise TypeError(f"Other must be type str not type {type(other)}")
        other_text = other if not isinstance(other, TrackedString) else other.__str__()
        new_source = self._source_history.append_and_copy(SourceRecord(f"{self} + {other}"))
        return TrackedString(super().__str__() + other_text,
                             source_history=new_source)

    # I should not need to specify these... however it is nice to 'see' what is happening
    def __contains__(self, string: str):
        return super().__contains__(string)

    def __len__(self):
        return super().__len__()

    def __ge__(self, other):
        if not isinstance(other, str):
            raise TypeError(f"'>=' not supported between instances of 'TrackedString' and {type(other)}")
        return super().__ge__(other)

    def __le__(self, other: str):
        if not isinstance(other, str):
            raise TypeError(f"'<=' not supported between instances of 'TrackedString' and {type(other)}")
        return super().__le__(other)

    def __lt__(self, other: str):
        if not isinstance(other, str):
            raise TypeError(f"'<' not supported between instances of 'TrackedString' and {type(other)}")
        return super().__lt__(other)

    def __gt__(self, other: str):
        if not isinstance(other, str):
            raise TypeError(f"'>' not supported between instances of 'TrackedString' and {type(other)}")
        return super().__ge__(other)

    def __eq__(self, other) -> bool:
        if not isinstance(other, str):
            raise TypeError(f"'==' not supported between instances of 'TrackedString' and {type(other)}")
        return super().__eq__(other)

    def __str__(self) -> str:
        return super().__str__()

    def __repr__(self):
        return (f"TrackedString({super().__repr__()}, self._source_history=SourceHistory(...))")

    def lower(self):
        return super().lower()

    def upper(self):
        return super().upper()
class SourceRecord:
    """
    Wrapper for abstract 'Node' object in a linked list.
    Stores data related to the source of a string  """
    def __init__(self, data: str):
        self.data = data
        self.parent: None | SourceRecord = None
        self.child: None | SourceRecord = None

    def __str__(self):
        return f"SourceRecord({self.data})"

    def __repr__(self) -> str:
        parent_exists = 'Yes' if self.parent else 'No'
        child_exists = 'Yes' if self.child else 'No'
        return (f"SourceRecord({self.data},"
                f"parent={parent_exists},"
                f"child={child_exists})")

class SourceHistory:
    """
    Wrapper for linked list datastructre.
    Container for SourceRecord objects """
    def __init__(self, *args):
        self.root: None | SourceRecord = None
        for arg in args:
            self.append(arg)

    def append(self, data):
        new_node = SourceRecord(data)
        if self.root is None:
            self.root = new_node
        else:
            current = self.root
            while current.child:
                current = current.child

            current.child = new_node
            new_node.parent = current
    @property
    def root_source(self):
        if not self.root:
            return None
        return self.root.data

    def append_and_copy(self, item: SourceRecord):
        """ Issues may arise if item.data is mutable """
        new_source = SourceHistory()
        current = self.root
        while current:
            new_source.append(current.data)
            current = current.child
        new_source.append(item.data)
        return new_source

    def last_node(self):
        current = self.root
        while current:
            if not current.child:
                break
            current = current.child
        return current


    def __iter__(self):
        current = self.root
        while current:
            yield current.data
            current = current.child
    def __repr__(self):
        return f"SourceHistory({list(self)})"

    def __str__(self):
        return '->'.join(event for event in self)

    def __len__(self):
        counter = 0
        current = self.root
        while current:
            current = current.child
            counter += 1
        return counter

    def __add__(self, other):
        if not isinstance(other, SourceHistory):
            raise TypeError(f"Unsupported opperand type(s) for +: 'SourceHistory' and '{type(other)}'")
        current = other.root
        while current:
            self.append(current.data)
            current.child
        return self # does this make sense?

