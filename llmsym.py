import json
from utils import load_data, dump_data
import argparse


def fail_index(data, n):
    fail_idx = []
    for idx in range(len(data)//n):
        d = data[idx*n]
        d_pass = False
        for j in range(n):
            d = data[idx*n+j]
            d_pass = d_pass or d['pass']
        if not d_pass:
            fail_idx.append(idx)
    return fail_idx

def succ_index(data, n):
    succ_idx = []
    for idx in range(len(data)//n):
        d = data[idx*n]
        d_pass = False
        for j in range(n):
            d = data[idx*n+j]
            d_pass = d_pass or d['pass']
        if d_pass:
            succ_idx.append(idx)
    return succ_idx

def mapidx(data1, data2):
    idxmap = []
    for d in data1:
        for idx, dd in enumerate(data2):
            if d['task_id'] == dd['task_id'] and d['assert'] == dd['assert']:
                idxmap.append(idx//5)
                break
    assert len(idxmap) == len(data1)
    return idxmap

data1 = load_data("results/crosshair_result.jsonl")
data2 = load_data("results/gpt_result_py.jsonl")
data3 = load_data("results/crosshair_result_typed.jsonl")
data4 = load_data("results/feedback_shot_result_from_gpt_py.jsonl")
crosshair_pass = set(succ_index(data1,1))
crosshair_typed_pass = set(succ_index(data3,5))
gpt_pass = set(succ_index(data2, 5))
gpt_pass_few_shot = set(succ_index(data4, 5))

print("PathEval Python")
print("LLMSym : " + str(len(crosshair_pass |  crosshair_typed_pass | gpt_pass | gpt_pass_few_shot)))
print( "LLMSym-E : " + str(len(crosshair_pass | gpt_pass | gpt_pass_few_shot)))
print( "LLMSym-F : " + str(len(crosshair_pass |  crosshair_typed_pass | gpt_pass)))
print( "LLMSym-EF : " + str(len(crosshair_pass| gpt_pass )))
print()


data1 = load_data("results/klee_result.jsonl.resort")
data2 = load_data("results/gpt_result_cpp.jsonl")
data3 = load_data("results/gpt_gen_klee_result.jsonl")
data4 = load_data("results/feedback_shot_result_from_gpt_cpp.jsonl")
klee_pass = set(succ_index(data1,5))
klee_harness_pass = set(succ_index(data3,5))
gpt_pass = set(succ_index(data2, 5))
gpt_pass_few_shot = set(succ_index(data4, 5))

klee_harness_idx_map = mapidx(data3, data1)
klee_harness_pass_mapped = []
for idx in klee_harness_pass:
    true_idx = klee_harness_idx_map[idx*5]
    klee_harness_pass_mapped.append(true_idx)

print("PathEval C++")
print("LLMSym : " + str(len(klee_pass |  klee_harness_pass | gpt_pass | gpt_pass_few_shot)))
print( "LLMSym-E : " + str(len(klee_pass | gpt_pass | gpt_pass_few_shot)))
print( "LLMSym-F : " + str(len(klee_pass |  klee_harness_pass | gpt_pass)))
print( "LLMSym-EF : " + str(len(klee_pass| gpt_pass )))
print()
