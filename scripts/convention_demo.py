"""Run two real Codex-authored orders repairs against the same S1 contract."""
from pathlib import Path
import shutil
import tempfile
from reproduce import ROOT, copy_base, python_in, run_tests, differences, compliance, write
from scenario_repairs import replace
from uplift.diff import git_apply


def main():
    output = ROOT / 'docs/convention-demo'; output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='uplift_conventions_') as directory:
        root = Path(directory)
        original = root / 'original'; copy_base(original)
        git_apply(original, ROOT / 'sample-app/scenarios/s1-null-user.patch')
        proofs = original / 'tests/uplift_proofs'; proofs.mkdir()
        source = ROOT / 'scenarios/s1-null-user/proofs/test_orders_create_order_unknown_user.py'
        shutil.copy2(source, proofs / source.name)
        variants = {
            'generic': "        if get_user(data.user_id) is None:\n            from shop.errors import ValidationError as InvalidOrder\n            raise InvalidOrder('unknown user')",
            'convention-aware': "        if get_user(data.user_id) is None:\n            raise NotFoundError('user', data.user_id)",
        }
        for label, code in variants.items():
            tree = root / label; shutil.copytree(original, tree)
            replace(tree, 'shop/orders/service.py', '        get_user(data.user_id)', code)
            result = run_tests(python_in('sample-app/.venv311'), tree, ['tests/orders', 'tests/uplift_proofs/' + source.name], output, label)
            if result['exitCode']:
                raise RuntimeError(label + ' did not preserve the contract')
            diff, _, added = differences(original, tree)
            (output / (label + '.diff')).write_text(diff, encoding='utf-8', newline='\n')
            write(output / (label + '-compliance.json'), compliance(tree, added))
    (output / 'README.md').write_text('''# Convention-aware repair comparison

Both variants are actual Codex-authored repairs of create_order on the same
isolated S1 patch. Both run the orders suite and unchanged unknown-user proof.
See generic.json and convention-aware.json for measured counts and commands.
These are not IBM Bob task runs, and neither patch is claimed to have been
produced by a separate agent or a parallel worker.

The generic repair imports an aliased domain exception inside the function.
It preserves behavior, but violates the observed module-level import convention.
The convention-aware repair reuses the existing NotFoundError import and the
existing translation to ValidationError. It adds no import or exception alias.
Both preserve the 422 unknown-user contract. Added lines are checked for naming,
absolute/module-level imports, and typed raises. Generic has one violation;
convention-aware has none. No retry was required for the accepted variant.

Reproduce: engine/.venv/Scripts/python scripts/convention_demo.py (Windows).
Use engine/.venv/bin/python on POSIX.
''', encoding='utf-8')


if __name__ == '__main__':
    main()
