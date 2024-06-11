import sys
import os
import re
import subprocess
from termcolor import colored
from subprocess import Popen, call, PIPE
import argparse
import csv
import time
import signal
import json
import tqdm
import tempfile
import shutil
from utils import load_data, dump_data
import concurrent.futures

timeout = 300

klee_path = "/usr/local/bin/klee"

def execute_with_rv(cmd, env={}):
    p = subprocess.Popen(cmd.split(' '), stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    try:
        stdout, stderr = p.communicate()
        return p.wait()
    except:
        print("Command execution timed out.")
        return -1

def timeout_execute(cmd, timeout, env={}):
    p = subprocess.Popen(cmd.split(' '), stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    signal.signal(signal.SIGALRM, lambda signum, frame: p.kill())

    try:
        signal.alarm(timeout)
        stdout, stderr = p.communicate()
        rt_value = p.wait()
        signal.alarm(0)
        if rt_value != 0:
            return rt_value, stderr.decode()
        return rt_value, stdout.decode()
    except:
        print("Command execution timed out.")
        return -1, "timeout"

def compile(file, out, mode):
    lib_path = '../klee/build/lib/'
    libcxx_include = "../klee/libcxx/libc++-install-140/include"
    libcxx_lib_dir = "../klee/libcxx/libc++-install-140/lib"
    libcxxabi_include = "../klee/libcxx/llvm-140/libcxxabi/include"
    libcxxabi_lib_dir = "../klee/libcxx/libc++-install-140/lib/x86_64-unknown-linux-gnu/"

    print(colored('[+] Compiling ...', 'green'))

    if mode == "bc":
        flags = f"-stdlib=libc++ -emit-llvm -c -g -O0 -Xclang -disable-O0-optnone -o {out} -I {libcxx_include} -I {libcxxabi_include}"
        cmd = f"clang++ {flags} {file}"
    elif mode == "bin":
        flags = f"-stdlib=libc++ -g -O0 -Xclang -disable-O0-optnone -o {out} -I {libcxx_include} -I {libcxxabi_include} -lkleeRuntest "
        flags += f"-L{libcxx_lib_dir} -L{libcxxabi_lib_dir} -L{lib_path}"
        cmd = f"clang++ {flags} {file}"
    print(cmd)

    env = os.environ 
    env.update({"LD_LIBRARY_PATH" : lib_path + ":" + libcxx_lib_dir + ":" + libcxxabi_lib_dir})

    p = Popen(cmd.split(' '), stdout=PIPE, stderr=PIPE, env=env)

    stdout, stderr = p.communicate()
    rt_value = p.wait()
    if rt_value != 0:
        print(colored('[+] Compiling error', 'red'))
        print(stderr)
        return False, stderr
    return True, stdout

def run_one(file, outdir):
        cmd = f"{klee_path} -libc=uclibc --libcxx --posix-runtime --max-time={timeout}s -exit-on-error-type=Assert --output-dir={outdir} {file}"
        return cmd

def check(outdir):
    for file in os.listdir(outdir):
        if file.endswith(".assert.err"):
            return True
    return False

def pipeline(data):
    code = data['code']
    temp_dir =  tempfile.TemporaryDirectory()
    infile = os.path.join(temp_dir.name, "a.cpp")
    bcfile = os.path.join(temp_dir.name, "a.bc")
    binfile = os.path.join(temp_dir.name, "a.out")
    outdir = os.path.join(temp_dir.name, "klee_out")
    with open(infile,"w") as f:
        f.write(code)
    ok, output = compile(infile, bcfile, "bc")
    if not ok:
        print("Compile to bitcode failed")
        # shutil.rmtree(temp_dir.name)
        data['pass'] = False
        return data
    ok, output = compile(infile, binfile, "bin")
    if not ok:
        print("Compile to binary failed")
        # shutil.rmtree(temp_dir.name)
        data['pass'] = False
        return data
    
    cmd = run_one(bcfile, outdir)
    execute_with_rv(cmd)
    result = check(outdir)
    # shutil.rmtree(temp_dir.name)
    data['pass'] = result
    return data

def co_run(infile, outfile):
    data = load_data(infile)
    with concurrent.futures.ThreadPoolExecutor(max_workers=32) as executor:
        futures = [executor.submit(pipeline, d) for d in data]
        for future in tqdm.tqdm(futures):
            result = future.result()
            for idx, d in enumerate(data):
                if d['code'] == result['code']:
                    if "pass" not in d:
                        d['pass'] = False
                    data[idx]['pass'] = d['pass']
    dump_data(data, outfile)

def test():
    code = """#include<stdio.h>
#include<math.h>
#include<vector>
#include<algorithm>
using namespace std;
#include<stdlib.h>
vector<int> get_odd_collatz(int n){
    vector<int> out={1};
    while (n!=1)
    {
            if (n%2==1) {out.push_back(n); n=n*3+1;}
        else n=n/2;
    }
    sort(out.begin(),out.end());
    return out;
}

#undef NDEBUG
#include<assert.h>
bool issame(vector<int> a,vector<int>b){
        if (a.size()!=b.size()) return false;
    for (int i=0;i<a.size();i++)
    {
        if (a[i]!=b[i]) return false;
    }
    return true;
}


#include "klee/klee.h"
int main(){
    int s_0;
    klee_make_symbolic(&s_0, sizeof(s_0), "s_0");

    auto result = get_odd_collatz(s_0);
    klee_assert(!(issame(result,{1,3,5})));

}"""
    assert pipeline({"code":code})["pass"]

if __name__ == "__main__":
    #test()
    co_run("gpt_gen_klee_harness.jsonl", "gpt_gen_klee_result.jsonl")