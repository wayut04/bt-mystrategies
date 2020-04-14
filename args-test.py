#!/usr/bin/env python

import argparse

def runmain():
    args = parse_args()

    if args.plot:
        print("plot true")
    else:
        print("plot false")

def parse_args():
    parser = argparse.ArgumentParser(
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--plot',
                        required=False, action='store_true',
                        help='Plot if possible')

    return parser.parse_args()

if __name__ == '__main__':
    runmain()
