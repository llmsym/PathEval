import json
import os
import json
import tqdm
import torch
import transformers
from transformers import AutoModelForCausalLM, AutoTokenizer

def trans_prompt():
    with open("internal/codellama_prompt.jsonl") as f:
        raw = [json.loads(x) for x in f.readlines()]
    
    def trans(x):
        prompt = x['cover'].replace("<FILL_ME>", "<fim_suffix>")
        prompt = "<fim_prefix>" + prompt + "<fim_middle>"
        x['prompt'] = prompt
        return x

    new = map(trans, raw)
    with open("internal/starcoder2_prompt.jsonl", "a") as f:
        [f.write(json.dumps(x)+'\n') for x in new]


checkpoint = "bigcode/starcoder2-7b"
device = "cuda" # for GPU usage or "cpu" for CPU usage

tokenizer = AutoTokenizer.from_pretrained(checkpoint)
# for multiple GPUs install accelerate and do `model = AutoModelForCausalLM.from_pretrained(checkpoint, device_map="auto")`
model = AutoModelForCausalLM.from_pretrained(checkpoint).to(device)

def ask(prompt):

    input_ids = tokenizer(prompt, return_tensors="pt")["input_ids"].to("cuda")
    generated_ids = model.generate(input_ids,
            do_sample=True,
            temperature=0.1,
            top_p=0.95,
            num_return_sequences=1,
            eos_token_id=tokenizer.eos_token_id,
            max_new_tokens=100)

    filling = tokenizer.batch_decode(generated_ids[:, input_ids.shape[1]:], skip_special_tokens = True)[0]
    return filling

def test():
    prompt = "<fim_prefix>def add2():\n    <fim_suffix>\n    return c<fim_middle>"
    print(ask(prompt))

def run(infile, outfile):
    global tokenizer
    global model

    result_file = open(outfile, "a")

    with open(infile) as f:
        lines = f.readlines()
        for line in tqdm.tqdm(lines):
            d = json.loads(line)
            content = d["prompt"]
            task_id = d["task_id"]
            
            for i in range(5):
                filling = ask(content)
                print(filling)
                d['filling'] = filling
                result_file.write(json.dumps(d)+"\n")
                result_file.flush()


import argparse

def parse_arg():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input_path", required=True, help="Input file path")
    parser.add_argument("-o", "--output_path", required=True, help="Output file path")
    args = parser.parse_args()
    return args

args = parse_arg()
run(args.input_path, args.output_path)
