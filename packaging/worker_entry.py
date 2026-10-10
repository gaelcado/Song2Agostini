"""Frozen interpreter dispatcher for the project's existing worker contract."""
import multiprocessing
import runpy
import sys


def main():
    multiprocessing.freeze_support()
    if len(sys.argv) < 3:
        raise SystemExit("Worker requires a script path or -c expression")
    if sys.argv[1] == "-c":
        exec(sys.argv[2], {"__name__": "__main__"})
    else:
        sys.argv = sys.argv[1:]
        runpy.run_path(sys.argv[0], run_name="__main__")


if __name__ == "__main__":
    main()
