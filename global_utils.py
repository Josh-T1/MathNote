from pathlib import Path
import json

""" Config """
CONFIG_PATH = Path(__file__).parent / "config.json"

def get_config():
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)
    return config
config = get_config()

def save_config(config: dict):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=6)

def load_json(file: str):
    with open(file, "r") as f:
        contents = json.load(f)
    return contents

def dump_json(file: str, contents: str):
    with open(file, "w") as f:
        json.dump(contents, f)
config = get_config()


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
        user_enum_key_values = {key.upper(): value for key, value in config['section-names'].items()}
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


class SectionNames(metaclass=ImmutableMeta):
    DEFINITION = "defin"
    THEOREM = "theo"
    DERIVATION = "der"
    PROOF = "pf"
    COROLLARY = "corollary"
    LEMMA = "lemma"
    PROPOSITION = "proposition"


