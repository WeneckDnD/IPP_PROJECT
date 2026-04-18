"""
This module contains the main logic of the interpreter.

IPP: You must definitely modify this file. Bend it to your will.

Author: Ondřej Ondryáš <iondryas@fit.vut.cz>
Author: Tadeas Bujdoso <xbjdot00>
"""

import logging
from pathlib import Path
import re
from typing import Any, TextIO, cast

from lxml import etree
from lxml.etree import ParseError
from pydantic import ValidationError

from interpreter.error_codes import ErrorCode
from interpreter.exceptions import InterpreterError
from interpreter.input_model import (
    Block,
    ClassDef,
    Expr,
    Literal,
    Method,
    Program,
    Send,
    Var,
)

from .classes import False_, Integer, Nil, String, True_, Object
# from .objects import NewObject
from .scope import Scope

logger = logging.getLogger(__name__)

type base_class_type = Object | Integer | String | Nil | True_ | False_

CLASS_REGISTRY: dict[str, base_class_type | Any] = {
  "Object": Object,
  "Integer": Integer,
  "String": String,
  "Nil": Nil,
  "True": True_,
  "False": False_,
}


def update_built_in_classes():
    # equalTo:
    setattr(CLASS_REGISTRY["Object"], "equalTo:", Object.equal_to)






class Interpreter:
    """
    The main interpreter class, responsible for loading the source file and executing the program.
    """

    def __init__(self) -> None:
        self.current_program: Program | None = None

    def load_program(self, source_file_path: Path) -> None:
        """
        Reads the source SOL-XML file and stores it as the target program for this interpreter.
        If any program was previously loaded, it is replaced by the new one.

        IPP: If you wish to run static checks on the program before execution, this is a good place
             to call them from.
        """
        logger.info("Opening source file: %s", source_file_path)
        try:
            xml_tree = etree.parse(source_file_path)
        except ParseError as e:
            raise InterpreterError(
                error_code=ErrorCode.INT_XML, message="Error parsing input XML"
            ) from e
        try:
            self.current_program = Program.from_xml_tree(cast(Any, xml_tree.getroot()))
        except ValidationError as e:
            raise InterpreterError(
                error_code=ErrorCode.INT_STRUCTURE, message="Invalid SOL-XML structure"
            ) from e
    
    def define_new_class(self, name, base_class_name, methods):
        # Získame rodičovskú triedu z registra (napr. Object)
        parent_cls = CLASS_REGISTRY.get(base_class_name, None)
        if parent_cls is None:
            parent_class_def = self.find_class(base_class_name)
            if parent_class_def is None:
                self.define_new_class(base_class_name, "Object", {})
            else:
                self.define_new_class(base_class_name, parent_class_def.parent, parent_class_def.methods)
            parent_cls = CLASS_REGISTRY.get(base_class_name, None)
            if parent_cls is None:
                raise InterpreterError(
                    error_code=ErrorCode.SEM_UNDEF,
                    message=f"Undefined class '{base_class_name}'",
                )
        
        all_methods = {}
        for method in methods:
            all_methods[method.selector] = method
        
        # Dynamicky vytvoríme novú triedu
        # type(meno, (rodičia,), {atribúty/metódy})
        new_cls = type(name, (parent_cls,), all_methods)
        # print(name, parent_cls.__name__)
        # Zaregistrujeme ju, aby sa z nej dali vytvárať inštancie
        CLASS_REGISTRY[name] = new_cls
        return new_cls

    # def send_message(
    #     self, receiver: NewObject, selector: str, args: list[Any], scope: Scope
    # ) -> Any:
    #     """Dispatch a message send to a receiver object."""
    #     if isinstance(receiver.value, Block):
    #         return self.execute_block(receiver.value, scope, args)
    #     method, class_def = receiver.lookup(
    #         selector, cast(Program, self.current_program).classes
    #     )
    #     if method is None:
    #         att = receiver.get_attribute(selector)
    #         if att is not None:
    #             return att
    #     # built-in vs user-defined
    #     if callable(method):
    #         is_param = selector in receiver.param_foos and method is not None
    #         new_args = []
    #         for arg in args or []:
    #             if isinstance(arg.value, Block):
    #                 new_value = self.execute_block(arg.value, scope, [])
    #                 new_args.append(new_value)
    #             else:
    #                 new_args.append(arg)

    #         new_value = method(*new_args) if is_param else method()
    #         value_type = type(new_value).__name__
    #         new_parent = self.create_parent_by_type(value_type, new_value)
    #         return NewObject(None, new_value, new_parent)
    #     if method is None:
    #         current_self = scope.get_variable("self")
    #         attr_name = selector[:-1]
    #         searched_method, _ = receiver.lookup(
    #             attr_name, cast(Program, self.current_program).classes
    #         )
    #         if searched_method is not None:
    #             raise InterpreterError(
    #                 error_code=ErrorCode.INT_INST_ATTR,
    #                 message=f"Attribute '{attr_name}' already exists as method",
    #             )
    #         current_self.set_attribute(attr_name, *args)
    #         scope.update_variable("self", current_self)
    #         return current_self

    #     new_class_scope = Scope(scope)
    #     if class_def is not None:
    #         self_receiver = NewObject(class_def, receiver.value, receiver.parent)
    #         super_receiver = self.get_super_class(self_receiver)
    #         new_class_scope.set_variable("self", receiver)
    #         new_class_scope.set_variable("super", super_receiver)
    #     return self.execute_method(method, new_class_scope, args)
    
    def send_message2(self, receiver: type[CLASS_REGISTRY[str]], selector: str, args: list[Any], scope: Scope) -> Any:
        print('selector',receiver.__class__.__name__, selector )
        method = getattr(receiver, selector, None) ## test the inherited methods
        # parent_name = receiver.__class__.__bases__[0].__name__

        if method is None and selector[-1] == ':':
            check_method = getattr(receiver, selector[:-1], None)
            if check_method is not None:
                raise InterpreterError(
                    error_code=ErrorCode.INT_INST_ATTR,
                    message=f"Method '{selector[:-1]}' already exists as attribute in class {receiver.__class__.__name__}",
                )
            setattr(receiver, selector[:-1], args[0]) ## TODO !!!!! check more args 
            return args[0]

        if method is None:
            print(dir(receiver))
            raise InterpreterError(
                error_code=ErrorCode.INT_DNU,
                message=f"Method '{selector}' not found in class {receiver.__class__.__name__}",
            )
        
        if callable(method):
            return method(*args)
        
        if isinstance(method, Method):
            new_class_scope = Scope(scope)
            new_class_scope.set_variable("self", receiver)
            return self.execute_method(method, new_class_scope, args)
        return method
        


    def execute(self, input_io: TextIO) -> None:
        """
        Executes the currently loaded program, using the provided input stream as standard input.
        """
        logger.info("Executing program")
        assert self.current_program is not None

        update_built_in_classes()
        # Define all classes in the program
        for class_def in self.current_program.classes:
            self.define_new_class(class_def.name, class_def.parent, class_def.methods)

        scope = Scope(parent=None)
  
        main_class_def = self.find_class("Main")
        if main_class_def is None:
            raise InterpreterError(
                error_code=ErrorCode.SEM_MAIN, message="No Main class found in the program"
            )
        if not any(m.selector == "run" for m in main_class_def.methods):
            raise InterpreterError(
                error_code=ErrorCode.SEM_MAIN, message="No run method found in the Main class"
            )
        
        main_class = CLASS_REGISTRY["Main"]()
        ret = self.send_message2(main_class, "run", [], scope)
        print('end of program, ret',ret)

    def execute_method(self, method: Method | Any, parent_scope: Scope, args: list[Any]) -> Any:
        """Run a user-defined method body with the given arguments."""
        if method is not None:
            return self.execute_block(method.block, parent_scope, args)
        raise InterpreterError(error_code=ErrorCode.INT_DNU, message="method not found")

    def execute_block(self, block: Block, parent_scope: Scope, args: list[Any]) -> Any:
        """Evaluate a block: bind parameters, then run assignments in order."""
        if len(args) != block.arity:
            raise InterpreterError(
                error_code=ErrorCode.SEM_ARITY,
                message=f"Block arity mismatch: expected {block.arity} arguments, got {len(args)}",
            )
        param_names = {p.name for p in block.parameters}
        current_scope = Scope(parent=parent_scope)

        for param in block.parameters:
            param_name = param.name
            param_value = args[param.order - 1]
            current_scope.set_variable(param_name, param_value)
        ret_value = None
        for assgn in block.assigns:
            assgn_target = assgn.target  # o
            if assgn_target.name in param_names:
                raise InterpreterError(
                    error_code=ErrorCode.SEM_COLLISION,
                    message=f"Assignment to formal parameter '{assgn_target.name}' is not allowed",
                )
            assgn_expr = assgn.expr
            exp = self.execute_expression(assgn_expr, current_scope)
            current_scope.set_variable(assgn_target.name, exp)
            ret_value = exp
        return ret_value

    def execute_params(self) -> None:
        """Placeholder for parameter execution (unused)."""

    def execute_expression(self, expr: Expr, current_scope: Scope) -> Any:
        """Evaluate an expression in the given scope and return its value."""
        if expr.send is not None:
            return self.execute_send(expr.send, current_scope)
        if expr.literal is not None:
            return self.execute_literal(expr.literal)
        if expr.var is not None:
            return current_scope.get_variable(expr.var.name)
        # if expr.block is not None:
        #     return NewObject(None, expr.block, None)
        raise InterpreterError(
            error_code=ErrorCode.INT_OTHER, message="Invalid or unsupported expression"
        )


    # value is used in special case for 'from:' selector
    def execute_literal(self, literal: Literal) -> base_class_type | Any:
        """Build a class instance for a literal value."""
        if literal.class_id == "class":
            return CLASS_REGISTRY[literal.value]()
        
        return CLASS_REGISTRY[literal.class_id](literal.value)


    # def find_parent(self, parent: str) -> str:
    #     """Walk the class hierarchy and return the root parent name."""
    #     class_def = self.find_class(parent)
    #     prev_class_def = None
    #     while class_def is not None:
    #         prev_class_def = class_def
    #         class_def = self.find_class(class_def.parent)
    #     if prev_class_def is not None:
    #         return prev_class_def.parent
    #     return parent

    def find_class(self, class_name: str) -> ClassDef | None:
        """Look up a class definition by name in the loaded program."""
        for cls in cast(Program, self.current_program).classes:
            if cls.name == class_name:
                return cls
        return None

    def execute_send(self, send: Send, current_scope: Scope) -> Any:
        """Evaluate arguments and receiver, then perform the message send."""
        selector = send.selector
        arguments = []
        for arg in send.args:
            if arg.expr.var is not None and arg.expr.var.name == "super":
                exp_arg = current_scope.get_variable("self")
            else:
                exp_arg = self.execute_expression(arg.expr, current_scope)
            arguments.append(exp_arg)
        class_y = self.execute_expression(send.receiver, current_scope)

        if selector == "from:":
            if not arguments:
                raise InterpreterError(
                    error_code=ErrorCode.INT_INVALID_ARG,
                    message="from: requires a value argument",
                )

            return self.send_message2(class_y, "new", arguments, current_scope)
        return self.send_message2(class_y, selector, arguments, current_scope)

