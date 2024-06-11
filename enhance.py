import json
from utils import load_data, dump_data
from cpp_ast_analysis import find_literal_in_args, getcodefromsrc, cut_off_main_function

def gen_klee_harness_from_gpt_filling(d):
    filling = d['filling']
    code = d['code']

    fn = d['fn']
    asst = d['assert']
    utils = d['utils']

    call = f"{fn}({filling});"
    literals = find_literal_in_args(call)

    symbolic_var_defn = ""
    symbolic_var_name = []

    for idx, l in enumerate(literals):
        s = getcodefromsrc(call, l['pos'][0], l['pos'][1])

        if l['type'] == "number_literal":
            if "." in s:
                p = "float"
            else:
                n = int(s)
                if n >= 2*31 or n < -2*31:
                    p = "long long"
                else:
                    p = "int"
            defn = f"\t{p} s_{idx};\n"
            defn += f"\tklee_make_symbolic(&s_{idx}, sizeof(s_{idx}), \"s_{idx}\");\n"
        elif l['type'] == "string_literal":
            size = len(s)
            if size < 16:
                size = 16
            p = "string"
            defn = f"\tchar s_{idx}[{size+1}];\n"
            defn += f"\tklee_make_symbolic(s_{idx}, sizeof(s_{idx}), \"s_{idx}\");\n"
        
        symbolic_var_name.append(f"s_{idx}")
        symbolic_var_defn += defn
    
    split_filling = []
    e = 0
    for idx, l in enumerate(literals):
        s = l['pos'][0][1] - len(f"{fn}(")
        split_filling.append(filling[e:s])
        split_filling.append(symbolic_var_name[idx])
        e = l['pos'][1][1] - len(f"{fn}(")
    split_filling.append(filling[e:])
    new_filling = "".join(split_filling)


    klee_assert = f"\tklee_assert(!({asst}));\n"

    t  = "#include \"klee/klee.h\"\n"
    t += "int main(){\n"
    t += f"{symbolic_var_defn}\n"
    t += f"\tauto result = {fn}({new_filling});\n"
    t += f"{klee_assert}\n"
    t += "}"

    lines = code.split("\n")
    new_lines = []
    for line in lines:
        if "int main(){" in line:
            break
        new_lines.append(line)
    new_code = "\n".join(new_lines)

    full_code = new_code + "\n" + utils + "\n" + t

    return full_code


def test():
    res = find_literal_in_args("fn(123);")
    print(res)
    res = find_literal_in_args("fn(123, \"123\");")
    print(res)
    res = find_literal_in_args("fn(vector<int>(1,2,3));")
    print(res)
    res = find_literal_in_args("fn(vector<int>(vector<int>({1,2,3})));")
    print(res)