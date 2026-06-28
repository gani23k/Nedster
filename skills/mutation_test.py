# skills/mutation_test.py
import ast, copy, subprocess, tempfile, shutil
from pathlib import Path
from skills.base import NedsterSkill

COMPARISON_FLIPS = {
    ast.Lt: ast.GtE, ast.GtE: ast.Lt, ast.Gt: ast.LtE, ast.LtE: ast.Gt,
    ast.Eq: ast.NotEq, ast.NotEq: ast.Eq,
}

class ComparisonMutator(ast.NodeTransformer):
    """Flips exactly one comparison operator per pass, identified by node index."""
    def __init__(self, target_index: int):
        self.target_index = target_index
        self.current_index = -1
        self.mutated = False

    def visit_Compare(self, node):
        self.generic_visit(node)
        for i, op in enumerate(node.ops):
            if type(op) in COMPARISON_FLIPS:
                self.current_index += 1
                if self.current_index == self.target_index and not self.mutated:
                    node.ops[i] = COMPARISON_FLIPS[type(op)]()
                    self.mutated = True
        return node

def count_mutable_comparisons(tree: ast.AST) -> int:
    count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            count += sum(1 for op in node.ops if type(op) in COMPARISON_FLIPS)
    return count

class MutationTestFile(NedsterSkill):
    name = "mutation_test_file"
    description = "Generate comparison-operator mutants of a source file and check whether the test suite catches each one."
    parameters = {
        "type": "object",
        "properties": {
            "source_path": {"type": "string"},
            "test_command": {"type": "string", "description": "e.g. 'pytest tests/test_x.py -q'"},
        },
        "required": ["source_path", "test_command"],
    }

    async def run(self, source_path: str, test_command: str) -> dict:
        source = Path(source_path).read_text()
        tree = ast.parse(source)
        n_mutants = count_mutable_comparisons(tree)
        if n_mutants == 0:
            return {"status": "no_mutable_operators", "survivors": []}

        survivors = []
        for idx in range(n_mutants):
            mutant_tree = ComparisonMutator(idx).visit(copy.deepcopy(tree))
            ast.fix_missing_locations(mutant_tree)
            mutated_source = ast.unparse(mutant_tree)

            with tempfile.TemporaryDirectory() as tmp:
                shutil.copytree(Path(source_path).parent, tmp, dirs_exist_ok=True)
                mutant_path = Path(tmp) / Path(source_path).name
                mutant_path.write_text(mutated_source)

                result = subprocess.run(
                    test_command.split(), cwd=tmp, capture_output=True, text=True, timeout=60
                )
                # Exit code 0 with a mutated comparison = tests didn't notice = survivor
                if result.returncode == 0:
                    survivors.append({"mutant_index": idx, "kind": "comparison_flip"})

        return {
            "total_mutants": n_mutants,
            "killed": n_mutants - len(survivors),
            "survivors": survivors,
            "mutation_score": round((n_mutants - len(survivors)) / n_mutants, 2) if n_mutants else None,
        }
