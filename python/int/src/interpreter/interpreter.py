"""
This module contains the main logic of the interpreter.

IPP: You must definitely modify this file. Bend it to your will.

Author: Ondřej Ondryáš <iondryas@fit.vut.cz>
Author: Tadeas Bujdoso <xbjdot00>
"""

import logging
from pathlib import Path
from typing import Any, TextIO

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

from .classes import False_, Integer, Nil, String, True_
from .objects import NewObject
from .scope import Scope

logger = logging.getLogger(__name__)


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
            self.current_program = Program.from_xml_tree(xml_tree.getroot())
        except ValidationError as e:
            raise InterpreterError(
                error_code=ErrorCode.INT_STRUCTURE, message="Invalid SOL-XML structure"
            ) from e

    def create_parent_by_type(self, obj_type: str, value= None) -> Any:
        """Wrap a Python value as the corresponding runtime parent object."""
        # print(f'value to create {value}')
        match obj_type:
            case "int":
                return Integer.new(value if value is not None else 0)
            case "str":
                return String.new(value if value is not None else "")
            case "None":
                return Nil.new()
            case "bool":
                return (
                    True_.new()
                    if value is not None and (value is True or value == 1)
                    else False_.new()
                )
            case _:
                return None

    def send_message(self, receiver: NewObject, selector: str, args: list, scope: Scope):
        """Dispatch a message send to a receiver object."""
        print(f"💬SEND MESSAGE: {selector} {args} {receiver.__class__}")
        # print(f'DIR Receiver: {receiver.parent.__class__} {dir(receiver)}, selector: {selector}')
        # print(f'❓Receiver: {isinstance(receiver.value, Block)}, Selector: {selector}')
        if isinstance(receiver.value, Block) and selector == "value:":
            return self.execute_block(receiver.value, scope, args)
        method = receiver.lookup(selector, self.current_program.classes)
        # print(f'Method: {method}, Selector: {selector}, Receiver: {receiver.attributes}')
        if method is None:
            # print(f'Selector: {selector}, Receiver: {receiver.attributes}')
            att = receiver.get_attribute(selector)
            # print(f'Attribute: {att}')
            if att is not None:
                return att
        # built-in vs user-defined
        if callable(method):
            is_param = selector in receiver.param_foos and method is not None
            print(f"isParam {is_param}")
            new_value = method(*args) if is_param else method()
            print(f"New value: {new_value}")
            value_type = type(new_value).__name__
            # print(f'Value type: {value_type}')
            new_parent = self.create_parent_by_type(value_type, new_value)
            # print(f'New parent: {new_parent}')
            return NewObject(None, new_value, new_parent)
        print(f"Method: {method}")
        if method is None:
            current_self = scope.get_variable("self")
            print(f"Current args: {args}, Selector: {selector}")
            current_self.set_attribute(selector[:-1], *args)
            scope.update_variable("self", current_self)
            return current_self

        new_class_scope = Scope(scope)
        new_class_scope.set_variable("self", receiver)
        return self.execute_method(method, new_class_scope, args)

    def execute(self, input_io: TextIO) -> None:
        """
        Executes the currently loaded program, using the provided input stream as standard input.
        """
        logger.info("Executing program")
        assert self.current_program is not None

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
        # print(main_class_def)
        parent_class_str = self.find_parent(main_class_def.parent)
        parent_class = self.create_obj_by_type(parent_class_str)
        main_class = NewObject(main_class_def,None, parent_class)
        self.send_message(main_class, "run", [], scope)
        # scope.set_variable("self", main_class)

        # main_class = None
        # for cls in self.current_program.classes:
        #     if cls.name == "Main":
        #         main_class = cls
        #         break
        # if not main_class:
        #     raise InterpreterError(
        #         error_code=ErrorCode.SEM_MAIN, message="No Main class found in the program"
        #     )

        # run_method = None
        # for mthd in main_class.methods:
        #     if mthd.selector == "run":
        #         run_method = mthd
        #         break
        # if not run_method:
        #     raise InterpreterError(
        #         error_code=ErrorCode.SEM_MAIN, message="No run method found in the Main class"
        #     )

        # self.execute_method(run_method, scope, [])

    def execute_method(self, method: Method, parent_scope: Scope, args: list) -> Any:
        """Run a user-defined method body with the given arguments."""
        # arity ?
        # find block
        # execute the block (execute_block)
        # block_arity = method.block.arity # TODO
        if method is not None:
            return self.execute_block(method.block, parent_scope, args)
        raise InterpreterError(error_code=ErrorCode.INT_DNU, message="method not found")

    def execute_block(self, block: Block, parent_scope: Scope, args: list) -> Any:
        """Evaluate a block: bind parameters, then run assignments in order."""
        print(f"EXECUTE BLOCK: {block.parameters} {block.assigns}")
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
            print(f"PARAM NAME: {param_name} PARAM VALUE: {param_value}")
            current_scope.set_variable(param_name, param_value)
        # self.scope.set_variable()
        ret_value = None
        for assgn in block.assigns:
            assgn_target = assgn.target  # o
            if assgn_target.name in param_names:
                raise InterpreterError(
                    error_code=ErrorCode.SEM_COLLISION,
                    message=f"Assignment to formal parameter '{assgn_target.name}' is not allowed",
                )
            print(f"Assign target: {assgn_target.name}")
            assgn_expr = assgn.expr
            exp = self.execute_expression(assgn_expr, current_scope)  # NewObject()
            print(f"Assign expr: {exp}")
            current_scope.set_variable(assgn_target.name, exp)
            print(f"💾STORED: {assgn_target.name} {exp}")
            # look_up = exp.lookup("foo")
            # print(look_up)
            # self.execute_block(look_up.block, current_scope)
            ret_value = exp
        return ret_value

    def execute_params():
        """Placeholder for parameter execution (unused)."""



    def execute_expression(self, expr: Expr, current_scope: Scope) -> Any:
        """Evaluate an expression in the given scope and return its value."""
        print(f"EXECUTE EXPRESSION: {expr}")
        if expr.send is not None:
            # print(f"SEND")
            return self.execute_send(expr.send, current_scope)
        if expr.literal is not None:
            # print(f"LITERAL")
            return self.execute_literal_new(expr.literal)
        if expr.var is not None:
            # print(f"VARIABLE")
            # print(f"value: {x}")
            return current_scope.get_variable(expr.var.name)
        if expr.block is not None:
            return NewObject(None, expr.block, None)
        print(f"🛑EXECUTE EXPRESSION: {expr} RETURNING NONE")
        raise InterpreterError(
            error_code=ErrorCode.INT_OTHER, message="Invalid or unsupported expression"
        )

    def execute_literal(self, literal: Literal) -> Any:
        """Reduce a literal to a plain Python value."""
        if literal.class_id == "Integer":
            return int(literal.value)
        if literal.class_id == "String":
            return literal.value
        if literal.class_id == "True":
            return True
        if literal.class_id == "Nil":
            return None
        if literal.class_id == "False":
            return False
        if literal.class_id == "class":
            # print(f"CLASS")
            return self.find_class(literal.value)  # TODO: Error None case
        return None

    # value is used in special case for 'from:' selector
    def execute_literal_new(self, literal: Literal) -> Any:
        """Build a NewObject wrapper for a literal value."""
        print(f"EXECUTE LITERAL NEW: {literal}")
        if literal.class_id == "Integer":
            value = int(literal.value)
            parent_class = Integer.new(value)
            return NewObject(None, value, parent_class)
        if literal.class_id == "String":
            value = literal.value
            parent_class = String.new(value)
            return NewObject(None, value, parent_class)
        if literal.class_id == "True":
            value = True
            parent_class = True_.new()
            return NewObject(None, value, parent_class)
        if literal.class_id == "False":
            value = False
            parent_class = False_.new()
            return NewObject(None, value, parent_class)
        if literal.class_id == "Nil":
            value = None
            parent_class = Nil.new()
            return NewObject(None, value, parent_class)
        if literal.class_id == "class":
            class_def = self.find_class(literal.value)
            # if class_def is None:
            #     raise InterpreterError(
            #         error_code=ErrorCode.SEM_UNDEF,
            #         message=f"Undefined class '{literal.value}'",
            #     )
            parent_class_str = self.find_parent(literal.value)
            parent_class = self.create_obj_by_type(parent_class_str)
            print(parent_class, parent_class_str)
            return NewObject(class_def, None, parent_class)
        return None

    def execute_literal_new_from(self, literal: Literal, value: any) -> Any:
        """Construct a class instance from a literal class name and a value."""
        class_def = self.find_class(literal.value)
        # if class_def is None:
        #     raise InterpreterError(
        #         error_code=ErrorCode.SEM_UNDEF,
        #         message=f"Undefined class '{literal.value}'",
        #     )
        parent_class_str = self.find_parent(literal.value)
        parent_class = self.create_obj_by_type(parent_class_str, value)
        return NewObject(class_def, value, parent_class)

    def create_obj_by_type(self, obj_type: str, *value) -> any:
        """Instantiate a built-in type object by name."""
        match obj_type:
            case "Integer":
                return Integer.new(*value)
            case "String":
                return String.new(*value)
            case "Nil":
                return Nil.new()
            case "True":
                return True_.new()
            case "False":
                return False_.new()

    def find_parent(self, parent: str):
        """Walk the class hierarchy and return the root parent name."""
        class_def = self.find_class(parent)
        # print(class_def)
        prev_class_def = None
        while class_def is not None:
            prev_class_def = class_def
            class_def = self.find_class(class_def.parent)
        if prev_class_def is not None:
            return prev_class_def.parent
        return parent


    def find_class(self, class_name: str) -> ClassDef | None:
        """Look up a class definition by name in the loaded program."""
        for cls in self.current_program.classes:
            if cls.name == class_name:
                return cls
        # print(f'NONE {cls} ')
        return None

    def execute_send(self, send: Send, current_scope: Scope) -> Any:
        """Evaluate arguments and receiver, then perform the message send."""
        print(f"EXECUTE SEND: {send}")
        selector = send.selector  # foo
        arguments = []
        for arg in send.args:
            order = arg.order
            print(f"ORDER: {order}")
            exp_arg = self.execute_expression(arg.expr, current_scope)
            arguments.append(exp_arg)
        print(f"ARGUMETS: {arguments}")
        class_y = self.execute_expression(send.receiver, current_scope)  # object

        # print(f"Executing send: selector={selector}, arguments={arguments}")

        # TODO: Call dedicated methods according to current Class ( Integer, String, Object,
        # Nil etc )
        # - function to find out if current selector is build-in or not for the current Parent
        # Class
        if selector == "new":
            # return self.send_message(class_y, selector, arguments, current_scope)
            # parent_class = Object.new(class_y.parent)
            # class_object = NewObject(class_y, parent_class)
            # print(f"Created new object of class with these attributes:{new_object.attributes}")
            return self.execute_expression(send.receiver, current_scope)
        if selector == "from:":
            if not arguments:
                raise InterpreterError(
                    error_code=ErrorCode.INT_INVALID_ARG,
                    message="from: requires a value argument",
                )
            return self.execute_literal_new_from(send.receiver.literal, arguments[0].value)
        # print(f'Arguments for send: {arguments} + Selector: {selector}')
        # print(f'Class_y value: {class_y.value if "value" in dir(class_y) else class_y}')
        # method = class_y.lookup(selector)
        # print(f'method: {method}')
        # print(f'Result value: {result.value if "value" in dir(result) else result}')
        return self.send_message(class_y, selector, arguments, current_scope)

    def eval_expr(self, expr: Expr) -> Any:
        """
        Evaluates an expression and returns it
        """
        if expr.send is not None:
            return self.eval_send(expr.send)
        if expr.literal is not None:
            return self.eval_literal(expr.literal)
        if expr.var is not None:
            return self.eval_var(expr.var)
        if expr.block is not None:
            return expr.block  # return unevaluated, called later by e.g. ifTrue:

        return "Unknown expression type"

    def eval_send(self, send: Send) -> Any:
        """Evaluates send expression and returns a tuple of (receiver, selector, args)."""
        receiver = self.eval_expr(send.receiver)
        selector = send.selector
        args = [self.eval_expr(arg.expr) for arg in send.args]

        return (receiver, selector, args)

    def eval_literal(self, literal: Literal) -> Any:
        """Evaluates literal class and returns its associated value."""
        if literal.class_id == "Integer":
            return int(literal.value)
        if literal.class_id == "String":
            return literal.value
        if literal.class_id == "True":
            return True
        if literal.class_id == "Nil":
            return None
        if literal.class_id == "False":
            return False

        return "Unknown literal class: " + literal.class_id

    def eval_var(self, var: Var) -> Any:
        """Resolve a variable name from the evaluation stack."""
        return self.stack.get(var.name)

    def map_objects(self) -> Any:
        """Return a map of class name to class definition for the loaded program."""
        object_map = {}
        for cls in self.current_program.classes:
            object_map[cls.name] = cls
        return object_map
