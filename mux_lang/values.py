"""Shared runtime semantics for Mux values."""

from __future__ import annotations

import math


class ValueSemantics:
    """Language-level operations that must not depend on Python coercions."""

    @staticmethod
    def is_number(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    @classmethod
    def truthy(cls, value):
        if value is None or value is False:
            return False
        if cls.is_number(value):
            return value != 0
        if isinstance(value, (str, list, tuple, dict, range)):
            return len(value) != 0
        return True

    @classmethod
    def equal(cls, left, right, seen=None, check_step=None):
        if check_step is not None:
            check_step()
        if cls.is_number(left) and cls.is_number(right):
            return left == right
        if type(left) is not type(right):
            return False
        if left is right:
            return True
        if isinstance(left, (list, tuple, dict)):
            seen = seen if seen is not None else set()
            pair = (id(left), id(right))
            if pair in seen:
                return True
            seen.add(pair)
            try:
                if isinstance(left, (list, tuple)):
                    return len(left) == len(right) and all(
                        cls.equal(a, b, seen, check_step) for a, b in zip(left, right)
                    )
                if len(left) != len(right):
                    return False
                for key, value in left.items():
                    if check_step is not None:
                        check_step()
                    if key not in right or not cls.equal(value, right[key], seen, check_step):
                        return False
                return True
            except (TypeError, RecursionError):
                return False
            finally:
                seen.remove(pair)
        if isinstance(left, float) and math.isnan(left):
            return False
        return left == right

    @classmethod
    def type_name(cls, value):
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "boolean"
        if cls.is_number(value):
            return "number"
        if isinstance(value, str):
            return "string"
        if isinstance(value, list):
            return "list"
        if isinstance(value, tuple):
            return "tuple"
        if isinstance(value, dict):
            return "dictionary"
        if isinstance(value, range):
            return "range"
        return type(value).__name__
