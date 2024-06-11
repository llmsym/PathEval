import os
import sys
import json


from tree_sitter import Language, Parser, Node, Tree

JAVA_LANGUAGE = Language("./tree-sitter-java.so", "java")

parser = Parser()
parser.set_language(JAVA_LANGUAGE)


def getcodefromsrc(s, start, end):
    lines = s.split("\n")
    if start[0] == end[0]:
        return lines[start[0]][start[1]:end[1]]
    else:
        # just return the full lines
        return "\n".join(lines[start[0]:end[0]+1])

def dfs(node, src, target) -> Node:
    if find_focal_method_call(src, node, target) == True:
        return node
    
    if len(node.children) == 0:
        return None
    
    for child in node.children:
        res = dfs(child, src, target)
        if res is not None:
            return res
    
    return None

def find_focal_method_call(src, node, target):
    if node.type == "method_invocation":
        fn = node.child_by_field_name("name")
        if getcodefromsrc(src, fn.start_point, fn.end_point) in target:
            return True
    return False

def find_assert(src ,target, tree):
    result = []
    root = tree.root_node
    focal_method_call = dfs(root, src, target)
    if focal_method_call is not None:
        parent = focal_method_call.parent
        while parent is not None:
            if parent.type == "method_invocation":
                fn = parent.child_by_field_name("name")
                if fn is not None and getcodefromsrc(src, fn.start_point, fn.end_point) == "asList":
                    args = parent.child_by_field_name("arguments")
                    for child in args.children:
                        if child.type != "(" and child.type != "," and child.type != ")":
                            result.append(getcodefromsrc(src, child.start_point, child.end_point))
                    break
                else:
                    parent = parent.parent
            else: 
                parent = parent.parent
    return list(set(result))


def find_focal_method(src):
    tree = parser.parse(src.encode("utf-8"))
    root = tree.root_node
    method = None
    for c in root.children:
        if c.type == "class_declaration":
            body = c.child_by_field_name("body")
            for x in body.children:
                if x.type == "method_declaration":
                    method = x
    if method == None:
        return None, None, None
    name = method.child_by_field_name("name")
    para = method.child_by_field_name("parameters")
    typ = method.child_by_field_name("type")
    n = getcodefromsrc(src, name.start_point, name.end_point)
    t = getcodefromsrc(src, typ.start_point, typ.end_point)
    p = getcodefromsrc(src, para.start_point, para.end_point)
    return t, n, p


def extract(src, focal_method_name):
    tree = parser.parse(src.encode("utf-8"))
    root = tree.root_node

    # s.digits(120) == 1
    if root.child(0).type == "expression_statement":
        cmp = root.child(0).child(0)
        if cmp.type == "binary_expression":
            r = cmp.child_by_field_name("right")
            return getcodefromsrc(src, r.start_point, r.end_point)
    # s.isNested("[[][]]" )
    # s.largestSmallestIntegers(Arrays.asList(-6, -4, -4, -3, -100, 1)).equals(Arrays.asList(Optional.of(-3), Optional.of(1)))
    # Objects.equals(s.filenameCheck("final..txt" ), "No" )
    if root.child(0).child(0).type == "method_invocation":
        call = root.child(0).child(0)
        name = call.child_by_field_name("name")
        obj = call.child_by_field_name("object")
        if getcodefromsrc(src, name.start_point, name.end_point) == focal_method_name:
            return "true"
        if getcodefromsrc(src, name.start_point, name.end_point) == "equals":
            if getcodefromsrc(src, obj.start_point, obj.end_point) == "Objects":
                args = call.child_by_field_name("arguments")
                r = args.child(3)
                return getcodefromsrc(src, r.start_point, r.end_point)
            else:
                args = call.child_by_field_name("arguments")
                return getcodefromsrc(src, args.start_point, args.end_point)
        if getcodefromsrc(src, name.start_point, name.end_point) == "isEmpty":
            return "true"
    
    # !s.isNested("]]]]]]]]" )
    if root.child(0).child(0).type == "unary_expression":
        call = root.child(0).child(0)
        return "false"
    
    return None

def gen_main(src, focal_method_name):
    tree = parser.parse(src.encode("utf-8"))
    root = tree.root_node
    fmc = dfs(root, src, focal_method_name)
    args = fmc.child_by_field_name("arguments")
    args_str = getcodefromsrc(src, args.start_point, args.end_point)
    cond = src.replace(args_str, "(<FILL_ME>)")

    template = """public class Main {
        public static void main(String[] args) {
            Solution s = new Solution();
            if (!(<COND>)) {
                    throw new AssertionError();
            }
    }
}"""
    return template.replace("<COND>", cond)

def gen_prompt_for_gpt():
    res = []
    cnt = 0
    with open("./humaneval_java.jsonl", "r") as f:
        lines = f.readlines()
        for line in lines:
            data = json.loads(line)
            code = data['declaration'] + data['canonical_solution']
            task_id = data['task_id']
            example_test = data['test'] # example test can be empty, use test instead
            tree = parser.parse(example_test.encode("utf-8"))

            typ, name, para = find_focal_method(data['declaration'])
            asserts = find_assert(example_test, name, tree)
            #print(example_test)

            dup = {}
            for a in asserts:
                # print(a)
                result = extract(a, name)
                if result == None:
                    continue
                else:
                    result = result.strip()
                    if result not in dup:
                        dup[result] = a
                        #print(a)
            asserts = dup.values()
            for a in asserts:
                main = gen_main(a, name)
                new_code = code + "\n" + main
                prompt = f"Please fill the arguments tagged with <FILL_ME> to make the assertion success.\n```java\n{new_code}\n```"
                cnt += 1
                res.append({"task_id": task_id, "prompt": prompt, "code":code, "fn":name, "type":typ, "para":para, "main":main})
        with open("./patheval_java.jsonl", "a") as f:
            for e in res:
                f.write(json.dumps(e)+'\n')
        print(f"Total {cnt} prompts")

def test():
    pass

if __name__ == "__main__":
    #test()
    gen_prompt_for_gpt()