from dataclasses import dataclass, field
from pathlib import Path
from typing import Generic, Iterator, TypeVar

from .source_file import TrackedText, FileType
from ..exceptions import FlashcardNotFoundException


@dataclass
class Section:
    name: str # TODO make Enum
    content: TrackedText
    pdf_path: Path | None = None
    title: TrackedText | None = None
    title_pdf: Path | None = None



@dataclass
class Flashcard:
    main_section: Section
    proof_section: Section | None = None
    seen: bool = False

    def filetype(self) -> FileType:
        return self.main_section.content.filetype()


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
