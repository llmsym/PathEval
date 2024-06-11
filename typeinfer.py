import os
import sys
import json

import random

import tree_sitter_python as tspython
from tree_sitter import Language, Parser
from utils import load_data, dump_data

PY_LANGUAGE = Language(tspython.language(), "python")

parser = Parser()
parser.set_language(PY_LANGUAGE)


def getcodefromsrc(s, start, end):
    lines = s.split("\n")
    if start[0] == end[0]:
        return lines[start[0]][start[1]:end[1]]
    else:
        # just return the full lines
        return "\n".join(lines[start[0]:end[0]+1])

def parse_assert(src):
    tree = parser.parse(src.encode('utf-8'))
    true_node = tree.root_node.child(0).child(1)
    return src[true_node.start_point[1]:true_node.end_point[1]]

def parse_focal_method(src):
    tree = parser.parse(src.encode('utf-8'))
    root = tree.root_node
    for child in root.children:
        if child.type == "function_definition":
            fn_node = child
            fname_node = fn_node.child_by_field_name("name")
            plist_node = fn_node.child_by_field_name("parameters")
            paras = []
            for p in plist_node.children:
                if p.type == "typed_parameter":
                    paras.append(getcodefromsrc(src, p.child(0).start_point, p.child(0).end_point))
                elif p.type == "identifier":
                    paras.append(getcodefromsrc(src, p.start_point, p.end_point))
                else:
                    pass
            paras = "(" + ",".join(paras) + ")"
            plist = getcodefromsrc(src, plist_node.start_point, plist_node.end_point)
            fn = getcodefromsrc(src, fname_node.start_point, fname_node.end_point)
    return fn, plist, paras

def parse_cons_plist(src):
    tree = parser.parse(src.encode('utf-8'))
    call = tree.root_node.child(0).child(0)
    args_node = []
    if call.type == "call":
        args = call.child_by_field_name("arguments")
        for arg in args.children:
            if arg.type != "(" and arg.type != ")" and arg.type !=",":
                args_node.append(arg)
        
        result = []
        for arg in args_node:
            result.append(src[arg.start_point[1]:arg.end_point[1]])
        return result
    return None

def const2typlst(args):
    lst = []
    # print(args)
    for arg in args:
        try:
            # there may not be nested structures in humaneval
            constant_type = type(eval(arg)).__name__
            if constant_type == "list" or constant_type == "tuple" or constant_type == "dict":
                constant_type == constant_type.capitalize()
                element_type = type(eval(arg + "[0]")).__name__
                constant_type = f"list[{element_type}]"
        except:
            constant_type = ""
        lst.append(constant_type)
    return lst

def getparas(src):
    result = []
    tree = parser.parse(src.encode('utf-8'))
    root = tree.root_node
    for child in root.children:
        if child.type == "function_definition":
            paras = child.child_by_field_name("parameters")
            paras_str = getcodefromsrc(src, paras.start_point, paras.end_point)
            for para in paras.children:
                if para.type == "typed_parameter" or para.type == "identifier":
                    result.append(getcodefromsrc(src, para.start_point, para.end_point))
            return result, paras_str
    return None, None

def addtype(typelst, paras):
    result = []
    for typ, para in zip(typelst, paras):
        if ":" in para:
            result.append(para)
        elif typ != "":
            result.append(f"{para}:{typ}")
    return "(" + ",".join(result) +")"
                

def find_filling(d):
    data = load_data("./gpt_result_py.jsonl")
    fillings = []
    for d2 in data:
        if d2['task_id'] == d['task_id']:
            asst = d2['cover'].split("\n")[-1]
            asst = asst[asst.index("==") + 2:]
            if d['assert'] in asst:
                fillings.append(d2['filling'])
    if len(fillings) > 5:
        fillings = fillings[-5:]
    return fillings

typed_data = []
with open("./path_selection_result.jsonl", "r") as f:
    lines = f.readlines()
    for line in lines:
        data = json.loads(line)
        code = data['code']
        task_id = data['task_id']
        fn = data['fn']

        fillings = find_filling(data)
        assert len(fillings) == 5
        for filling in fillings:
            call = f"{fn}({filling})"
            cons = parse_cons_plist(call)
            if cons != None:
                typelist = const2typlst(cons)
                paras, old_paras_str = getparas(data['code'])
                if paras != None:
                    new_paras_str = addtype(typelist,paras)
                    new_code = "from typing import List, Tuple, Dict\n" + data['code']
                    data['code'] = new_code
                    data['para'] = new_paras_str
            typed_data.append(json.dumps(data))
with open("humaneval_py_typed.jsonl", "w") as f:
    f.write("\n".join(typed_data) + "\n")