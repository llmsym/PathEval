import json
import sys
import os

if len(sys.argv) != 3:
    print("fim.py INPUTFILE OUTPUTFILE")

inputfile = sys.argv[1]
outputfile = sys.argv[2]
assert inputfile.endswith(".jsonl")

with open(inputfile, "r") as f:
    data = [json.loads(line) for line in f.readlines()]
    fim_data = []
    for d in data:
        fim = d['prompt'].replace("Please fill the arguments tagged with FILL_ME to make the assertion success.\n", "")
        fim = "<fim_prefix>" + fim.replace("<FILL_ME>", "<fim_suffix>") + "<fim_middle>"
        d['prompt'] = fim
        fim_data.append(d)

    with open(outputfile, "w") as f:
        for d in fim_data:
            f.write(json.dumps(d)+'\n')