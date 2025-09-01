from dataclasses import dataclass, field
from typing import Iterator, TypedDict

from .source_file import TrackedText, FileType
from ..exceptions import FlashcardNotFoundException
from ..config import CONFIG

# TODO: .proof
@dataclass
class Flashcard:
    section_name: str
    question: TrackedText
    answer: TrackedText
    pdf_answer_path: None | str = None
    pdf_question_path: None | str = None
    additional_info: dict[str, TrackedText] = field(default_factory=dict)
    seen: bool = False

    def filetype(self) -> FileType:
        return self.question.filetype()

    def add_info(self, name: str, info: TrackedText) -> None:
        self.additional_info[name] = info

    def __repr__(self) -> str:
        question = "..." if self.question else 'None'
        answer = "..." if self.answer else 'None'
        return f"Flashcard(question={question}, answer={answer}, pdf_answer_path={self.pdf_question_path}, pdf_question_path={self.pdf_answer_path}, file_type={self.filetype()})"

    def __str__(self) -> str:
        return f"Flashcard(question={self.question}, answer={self.answer}, pdf_answer_path={self.pdf_question_path}, pdf_question_path={self.pdf_answer_path})"


class Node:
    def __init__(self, data: Flashcard) -> None:
        self.data = data
        self.next: Node | None = None
        self.prev: Node | None = None

class FlashcardDoubleLinkedList:
    """ Container for Flashcards """
    def __init__(self, *args) -> None:
        self.head: Node | None= None
        self.current: Node | None= None
        for arg in args:
            self.append(arg)

    def clear(self) -> None:
        self.head = None
        self.current = None

    def remove(self, index: int) -> None:
        """ Remove node at index """
        if index > len(self) or index < 0:
            raise IndexError(f"Index {index} is out of range for remove operation")

        for _index, node in enumerate(self):
            if _index != index:
                continue
            # adjust next, prev referecnes
            if (next_node := node.next):
                next_node.prev = node.prev
            if (prev_node := node.prev):
                prev_node.next = node.next
            break


    def append(self, data) -> None:
        new_node = Node(data)
        if not self.head:
            self.current = new_node
            self.head = new_node

        else:
            cur = self.head
            while cur.prev:
                cur = cur.prev
            cur.prev = new_node

    def prepend(self, data: Flashcard) -> None:
        new_node = Node(data)
        if (old_head := self.head):
            self.head = new_node
            self.head.prev = old_head
            old_head.next = self.head

        else:
            self.current = new_node
            self.head = self.tail = new_node

    def get_next(self) -> Flashcard:
        # Current node exists and has next reference, then return next reference and set current to next
        if self.current and self.current.next:
            self.current = self.current.next
            return self.current.data
        else:
            raise FlashcardNotFoundException("Already at the end of the flashcards")

    def get_prev(self) -> Flashcard:
        if self.current and self.current.prev:
            self.current = self.current.prev
            return self.current.data
        else:
            raise FlashcardNotFoundException("Already at the begging of the flashcards")

    def _get_last_node(self) -> Node | None:
        current = self.head
        while current and current.prev:
            current = current.prev
        return current

    def __iter__(self) -> Iterator[Node]:
        """ [head -> head.prev -> ... -> head.prev.(...).prev] """
        current = self.head
        while current:
            yield current
            current = current.prev

    def __len__(self) -> int:
        counter = 0
        for _ in self:
            counter += 1
        return counter

    def __reversed__(self) -> Iterator[Node]:
        """ [head <- last.next.(...).next <- ... <- last.next <- last] """
        current = self._get_last_node()
        while current:
            yield current
            current = current.next


class SectionNamesDescriptor:
    def __init__(self, name: str, value: str):
        self.name = name
        self.value = value

    def __get__(self, instance, owner=None):
        return self
    def __str__(self):
        return self.value


class ImmutableMeta(type):
    _is_initialized = False

    def __new__(mcs, name, bases, class_dict):
        user_enum_key_values = {key.upper(): value for key, value in CONFIG.section_names.items()}
        class_dict.update(user_enum_key_values)
        for key, value in class_dict.items():
            if not key.startswith("__"):
                class_dict[key] = SectionNamesDescriptor(key, value)
        cls = super().__new__(mcs, name, bases, class_dict)
        cls._is_initialized = True
        return cls

    def is_name(cls, name:str) -> bool:
        for attr_name in cls.__dict__:
            if name == attr_name:
                return True
        return False

    def __iter__(cls):
        for attr_name in cls.__dict__:
            attr_value = getattr(cls, attr_name)
            if isinstance(attr_value, SectionNamesDescriptor):
                yield attr_value

    def __setattr__(cls, key, value):
        if cls._is_initialized and key in cls.__dict__:
            raise AttributeError(f"Cannot modify attribute '{key}'. SectionNames attributes are immutable.")
        super().__setattr__(key, value)

    def __iterable__(cls):
        return cls

    def __contains__(cls, value):
        if isinstance(value, str):
            return value in [i.value for i in cls]
        elif isinstance(value, SectionNamesDescriptor):
            return value.value in [i.value for i in cls]
        else:
            return False


# TODO: This solution sucks
# Warning: we dynamically set attr 'proof' using the value of SectionNames.PROOF
class SectionNames(metaclass=ImmutableMeta):
    DEFINITION = "defin"
    THEOREM = "theo"
    DERIVATION = "der"
    PROOF = "proof"
    COROLLARY = "corollary"
    LEMMA = "lemma"
    PROPOSITION = "proposition"
    UNNAMED = "unnamed"
    PREAMBLE = "preamble"

# We would prefer to have name as enum (containing all section names), however users may define new sections in config file. Look at ImmutableMeta in mathnotelib.utils
# Using SectionNames/SectionNamesDescriptor is hack, not really sure how to fix this
class Section(TypedDict):
    name: str # TODO make Enum
    content: TrackedText
    header: TrackedText


