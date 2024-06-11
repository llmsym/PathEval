import json
import logging
import sys
from utils import load_data, dump_data

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='[%(levelname)s]\t%(message)s')

def load_data(file):
    with open(file) as f:
        return [json.loads(line) for line in f.readlines()]

def skip(data, n):
    res = []
    for i, d in enumerate(data):
        if i % n == 0:
            res.append(d)
    return res

def pass_rate(data, n=5):
    cnt = 0
    total = len(data) // n
    logging.debug(f"Total result : {total}")
    for i in range(total):
        ntries = data[i*n:i*n+n]
        res = False
        for one in ntries:
            res = res or one['pass']
        if res: cnt += 1
    logging.debug(f"Pass result : {cnt}")
    return cnt / total

def common(infile):
    data = load_data(infile)
    data1 = skip(data, 5)
    r = pass_rate(data1, 1)
    logging.info(f"pass rate 1 : {r}")
    r = pass_rate(data, 5)
    logging.info(f"pass rate 5 : {r}")
    return


def task_group(data):
    all_task = {}
    for d in data:
        task_id = d['task_id']
        if task_id not in all_task:
            all_task[task_id] = []
        all_task[task_id].append(d)
    return all_task

def task_view(infile):
    prs = []
    data = load_data(infile)
    all_task = task_group(data)
    for task in all_task:
        assert len(all_task[task]) % 5 == 0
        pr = pass_rate(all_task[task])
        prs.append(pr)
    prs = sorted(prs)
    print(prs)
    return prs


def attempt_times(data):
    n = 5
    result = []
    total = len(data) // n
    for i in range(total):
        attempt = 0
        ntries = data[i*n:i*n+n]
        res = False
        for one in ntries:
            res = res or one['pass']
            if not res:
                attempt += 1
        if res:
            result.append(attempt+1)
    counts = {
        1: 0,
        2: 0,
        3: 0,
        4: 0,
        5: 0
    }

    for num in result:
        if 1 <= num <= 5:
            counts[num] += 1

    return counts

def attempts(infile):
    data = load_data(infile)
    r = attempt_times(data)
    for k, v in r.items():
        print(str(v) + ",", end='')


def load_data(file):
    with open(file) as f:
        return [json.loads(line) for line in f.readlines()]

# python only
def with_type(d): 
    para = d['para']
    return ":" in para

def type_view_for_python(infile):
    data =load_data(infile)
    r = pass_rate(data, 5)
    logging.info(f"pass rate : {r}")
    wth = [d for d in data if with_type(d)]
    wthout = [d for d in data if not with_type(d)]
    r = pass_rate(wth, 5)
    logging.info(f"pass rate with type: {r}")
    r = pass_rate(wthout, 5)
    logging.info(f"pass rate without type: {r}")

def is_aggregate(d):
    para = d['para']
    return "vector" in para or "map" in para or "array" in para or "stack" in para or "set" in para

def is_aggregate_rv(d):
    para = d['type']
    return "vector" in para or "map" in para or "array" in para or "stack" in para or "set" in para

def is_string(d):
    para = d['para']
    return "string" in para

def is_string_rv(d):
    para = d['type']
    return "string" in para

def is_float(d):
    para = d['para']
    return "float" in para or "double" in para

def is_float_rv(d):
    para = d['type']
    return "float" in para or "double" in para

def is_multi(d):
    para = d['para']
    return len(para.split(",")) > 1

def is_aggregate_rv(d):
    rv = d['type']
    return "vector" in rv or "map" in rv or "array" in rv or "stack" in rv or "set" in rv

def typ(infile):
    data =load_data(infile)
    r = pass_rate(data, 5)
    logging.info(f"pass rate : {r}")
    wth = [d for d in data if is_aggregate(d)]
    # wthout = [d for d in data if not is_aggregate(d)]
    r = pass_rate(wth, 5)
    logging.info(f"pass rate with aggregate inputs: {r}")
    # r = pass_rate(wthout, 5)
    # logging.info(f"pass rate without aggregate inputs : {r}")

    wth = [d for d in data if is_aggregate_rv(d)]
    r = pass_rate(wth, 5)
    logging.info(f"pass rate with aggregate output: {r}")

    wth = [d for d in data if is_aggregate(d) and is_aggregate_rv(d)]
    # wthout = [d for d in data if not (is_aggregate(d) and is_aggregate_rv(d))]
    r = pass_rate(wth, 5)
    logging.info(f"pass rate with aggregate input and output: {r}")
    # r = pass_rate(wthout, 5)
    # logging.info(f"pass rate without aggregate input and output: {r}")

    wth = [d for d in data if is_aggregate(d) and not is_aggregate_rv(d)]
    # # wthout = [d for d in data if not (not is_aggregate(d) and is_aggregate_rv(d))]
    r = pass_rate(wth, 5)
    logging.info(f"pass rate with aggregate input and not aggregate output: {r}")
    # r = pass_rate(wthout, 5)
    # logging.info(f"pass rate without non-aggregate input and output: {r}")

    wth = [d for d in data if not is_aggregate(d) and  is_aggregate_rv(d)]
    r = pass_rate(wth, 5)
    logging.info(f"pass rate with not aggregate input and aggregate output: {r}")

    wth = [d for d in data if not is_aggregate(d) and not is_aggregate_rv(d)]
    # # wthout = [d for d in data if not (not is_aggregate(d) and is_aggregate_rv(d))]
    r = pass_rate(wth, 5)
    logging.info(f"pass rate with not aggregate input and not aggregate output: {r}")
    # r = pass_rate(wthout, 5)
    # logging.info(f"pass rate without non-aggregate input and output: {r}")

    wth = [d for d in data if is_string(d)]
    # wthout = [d for d in data if not is_string(d)]
    r = pass_rate(wth, 5)
    logging.info(f"pass rate with string inputs: {r}")
    # r = pass_rate(wthout, 5)
    # logging.info(f"pass rate without string inputs : {r}")

    wth = [d for d in data if is_string_rv(d)]
    # wthout = [d for d in data if not is_string(d)]
    r = pass_rate(wth, 5)
    logging.info(f"pass rate with string output: {r}")

    wth = [d for d in data if is_float(d)]
    # wthout = [d for d in data if not is_float(d)]
    r = pass_rate(wth, 5)
    logging.info(f"pass rate with floating point inputs: {r}")
    # r = pass_rate(wthout, 5)
    # logging.info(f"pass rate without floating point inputs : {r}")

    wth = [d for d in data if is_float_rv(d)]
    # wthout = [d for d in data if not is_float(d)]
    r = pass_rate(wth, 5)
    logging.info(f"pass rate with floating point output: {r}")

    wth = [d for d in data if is_multi(d)]
    # wthout = [d for d in data if not is_multi(d)]
    r = pass_rate(wth, 5)
    logging.info(f"pass rate with multiple inputs: {r}")
    # r = pass_rate(wthout, 5)
    # logging.info(f"pass rate without multiple inputs : {r}")

import lizard
def complexity(code, fn):
    i = lizard.analyze_file.analyze_source_code("a.cpp", code)
    for func in i.function_list:
        if func.name == fn:
            complexity = func.cyclomatic_complexity
            return complexity
    return None

def comp_view(infile):
    prs = []
    data = load_data(infile)
    all_task = task_group(data)
    for task in all_task:
        assert len(all_task[task]) % 5 == 0
        pr = pass_rate(all_task[task])
        d = all_task[task][0]
        code = d['code']
        fn = d['fn']
        comp = complexity(code, fn)
        prs.append([pr, comp])
    for xy in prs:
        print(f"{xy[0]},{xy[1]}")
            
import argparse

def parse_arg():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input_path", required=True, help="Input file path")
    parser.add_argument("-v", "--view", required=False, help="common | type | attempts | task | comp", default="common")
    args = parser.parse_args()
    return args


def test():
    pass


def main():
    args = parse_arg()
    if args.view == "common":
        common(args.input_path)
    elif args.view == "type":
        typ(args.input_path)
    elif args.view == "type_py":
        type_view_for_python(args.input_path)
    elif args.view == "attempts":
        attempts(args.input_path)
    elif args.view == "task":
        task_view(args.input_path)
    elif args.view == "comp":
        comp_view(args.input_path)

if __name__ == "__main__":
    main()