import os
import string
import sys
import json


from tree_sitter import Language, Parser
from utils import load_data, dump_data

CPP_LANGUAGE = Language("./tree-sitter-cpp.so", "cpp")

parser = Parser()
parser.set_language(CPP_LANGUAGE)

MAX_ARRAY_MEMBER = 8
MAX_STRING_LEN = 16

def limit(max_array_member, max_string_len):
    MAX_ARRAY_MEMBER = max_array_member
    MAX_STRING_LEN = max_string_len

def getcodefromsrc(s, start, end):
    lines = s.split("\n")
    if start[0] == end[0]:
        return lines[start[0]][start[1]:end[1]]
    else:
        # just return the full lines
        return "\n".join(lines[start[0]:end[0]+1])

def parse_focal_method(src):
    tree = parser.parse(src.encode('utf-8'))
    root = tree.root_node
    for child in root.children:
        if child.type == "function_definition":
            fn_node = child
            typ_node = fn_node.child_by_field_name("type")
            declarator = fn_node.child_by_field_name("declarator")
            fname_node = declarator.child_by_field_name("declarator")
            plist_node = declarator.child_by_field_name("parameters")
            paras = getcodefromsrc(src, plist_node.start_point, plist_node.end_point)
            fn = getcodefromsrc(src, fname_node.start_point, fname_node.end_point)
            typ = getcodefromsrc(src, typ_node.start_point, typ_node.end_point)
    return fn, paras, typ

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
    if node.type == "call_expression":
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

def find_assert(src ,target, tree):
    result = []
    root = tree.root_node
    for node in root.children:
        if node.type == 'function_definition':
            func_def = node
            fn = func_def.child_by_field_name("declarator").child_by_field_name("declarator")
            if getcodefromsrc(src, fn.start_point, fn.end_point) == "main":
                for node in func_def.child_by_field_name("body").children:
                    if node.type == "expression_statement" and  node.child(0).type == "call_expression":
                        cond = node.child(0).child(1)
                        call = dfs(cond ,src, target)
                        v = cond
                        if call is not None:
                            raw = getcodefromsrc(src, v.start_point, v.end_point)
                            new = raw.replace(getcodefromsrc(src, call.start_point, call.end_point), "result")
                            new = new.replace(" ", "")
                            result.append(new)
    return list(set(result))

def get_function_by_name(src, name):
    tree = parser.parse(src.encode("utf-8"))
    root = tree.root_node
    for node in root.children:
        if node.type == 'function_definition':
            func_def = node
            func_decl = node.child_by_field_name("declarator").child_by_field_name("declarator")
            fn = getcodefromsrc(src, func_decl.start_point, func_decl.end_point)
            if fn == name:
                return getcodefromsrc(src, func_def.start_point, func_def.end_point)
    return None

def cut_off_main_function(src, tree):
    result = src
    root = tree.root_node
    for node in root.children:
        if node.type == 'function_definition':
            func_def = node
            fn = func_def.child_by_field_name("declarator").child_by_field_name("declarator")
            if getcodefromsrc(src, fn.start_point, fn.end_point) == "main":
                main = getcodefromsrc(src, func_def.start_point, func_def.end_point)
    return src.replace(main, "")

def find_focal_method(src):
    tree = parser.parse(src.encode("utf-8"))
    root = tree.root_node
    for child in root.children:
        if child.type == "function_definition":
            return getcodefromsrc(src, child.start_point, child.end_point)


def focal_method_name(src):
    tree = parser.parse(src.encode("utf-8"))
    root = tree.root_node
    for child in root.children:
        if child.type == "function_definition":
            rtype = child.child_by_field_name("type")
            declarator = child.child_by_field_name("declarator")
            fn = declarator.child_by_field_name("declarator")
            focal_method_name = getcodefromsrc(src, fn.start_point, fn.end_point)
            return focal_method_name

def find_literal_in_args(callsite):
    tree = parser.parse(callsite.encode("utf-8"))
    root = tree.root_node
    call = root.child(0).child(0)
    result = []
    def find_literal(node):
        if node.type == "string_literal" or node.type == "number_literal":
            result.append({"type":node.type, "pos":[node.start_point, node.end_point]})
            return
        if node.child_count == 0:
            return
        for c in node.children:
            find_literal(c)
    
    find_literal(call)
    return result  
            

def symbolic_value_definition(src, asserts):
    tree = parser.parse(src.encode("utf-8"))
    root = tree.root_node
    for child in root.children:
        if child.type == "function_definition":
            rtype = child.child_by_field_name("type")
            declarator = child.child_by_field_name("declarator")
            fn = declarator.child_by_field_name("declarator")
            focal_method = getcodefromsrc(src, fn.start_point, fn.end_point)
            parameters = declarator.child_by_field_name("parameters")
            paras = filter(lambda x : x.type == "parameter_declaration", parameters.children)
            paras = [x.child_by_field_name("type") for x in paras]
            para_types = [getcodefromsrc(src, x.start_point, x.end_point) for x in paras]
            return template(para_types, asserts, focal_method)

def dispatch_var(p,cnt, prefix="s"):
    if p.startswith("vector"):
        return vector_var(p, cnt, prefix)
    elif p.startswith("map"):
        return map_var(p, cnt, prefix)
    else:
        return simple_var(p, cnt, prefix)

def simple_var(p,cnt, prefix=""):
    global vars
    name = f"{prefix}_{cnt}"
    if p == "string":
        vars += f"\tchar chr_{name}[{MAX_STRING_LEN}];\n"
        vars += f"\tklee_make_symbolic(chr_{name}, sizeof(chr_{name}), \"chr_{name}\");\n"
        vars += f"\t{p} {name}(chr_{name});\n"
    else:
        vars += f"\t{p} {name};\n"
        vars += f"\tklee_make_symbolic(&{name}, sizeof({name}), \"{name}\");\n"
    return f"{name}"

def vector_var(p, cnt, prefix=""):
    global vars
    element_type = p[p.index("<")+1:p.rindex(">")]
    elements = []
    name = f"{prefix}_vec_{cnt}"
    vars += "\n"
    for i in range(MAX_ARRAY_MEMBER):
        this_prefix = name + "_m"
        elements.append(dispatch_var(element_type, i, this_prefix))
    s = "{" + ",".join(elements) + "}"
    vars += f"\t{p} {name} = {s};\n" 
    return name

def map_var(p, cnt, prefix=""):
    global vars
    element_types = p[p.index("<")+1:p.rindex(">")].split(",")
    elements = {}
    name = f"{prefix}_map_{cnt}"
    vars += "\n"
    for i in range(MAX_ARRAY_MEMBER):
        key_prefix = name + "_k"
        value_prefix = name + "_v"
        key = dispatch_var(element_types[0], i, key_prefix)
        value = dispatch_var(element_types[1], i, value_prefix)
        elements[key] = value
    
    vars += f"\t{p} {name};\n"
    for key in elements:
        vars += f"\t{name}[{key}] = {elements[key]};\n"
    return name

vars = ""

def template(paras, asserts, focal_method) -> [string]:
    global vars
    result = []
    for a in asserts:
        vars = ""
        klee_assert = f"\tklee_assert(!({a}));\n"

        arguments = []
        cnt = 0
        for p in paras:
            arguments.append(dispatch_var(p, cnt))
            cnt += 1

        arguments = "(" + ",".join(arguments) + ")"

        t  = "#include \"klee/klee.h\"\n"
        t += "int main(){\n"
        t += f"{vars}\n"
        t += f"\tauto result = {focal_method}{arguments};\n"
        t += f"{klee_assert}\n"
        t += "}"
        result.append(t)
    return result

def gen_harness_for_klee(outputfile):
    result = []
    raw_data = load_data("./humaneval_cpp.jsonl")
    for data in raw_data:
        code = data['declaration'] + data['canonical_solution']
        task_id = data['task_id']
        tests = data['test']
        tree = parser.parse(tests.encode("utf-8"))
        utils = cut_off_main_function(tests, tree)

        focal_method_def = find_focal_method(data['prompt'])
        asserts = find_assert(tests, focal_method_def, tree)
        
        new_mains = symbolic_value_definition(focal_method_def, asserts)
        assert len(new_mains) == len(asserts)
        for m, a in zip(new_mains, asserts):
            d = {}
            d['task_id'] = task_id
            d['utils'] = utils
            d['code'] = code + '\n' + utils + '\n' +  m
            d['assert'] = a
            result.append(d)
    dump_data(result, outputfile)

def prompt_gpt(focal_method, asserts):
    res = []
    for e in asserts:
        t  = ""
        t += "int main(){\n"
        t += f"\tauto result = {focal_method}(<FILL_ME>);\n"
        t += f"\tassert{e};\n"
        t += "}"
        res.append(t)
    return res


def gen_prompt_for_gpt(outputfile):
    res = []
    cnt = 0
    raw_data = load_data("./humaneval_cpp.jsonl")
    for data in raw_data:
        code = data['declaration'] + data['canonical_solution']
        task_id = data['task_id']
        example_test = data['test'] # example test can be empty, use test instead
        tree = parser.parse(example_test.encode("utf-8"))
        utils = cut_off_main_function(example_test, tree)

        focal_method_def = find_focal_method(data['prompt'])
        asserts = find_assert(example_test, focal_method_def, tree)
        fn, para, typ = parse_focal_method(data['declaration'])
        # print(asserts)

        main_ = prompt_gpt(focal_method_name(focal_method_def), asserts)

        for main_i in main_:
            new_code = code + main_i
            prompt = f"Please fill the arguments tagged with <FILL_ME> to make the assertion success.\n```cpp\n{new_code}\n```"
            cnt += 1
            res.append({"task_id": task_id,"fn":fn, "para":para, "type":typ, "prompt": prompt, "code":new_code, "utils":utils})
    dump_data(res, outputfile)
    print(f"Total {cnt} prompts")

def test():
    global vars
    dispatch_var("vector<int>", 0)
    dispatch_var("map<string, int>", 1)
    dispatch_var("vector<vector<int>>", 2)
    print(vars)

if __name__ == "__main__":
    # test()
    gen_prompt_for_gpt("patheval_cpp.jsonl")
    gen_harness_for_klee("klee_harness.jsonl")