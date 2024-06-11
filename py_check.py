import os
import json
import tempfile
import subprocess
import tqdm

def fim_extract(s):
    if "\n" in s:
        s = s[:s.index("\n")]
        s = s.strip()
    if "==" in s:
        s = s[:s.rindex("==")]
        s = s.strip()
        if s[-1] == ")":
            s = s[:-1]
    return s

def chat_extract(s, fn):
    from py_ast_analysis import extract_from_chat
    filling = extract_from_chat(s, fn)
    if filling == "":
        return s.split("\n")[0]
    return filling

def compile_and_run(code):
    temp_dir = tempfile.TemporaryDirectory()
    file_path = os.path.join(temp_dir.name, "temp.py")
    with open(file_path, "w") as f:
        f.write(code)

    try:
        result = subprocess.run(["python3", file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        output = result.stdout.decode("utf-8")
        stderr = result.stderr.decode("utf-8")
    except subprocess.TimeoutExpired:
        temp_dir.cleanup()
        return -1 , "Timeout", "Timeout"

    temp_dir.cleanup()

    return result.returncode, output, stderr

def run(inputfile, outputfile, mode):
    o = open(outputfile, "a")

    with open(inputfile) as f:
        lines = f.readlines()
        for line in tqdm.tqdm(lines):
            d = json.loads(line)
            filling = d["filling"]
            if mode == "fim":
                filling = fim_extract(filling)
            elif mode == "chat":
                fn = d['fn']
                filling = chat_extract(filling, fn)

            content = d['cover']
            content = content.replace("<FILL_ME>", filling)
            code = content
            
            retval, stdout, stderr = compile_and_run(code)

            if retval == 0:
                d['pass'] = True
                d['filling'] = filling
            else:
                d['pass'] = False
                d['filling'] = filling
            o.write(json.dumps(d) + '\n')
            o.flush()

def test():
    code = "assert 1==1"
    rv, output, err = compile_and_run(code)
    assert rv == 0

    code = "assert 1==0"
    rv, output, err = compile_and_run(code)
    assert rv != 0

    code = "abxd"
    rv, output, err = compile_and_run(code)
    assert rv != 0

def main():
    from utils import parse_iofile
    args = parse_iofile()
    run(args.input_path, args.output_path, args.mode)

if __name__ == "__main__":
    # test()
    main()
