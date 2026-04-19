"""docstring"""
# from typing import Any

# from interpreter.input_model import (
#   Assign,
#   Block,
#   ClassDef,
#   Expr,
#   Literal,
#   Method,
#   Var,
# )


# class BuiltInBlock:
#   arity: int
#   params: list[str]
#   return_type: str
#   build_in_handler: str

# class BuiltInMethod:
#   selector: str
#   is_built_in: True
#   block: BuiltInBlock

# class BuiltInClassDef:
#   name: str
#   parent: str
#   methods: list[BuiltInMethod | Method]

# class BaseObject:
#   def __init__(self, *args: Any):
#     self.fields = {}
#     self.args = args
#     self.parent = None

# def create_new_class(name: str, base_classes: tuple[type[BaseObject], ...] =
# (BaseObject,)) -> BaseObject:
#   new_class = type(name, base_classes, {})()
#   return new_class

# # Toto asi pojde inde
# def execute_builtin(self, handler, receiver, args):
#   if handler == "builtin_identical_to:":
#     return self.builtin_identical_to(
#       receiver,
#       args[0],
#     )
#   if handler == "builtin_new":
#     return self.builtin_new()

#   raise Exception(f"Unknown builtin: {handler}")

# def builtin_identical_to(self, receiver, other):
#   return receiver is other

# def builtin_new(self):
#   return create_new_class(self.name)
# # po tade

# def build_builtin_classes() -> dict[str, ClassDef]:
#   builtins = {}

#   # -----------------------------------------------------
#   # Object
#   # -----------------------------------------------------

#   object_class = BuiltInClassDef(
#     name="Object",
#     parent=None,
#     methods=[
#       BuiltInMethod(
#         selector="identicalTo:",
#         block=BuiltInBlock(
#           arity=1,
#           params=["obj"],
#           return_type="boolean",
#           build_in_handler="builtin_identical_to:",
#         ),
#       ),
#       Method(
#         selector="asString",
#         block=Block(
#           arity=0,
#           params=[],
#           assigns=[
#             Assign(
#               target=Var(name="_"),
#               expr=Expr(
#                 literal=Literal(class_id="String", value=""),
#               ),
#             ),
#           ],
#         ),
#       ),
#       BuiltInMethod(
#         selector="new",
#         block=BuiltInBlock(
#           arity=0,
#           params=[],
#           return_type="Object",
#           build_in_handler="builtin_new",
#         ),
#       ),
#     ],
#   )
#   builtins["Object"] = object_class

#   object_integer = BuiltInClassDef(
#     name="Integer",
#     parent="Object",
#     methods=[
#       BuiltInMethod(
#         selector="new",
#         block=BuiltInBlock(
#           arity=0,
#           params=[],
#           return_type="Integer",
#           build_in_handler="builtin_new",
#         ),
#       )
#     ]
#   )
#   builtins["Integer"] = object_integer

#   return builtins
