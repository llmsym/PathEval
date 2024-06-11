import os
import subprocess
import json
import tempfile
import tqdm
import sys
from utils import parse_iofile, load_data, dump_data
import shutil
from pprint import pprint

task_result = {}

def compile_and_run(code):
    with tempfile.NamedTemporaryFile(suffix='.c', delete=True) as temp_file:
        temp_file.write(code.encode('utf-8'))
        temp_file.flush()

        d = os.path.dirname(temp_file.name)
        hpp = os.path.join(d, "pprint.hpp")
        if not os.path.exists(hpp):
            shutil.copyfile("./pprint.hpp", hpp)

        compile_command = ['clang++', temp_file.name, '-o', 'output', "-lstdc++", "-lm", "-lcrypto", "-std=c++17"]
        compile_process = subprocess.run(compile_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if compile_process.returncode == 0:
            # 运行可执行文件
            run_command = ['./output']
            run_process = subprocess.run(run_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = run_process.stdout.decode('utf-8')
            error = run_process.stderr.decode('utf-8')
            return run_process.returncode, output, error
        else:
            error = compile_process.stderr.decode('utf-8')
            print(error)
            return -1, "compile error", error

from cpp_ast_analysis import parser, dfs, getcodefromsrc
# This function should not be here but keep now
def extract_from_chat(chat, fn):
    target_line = ""
    lines = chat.split("\n")
    for line in lines:
        if fn in line:
            target_line = line
            break
    if target_line != "":
        tree = parser.parse(target_line.encode('utf-8'))
        root = tree.root_node
        call = dfs(root, target_line, fn)
        if call is not None:
            args = call.child_by_field_name("arguments")
            return getcodefromsrc(target_line, args.start_point, args.end_point)[1:-1]
    return ""

def chat_extract(s, fn):
    lines = s.split('\n')

    # by key word in template
    for line in lines:
        if "auto result" in line:
            filling = extract_from_chat(line, fn)
            if filling != "":
                return filling
    
    # by focal method name
    for line in lines:
        if fn in line:
            if '`' in line:
                line = line[line.index("`"):line.rindex("`")]
            filling = extract_from_chat(line, fn)
            if filling != "":
                return filling
    
    # return raw, which is not common for codeqwen
    return s.split('\n')[0]

def fim_extract(s, suffix):
    if suffix in s:
        s = s[:s.index(suffix)]
        return s
    return s.split("\n")[0]

def run_one(d, mode):
    code = d['code']
    fn = d['fn']

    if "utils" in d:
        utils = d['utils']
    else:
        utils = ""
    filling = d['filling']
    filling = filling.strip()
    if mode == "fim":
        suffix_idx = code.index("<FILL_ME>") + len("<FILL_ME>")
        suffix = code[suffix_idx:]
        suffix = suffix.split('\n')[0]
        filling = fim_extract(filling, suffix)
    elif mode == "chat":
        fn = d['fn']
        filling = chat_extract(filling, fn)
    d['filling'] = filling
    
    newcode = "#include \"pprint.hpp\"\n" + code
    newcode = newcode.replace("<FILL_ME>", filling)

    new_lines = []
    for line in newcode.split('\n'):
        if "assert(" in line:
            new_lines += ["\tpprint::PrettyPrinter printer;", "\tprinter.print(result);"]
        else:
            new_lines.append(line)
    newcode = "\n".join(new_lines)

    lines = newcode.split("\n")
    for i in range(len(lines)):
        if "int main" in lines[i]:
            newcode = "\n".join(lines[:i]) + "\n" + utils + "\n".join(lines[i:])
            break

    rv, output, error = compile_and_run(newcode)
    output = output.replace("\n", " ")
    d['filling'] = filling
    d['output'] = output
    d['newcode'] = newcode
    return d

def run(infile, outfile, mode):
    data = load_data(infile)
    o = open(outfile, "a")
    for d in tqdm.tqdm(data):
        dd = run_one(d, mode)
        o.write(json.dumps(dd)+'\n')
        o.flush()
    o.close()
    

def test():
    data = load_data("gpt_response_cpp.jsonl")
    data = data[0:5]
    for d in data:
        dd = run_one(d, "chat")
        print(d["output"])

# test()
args = parse_iofile()
run(args.input_path, args.output_path, args.mode)