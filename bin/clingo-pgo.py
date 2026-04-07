#!/usr/bin/env python3

import os
import pathlib
import sys

import clingo


def run(problem_path: str, *control_files: str):
    control = clingo.Control()
    control.configuration.configuration = "tweety"
    control.configuration.solver.heuristic = "Domain"
    control.configuration.solver.opt_strategy = "usc"

    with open(problem_path, "r") as f:
        problem = f.read()
    control.add("base", [], problem)

    for path in control_files:
        control.load(path)

    control.ground([("base", [])])
    models = []

    def on_model(model):
        models.append((model.cost, model.symbols(shown=True, terms=True)))

    with control.solve(on_model=on_model, async_=True) as handle:
        finished = False
        while not finished:
            finished = handle.wait(1.0)
        solve_result = handle.get()

    if not solve_result.satisfiable:
        print("UNSATISFIABLE")
        sys.exit(1)

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
                        except RuntimeError:
                            _ = str(arg)
            except RuntimeError:
                pass

        for attr in sorted(attrs)[:20]:
            print(attr)


if __name__ == "__main__":
    dir = pathlib.Path(__file__).parent
    run(
        str(dir / "hdf5.lp"),
        str(dir / "concretize.lp"),
        str(dir / "direct_dependency.lp"),
        str(dir / "heuristic.lp"),
        str(dir / "libc_compatibility.lp"),
    )
