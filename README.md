# This repository is for the artifacts of the paper “Towards Understanding the Effectiveness of Large Language Modeling on Directed Test Input Generation”

This repository contains the scripts and data involved in the experiments described in the research paper. The content is intended to be used by the academic community to reproduce the findings and build upon the work. The files have been organized and documented to facilitate accessibility and usability for other researchers.

## Project Structure

### dataset
The original dataset from `HumanEval-X` are split into:
- humaneval_cpp.jsonl
- humaneval_java.jsonl
- humaneval_py.jsonl

All the code related to Abstrat Syntax Tree analysis, including transform scripts to construct our dataset `PathEval` are placed into:
- cpp_ast_analysis.py
- py_ast_analysis.py
- java_ast_analysis.py

We use the following scripts to query LLMs:
- gpt_run.py
- codellama.py
- codeqwen.py
- starcoder.py

The following scripts are used to run constraint-based tools:
- klee_run.py
- crosshair_run.py
- evosuite_run.py

And use the following scripts to check the answer of LLMs:
- cpp_check.py
- java_check.py
- py_check.py

### RQ1 and RQ2

The result of our evaluation are placed under the floder `results`:
- codellama_result_cpp.jsonl   
- codellama_result_py.jsonl 
- codellama_result_java.jsonl  
- gpt_result_cpp.jsonl   
- gpt_result_py.jsonl  
- gpt_result_java.jsonl        
- codeqwen_result_cpp.jsonl  
- codeqwen_result_py.jsonl
- codeqwen_result_java.jsonl       
- starcoder2_result_cpp.jsonl  
- starcoder2_result_py.jsonl
- starcoder2_result_java.jsonl
- klee_result.jsonl
- crosshair_result.jsonl
- evosuite_result.jsonl

The code related to results analysis are placed into:
- data_analysis.py

For example:
``` 
# For Pass Rate:
    python3 .\data_analysis.py -i codellama_result_cpp.jsonl
# For Attempts(LLM only) :
    python3 .\data_analysis.py -i codellama_result_cpp.jsonl -v attempts
# For Input Output Type:  
    python3 .\data_analysis.py -i codellama_result_cpp.jsonl -v type
# For Type Annotation:    
    python3 .\data_analysis.py -i codellama_result_py.jsonl -v type_py
# For Code Group: 
    python3 .\data_analysis.py -i codellama_result_cpp.jsonl -v task
``` 

### RQ3

For our soluation LLMSym, we use the following scripts to conduct feedback shot:
- cpp_executor.py (& pprint.hpp)
- py_executor.py

And using the following scripts to enhance harness:
- typeinfer.py
- enhance.py

The result of LLMSym and the baselines is saved in:

- results/crosshair_result.jsonl
- results/gpt_result_py.jsonl
- results/crosshair_result_typed.jsonl
- results/feedback_shot_result_from_gpt_py.jsonl

- results/klee_result.jsonl.resort
- results/gpt_result_cpp.jsonl
- results/gpt_gen_klee_result.jsonl
- results/feedback_shot_result_from_gpt_cpp.jsonl

You can run the following script to get the result in RQ3:
```
python3 diff.py
```

## Environment Setup

### Setup for Treesitter:
We use tree-sitter to conduct AST analysis on C++, Python and Java.
You can follow the document here to install tree-sitter: https://tree-sitter.github.io/tree-sitter/

Additionally, the following parsers should be clone and build:
https://github.com/tree-sitter/py-tree-sitter

https://github.com/tree-sitter/tree-sitter-cpp

https://github.com/tree-sitter/tree-sitter-java

Follow the document tree-sitter to obtain the ".so" library and put them at under this dir.

### Setup for LLMs

we use `codellama/CodeLlama-7b-hf`, `Qwen/CodeQwen1.5-7B-Chat`, `bigcode/starcoder2-7b` in our evaluation, you can find them all in huggingface, or you can use the corresponding script to download and run the models.

For ChatGPT, you can use our script `gpt_run.py` and set your OpenAI KEY in environ to start query it.

### Setup for Constraint-based Tools.

#### KLEE
We follow this document to manually build KLEE (LLVM 14) with libc++ support: 
https://klee-se.org/build-llvm13/.

You should edit the location of following paths in `klee_run.py` based on your building:
```py
    lib_path = '../klee/build/lib/'
    libcxx_include = "../klee/libcxx/libc++-install-140/include"
    libcxx_lib_dir = "../klee/libcxx/libc++-install-140/lib"
    libcxxabi_include = "../klee/libcxx/llvm-140/libcxxabi/include"
    libcxxabi_lib_dir = "../klee/libcxx/libc++-install-140/lib/x86_64-unknown-linux-gnu/"
```

#### EvoSuite
EvoSuite can be downloaded here : https://www.evosuite.org/
Using `-generateSuiteUsingDSE` to use Dynamic Symbolic Execution to generate test suite.

#### CrossHair

Follow this link install crosshair and generate test by concolic execution: https://crosshair.readthedocs.io/en/latest/cover.html.