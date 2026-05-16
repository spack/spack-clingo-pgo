#!/usr/bin/env python3

import importlib
import pathlib
import sys

import clingo

# clingo 6 (the wip-20 rewrite) split the module into submodules and dropped the
# top-level Control / configuration API. Detect it the same way Spack's solver
# does (spack/lib/spack/spack/solver/core.py: clingo_v6()).
CLINGO_V6 = not hasattr(clingo, "Control")


def make_control():
    """Create a Control configured with the tweety/Domain/usc settings, for
    either the legacy clingo API or the clingo 6 (wip-20) API."""
    if CLINGO_V6:
        library = importlib.import_module("clingo.core").Library()
        # clingo 6 moves solver configuration to command-line options, and its
        # grounder no longer implicitly projects anonymous variables occurring
        # only in negative literals -- the corpus relies on that projection.
        options = [
            "--project-anonymous",
            "--configuration=tweety",
            "--heuristic=Domain",
            "--opt-strategy=usc",
        ]
        return importlib.import_module("clingo.control").Control(library, options)

    control = clingo.Control()
    control.configuration.configuration = "tweety"
    control.configuration.solver.heuristic = "Domain"
    control.configuration.solver.opt_strategy = "usc"
    return control


def add_program(control, problem, control_files):
    """Feed the problem string and the control program files to the Control."""
    if CLINGO_V6:
        control.parse_string(problem)
        control.parse_files(list(control_files))
    else:
        control.add("base", [], problem)
        for path in control_files:
            control.load(path)


def run(problem_path: str, *control_files: str):
    control = make_control()

    with open(problem_path, "r") as f:
        problem = f.read()
    add_program(control, problem, control_files)

    control.ground([("base", [])])
    models = []

    def on_model(model):
        models.append((model.cost, model.symbols(shown=True, terms=True)))

    solve_result = control.solve(on_model=on_model)

    if not solve_result.satisfiable:
        print("UNSATISFIABLE")
        sys.exit(1)

    # Exercise the statistics accessor.
    if CLINGO_V6:
        _ = control.stats.nestify()
    else:
        _ = control.statistics

    if models:
        min_cost, best_model = min(models)
        print(f"Cost: {min_cost}")
        print(f"Symbols: {len(best_model)}")

        # Exercise symbol accessors
        attrs = []
        for sym in best_model:
            try:
                name = sym.name
                args = sym.arguments
                if name == "attr":
                    entry = tuple(
                        (
                            arg.string
                            if hasattr(arg, "string") and arg.string
                            else str(arg)
                        )
                        for arg in args
                    )
                    attrs.append(entry)
                else:
                    for arg in args:
                        try:
                            _ = arg.string
                        except (RuntimeError, ValueError):
                            _ = str(arg)
            except (RuntimeError, ValueError):
                pass

        for attr in sorted(attrs)[:20]:
            print(attr)


if __name__ == "__main__":
    share = pathlib.Path(__file__).parent.parent / "share"
    run(
        str(share / "hdf5.lp"),
        str(share / "concretize.lp"),
        str(share / "direct_dependency.lp"),
        str(share / "heuristic.lp"),
        str(share / "libc_compatibility.lp"),
    )
