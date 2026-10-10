"""Verification-only subprocess. Never prints a reference or full metrics."""
import argparse
from .final_verification import verify_final

parser=argparse.ArgumentParser()
parser.add_argument('directory');parser.add_argument('--reference')
args=parser.parse_args()
verify_final(args.directory,args.reference)
