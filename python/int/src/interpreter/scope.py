"""Interpreter lexical scopes for variable binding and lookup."""

from typing import Any


class Scope:
    """A scope with a map of names to values and an optional parent scope."""

    def __init__(self, parent) -> Any:
        self.parent = parent
        self.variables = {}

    def set_variable(self, name, value):
        """Bind ``name`` to ``value`` in this scope."""
        self.variables[name] = value

    def get_variable(self, name):
        """Return the value for ``name``, searching this scope then parents."""
        if name in self.variables:
            return self.variables[name]
        if self.parent is not None:
            return self.parent.get_variable(name)
        raise NameError(f"Variable '{name}' not found in scope.")  # TODO use interpreter errors

    def update_variable(self, name, new):
        """Set ``name`` to ``new`` in this scope or the nearest defining parent."""
        if name in self.variables:
            self.variables[name] = new
        elif self.parent is not None:
            self.parent.update_variable(name, new)
        else:
            raise NameError(f"Variable '{name}' not found in scope.")
