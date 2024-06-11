import os
import subprocess
import json
import tempfile
import tqdm
import sys
import shutil

from java_ast_analysis import parser, dfs, getcodefromsrc
# This function should not be here but keep now
def extract_from_chat(chat, fn):
    target_line = chat
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
        if "if (!(" in line:
            filling = extract_from_chat(line, fn)
            if filling != "":
                return filling

    # by focal method name
    for line in lines:
        if f"s.{fn}" in line:
            if '`' in line:
                line = line[line.index("`"):line.rindex("`")]
            filling = extract_from_chat(line, fn)
            if filling != "":
                return filling
    return s.split('\n')[0]

def compile_and_run(focal_method, main):
    original_dir = os.getcwd()
    temp_dir = tempfile.TemporaryDirectory()
    os.chdir(temp_dir.name)
    with open("./Main.java", "w") as f:
        f.write(main)
    with open("./FocalMethod.java", "w") as f:
        f.write(focal_method)

    class_name = "Main"
    compile_command = ['javac', './Main.java', './FocalMethod.java']
    compile_process = subprocess.run(compile_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if compile_process.returncode == 0:
        # 运行可执行文件
        run_command = ['java', class_name]
        try:
            run_process = subprocess.run(run_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
            output = run_process.stdout.decode('utf-8')
            error = run_process.stderr.decode('utf-8')
            rv = run_process.returncode
        except subprocess.TimeoutExpired:
            os.chdir(original_dir)
            shutil.rmtree(temp_dir.name) 
            return -1 , "Timeout", "Timeout"
    else:
        error = compile_process.stderr.decode('utf-8')
        print(error)
        rv = -1
        output = "compile error"
    os.chdir(original_dir)
    shutil.rmtree(temp_dir.name) 
    return rv, output, error

def fim_extract(s, suffix):
    if suffix in s:
        s = s[:s.index(suffix)]
        return s
    return s.split("\n")[0]

def run(inputfile, outputfile, mode):
    o = open(outputfile, "a")
    with open(inputfile) as f:
        lines = f.readlines()
        for line in tqdm.tqdm(lines):
            d = json.loads(line)
            filling = d["filling"]
            code = d['code']
            main = d['main']
            if mode == "fim":
                suffix_idx = main.index("<FILL_ME>") + len("<FILL_ME>")
                suffix = main[suffix_idx:]
                suffix = suffix.split('\n')[0]
                filling = fim_extract(filling, suffix)
            elif mode == "chat":
                fn = d['fn']
                filling = chat_extract(filling, fn)

            focal_method = code.replace(d['main'], "")

            new_main = main.replace("<FILL_ME>", filling)
            prefix = "import java.util.*;\nimport java.lang.*;\n"
            new_main = prefix + new_main
            
            rv, output, error = compile_and_run(focal_method, new_main)
            if rv == 0:
                d['pass'] = True
                d['testcase'] = filling
            else:
                d['pass'] = False
                d['testcase'] = filling
            o.flush()
            o.write(json.dumps(d)+'\n')

from utils import parse_iofile
args = parse_iofile()
run(args.input_path, args.output_path, args.mode)