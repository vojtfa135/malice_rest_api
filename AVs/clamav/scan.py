#!/bin/python3

import clamd
import argparse


def parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample")
    return parser


class ClamAV():
    def __init__(self):
        cd = clamd.ClamdUnixSocket()

    def scan(self, sample):
        return cd.scan(sample)


def main():
    args = parser().parser_args()
    clamav = ClamAV()
    print(clamav.scan(args.sample))


if __name__ == "__main__":
    main()
