import os
from subprocess import STDOUT, check_output
import json
import tqdm
import subprocess
import requests
import time
from utils import load_data, dump_data

all_code = []

apikey = os.getenv("APIKEY")

def make_api_request(prompt, retry=0):
    time.sleep(1<<retry)
    if retry > 5:
        print("up to retry limitation, exiting...")
        exit(0)
    url = "https://api.f2gpt.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {apikey}"
    }
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "n":5
    }
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response_json = response.json()
    except requests.exceptions.ConnectionError:
        retry += 1
        return make_api_request(prompt, retry)
    return response_json

def skip(data, outfile):
    if os.path.exists(outfile):
        out = open(outfile, "r")
        exist = len(out.readlines())
        data = data[exist:]
    return data

def run(infile, outfile):
    out = open(outfile, "a")
    data = load_data(infile)
    data = skip(data, outfile)
    for d in tqdm.tqdm(data):
        prompt = d['prompt']
        result = make_api_request(prompt)
        d['gpt_result'] = result
        out.write(json.dumps(d) + "\n")
        out.flush()


import argparse

def parse_arg():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input_path", required=True, help="Input file path")
    parser.add_argument("-o", "--output_path", required=True, help="Output file path")
    args = parser.parse_args()
    return args

args = parse_arg()
run(args.input_path, args.output_path)