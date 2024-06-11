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

def dfs(node, src, target):
    if find_focal_method_call(src, node, target) == True:
        return node
    
    if len(node.children) == 0:
        return None
    
    for child in node.children:
        res = dfs(child, src, target)
        if res is not None:
            return res
    
    return None

def find_focal_method_call(src, node, target):
    if node.type == "call":
        fn = node.child_by_field_name("function")
        if getcodefromsrc(src, fn.start_point, fn.end_point) in target:
            return True
    return False

# This function should not be here but keep now
def extract_from_chat(chat, fn):
    target_line = ""
    lines = chat.split("\n")
    for line in lines:
        if fn in line:
            target_line = line
            break
    if target_line != "":
        target_line = target_line[target_line.index(fn):]
        tree = parser.parse(target_line.encode('utf-8'))
        root = tree.root_node
        call = dfs(root, target_line, fn)
        if call is not None:
            args = call.child_by_field_name("arguments")
            return getcodefromsrc(target_line, args.start_point, args.end_point)[1:-1]
    return ""

def extract_pair(asst):
    tree = parser.parse(asst.encode('utf-8'))
    root = tree.root_node
    if root.child(0).type == "assert_statement":
        cmp_node = root.child(0).child(1)
        if cmp_node.type == "comparison_operator":
            call = cmp_node.child(0)
            oracle = cmp_node.child(2)
            args_node = call.child_by_field_name("arguments")
            return getcodefromsrc(asst, args_node.start_point, args_node.end_point).strip()[1:-1], getcodefromsrc(asst, oracle.start_point, oracle.end_point).strip()
    return None, None

# def getwanted(src):
#     tree = parser.parse(src.encode('utf-8'))
#     if tree.root_node.child(0).child(0).type == "comparison_operator":
#         result_node = tree.root_node.child(0).child(0).child(2)
#         return src[result_node.start_point[1]:result_node.end_point[1]]
#     return None

def assert_filter(src):
    try:
        tree = parser.parse(src.encode('utf-8'))
        cond = tree.root_node.child(0).child(1)
        if cond.type != "comparison_operator":
            return ["True", "False"]
        return [getcodefromsrc(src, cond.child(2).start_point, cond.child(2).end_point).strip()]
    except:
        return None

def gen_prompt_for_gpt(outfile):
    result = []
    with open("./humaneval_py.jsonl", "r") as f:
        lines = f.readlines()
        for line in lines:
            asserts = []
            data = json.loads(line)
            code = data['declaration'] + data['canonical_solution']
            task_id = data['task_id']
            test = data['test'] # example test can be empty, use test instead

            #print(task_id)
            #print(example_test)

            args = []
            for a in test.split("\n"):
                if "assert" in a and a.strip()[0]!='#':
                    a = a.strip()
                    if a.startswith("assert True"):
                        continue
                    res = assert_filter(a)
                    arg, oracle = extract_pair(a)
                    if res == None:
                        continue
                    args.append(arg)
                    asserts.append(oracle)
            
            asserts = list(set(asserts))
            
            fn, para, _ = parse_focal_method(data['declaration'])
            for a in asserts:
                new_code = code +'\n'+f"assert {fn}(<FILL_ME>) == {a}"
                prompt = f"Please fill the arguments tagged with <FILL_ME> to make the assertion success.\n```py\n{new_code}\n```"
                result.append({"task_id":task_id, "fn":fn,"para":para, "arg":args,"prompt":prompt, "assert": a, "code":code})

    dump_data(result, outfile)

gen_prompt_for_gpt("patheval_py.jsonl")