import os
from subprocess import STDOUT, check_output
import json
import tqdm
import subprocess

from concurrent.futures import ThreadPoolExecutor, as_completed

all_code = []

def init():
    with open("./humaneval_py_typed.jsonl") as f:
        lines = f.readlines()
        for line in lines:
            d = json.loads(line)
            find_path =  f"def find_path{d['para']}:\n"
            find_path += f"\tassert {d['fn']}{d['arg']} == {d['assert']}"

            code = d['code'] + '\n' + find_path
            d['cover'] = code
            all_code.append(d)
            

def execute_command(cmd, seconds, task):
    cmd = cmd.split(" ")
    try:
        output = check_output(cmd, stderr=STDOUT, timeout=seconds)
        return task, output.decode()
    except:
        return task, "TIMEOUT"

def gen_test(code):
    with open("a.py", "w") as temp_file:
        temp_file.write(code)
    package = "a.find_path"

    cmd = f"crosshair cover {package}"

    try:
        result = subprocess.run(cmd.split(" "), capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            output = result.stdout.strip()
        else:
            print(result.stderr.strip())
            return "Error"
        return output
    except Exception as e:
        print(e)
        return "TIMEOUT"

def gen_check(code, output):
    tc = output.split("\n")

    for a_tc in tc:
        with open("b.py", "w") as temp_file:
            temp_file.write(code + "\n" + a_tc)
            temp_file.flush()

            try:
                result = subprocess.run(["python3", "b.py"], capture_output=True, text=True, timeout=10)
                if "AssertionError" not in result.stderr and result.returncode == 0:
                    return True
                else:
                    pass
            except Exception as e:
                print(e)
    return False

def run():
    init()

    if os.path.exists("crosshair_result.jsonl"):
        os.remove("crosshair_result.jsonl")

    f = open("crosshair_result.jsonl", "a")
    for d in tqdm.tqdm(all_code):
        code = d['cover']
        result = gen_test(code)

        check = False
        if result != "TIMEOUT" and result != "Error":
            check = gen_check(code, result)
            
        d['pass'] = check
        d['testcase'] = result
        f.write(json.dumps(d)+'\n')
        f.flush()
    f.close()
run()