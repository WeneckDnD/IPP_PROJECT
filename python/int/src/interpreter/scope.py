from typing import *

class Scope:
    def __init__(self, parent) -> Any:
        self.parent = parent
        self.variables = {}

    def set_variable(self, name, value):
        self.variables[name] = value

    def get_variable(self, name):
        if name in self.variables:
            return self.variables[name]
        elif self.parent is not None:
            return self.parent.get_variable(name)
        else:
            raise NameError(f"Variable '{name}' not found in scope.") # TODO use interpreter errors
    
    def update_variable(self, name, new):
        if name in self.variables:
            self.variables[name] = new
        elif self.parent is not None:
            self.parent.update_variable(name, new)
        else:
            raise NameError(f"Variable '{name}' not found in scope.")
