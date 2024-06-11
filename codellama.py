from transformers import LlamaForCausalLM, CodeLlamaTokenizer
import os
import json
import tqdm
import torch
import transformers
tokenizer = None
model = None

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

def run(infile, outfile):
    global tokenizer
    global model
    tokenizer = CodeLlamaTokenizer.from_pretrained("codellama/CodeLlama-7b-hf")
    model = LlamaForCausalLM.from_pretrained("codellama/CodeLlama-7b-hf", torch_dtype=torch.float16).to("cuda")

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
                d["filling"] = filling
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
