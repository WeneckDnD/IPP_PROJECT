"""
This module contains the main logic of the interpreter.

IPP: You must definitely modify this file. Bend it to your will.

Author: Ondřej Ondryáš <iondryas@fit.vut.cz>
Author: Tadeas Bujdoso <xbjdot00>
"""

import logging
from pathlib import Path
from typing import TextIO

from lxml import etree
from lxml.etree import ParseError
from pydantic import ValidationError

from interpreter.error_codes import ErrorCode
from interpreter.exceptions import InterpreterError
from interpreter.input_model import *

from .classes import *
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
    
    def create_parent_by_type(self, obj_type: str, value= None) -> any:
        # print(f'value to create {value}')
        match obj_type:
            case "int":
                return Integer.new(value if value is not None else 0)
            case "str":
                return String.new(value if value is not None else "")
            case "None":
                return Nil.new()
            case "bool":
                return True_.new() if value is not None and value == True else False_.new()


    def send_message(self, receiver: NewObject, selector: str, args: list, scope: Scope):
        # print(f'DIR Receiver: {dir(receiver)}')
        # print(f'Receiver: {receiver}, Selector: {selector}')
        method = receiver.lookup(selector, self.current_program.classes)
        # print(f'Method: {method}')  
        # built-in vs user-defined
        if callable(method):
            isParam = selector in receiver.param_foos and method is not None
            print(f'isParam {isParam}')
            new_value = method(*args) if isParam else method()
            print(f'New value: {new_value}')
            value_type = type(new_value).__name__
            # print(f'Value type: {value_type}')
            new_parent = self.create_parent_by_type(value_type, new_value)
            # print(f'New parent: {new_parent}')
            return NewObject(None, new_value, new_parent)
        else:
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
        # print(main_class_def)
        parent_class_str = self.find_parent(main_class_def.parent)
        parent_class = self.create_obj_by_type(parent_class_str)
        scope.set_variable("self", NewObject(main_class_def,None, parent_class))

        main_class = None
        for cls in self.current_program.classes:
            if cls.name == "Main":
                main_class = cls
                break
        if not main_class:
            raise InterpreterError(
                error_code=ErrorCode.SEM_MAIN, message="No Main class found in the program"
            )

        run_method = None
        for mthd in main_class.methods:
            if mthd.selector == "run":
                run_method = mthd
                break
        if not run_method:
            raise InterpreterError(
                error_code=ErrorCode.SEM_MAIN, message="No run method found in the Main class"
            )

        self.execute_method(run_method, scope, [])

    def execute_method(self, method: Method, parent_scope: Scope, args: list) -> Any:
        # arity ?
        # find block
        # execute the block (execute_block)
        # block_arity = method.block.arity # TODO
        if method is not None:
            return self.execute_block(method.block, parent_scope, args)
        raise InterpreterError(error_code=ErrorCode.INT_DNU, message="method not found")

    def execute_block(self, block: Block, parent_scope: Scope, args: list) -> Any:
        current_scope = Scope(parent=parent_scope)

        for param in block.parameters:
            param_name = param.name
            param_value = args[param.order - 1]
            print(f'PARAM NAME: {param_name} PARAM VALUE: {param_value}')
            current_scope.set_variable(param_name, param_value)
        # self.scope.set_variable()
        retValue = None
        for assgn in block.assigns:
            assgn_target = assgn.target  # o
            print(f"Assign target: {assgn_target.name}")
            assgn_expr = assgn.expr
            exp = self.execute_expression(assgn_expr, current_scope)  # NewObject()
            print(f"Assign expr: {exp}")
            current_scope.set_variable(assgn_target.name, exp)
            # look_up = exp.lookup("foo")
            # print(look_up)
            # self.execute_block(look_up.block, current_scope)
            retValue = exp
        return retValue
    
    def execute_params():
        pass



    def execute_expression(self, expr: Expr, current_scope: Scope) -> Any:
        if expr.send is not None:
            # print(f"SEND")
            return self.execute_send(expr.send, current_scope)
        if expr.literal is not None:
            # print(f"LITERAL")
            return self.execute_literal_new(expr.literal)
        if expr.var is not None:
            # print(f"VARIABLE")
            x = current_scope.get_variable(expr.var.name)
            # print(f"value: {x}")
            return x

    def execute_literal(self, literal: Literal) -> Any:
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

    def execute_literal_new(self, literal: Literal) -> Any:
        if literal.class_id == "Integer":
            value = int(literal.value)
            parent_class = Integer.new(value)
            new_integer_class = NewObject(None, value, parent_class)
            return new_integer_class
        if literal.class_id == "String":
            value = literal.value
            parent_class = String.new(value)
            new_string_class = NewObject(None, value, parent_class)
            return new_string_class
        if literal.class_id == "True":
            value = True
            parent_class = True_.new()
            new_true_class = NewObject(None, value, parent_class)
            return new_true_class
        if literal.class_id == "False":
            value = False
            parent_class = False_.new()
            new_false_class = NewObject(None, value, parent_class)
            return new_false_class
        if literal.class_id == "Nil":
            value = None
            parent_class = Nil.new()
            new_nil_class = NewObject(None, value, parent_class)
            return new_nil_class
        if literal.class_id == "class":
            class_def = self.find_class(literal.value)
            parent_class_str = self.find_parent(literal.value)
            parent_class = self.create_obj_by_type(parent_class_str)
            print(parent_class, parent_class_str)
            new_class = NewObject(class_def, None, parent_class)
            return new_class
        

    def create_obj_by_type(self, obj_type: str, *value) -> any:
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
        for cls in self.current_program.classes:
            if cls.name == class_name:
                return cls
        # print(f'NONE {cls} ')
        return None

    def execute_send(self, send: Send, current_scope: Scope) -> Any:
        selector = send.selector  # foo
        arguments = []  
        for arg in send.args:
            order = arg.order
            print(f'ORDER: {order}')
            exp_arg = self.execute_expression(arg.expr, current_scope)
            arguments.append(exp_arg)
        print(f'ARGUMETS: {arguments}')
        class_y = self.execute_expression(send.receiver, current_scope)  # object

        # print(f"Executing send: selector={selector}, arguments={arguments}")

        # TODO: Call dedicated methods according to current Class ( Integer, String, Object, Nil etc )
        # - function to find out if current selector is build-in or not for the current Parent Class
        if selector == "new":
            class_y = self.execute_expression(send.receiver, current_scope)
            # return self.send_message(class_y, selector, arguments, current_scope)
            # parent_class = Object.new(class_y.parent)
            # class_object = NewObject(class_y, parent_class)
            # print(f"Created new object of class with these attributes:{new_object.attributes}")
            return class_y
        # print(f'Arguments for send: {arguments} + Selector: {selector}')
        # print(f'Class_y value: {class_y.value if "value" in dir(class_y) else class_y}')
        result = self.send_message(class_y, selector, arguments, current_scope)
        # method = class_y.lookup(selector)
        # print(f'method: {method}')
        # print(f'Result value: {result.value if "value" in dir(result) else result}')
        return result

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
        return self.stack.get(var.name)

    def map_objects(self) -> Any:
        object_map = {}
        for cls in self.current_program.classes:
            object_map[cls.name] = cls
        return object_map
