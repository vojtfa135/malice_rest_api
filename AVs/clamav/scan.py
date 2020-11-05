import argparse
import subprocess


def parser():
    parser = argparse.ArgumentParser(description="Scan malware")
    parser.add_argument("--path", help="Provide path to a file")
    return parser


class ClamAV():

    def __init__(self):
        self.result_template = {"infected": False, "signature": ""}

    def update_definitions(self):
        subprocess.run(["freshclam"], stdout=subprocess.DEVNULL)

    def scan(self, sample):
        scan = str(subprocess.run(["clamscan", "--no-summary",  "-v",  "{}".format(sample)], stdout=subprocess.PIPE).stdout)

        if "FOUND" in scan:
            start = scan.find("{}: ".format(sample)) + len("{}: ".format(sample))
            end = scan.find(" FOUND")
            self.result_template["signature"] = scan[start:end]
            self.result_template["infected"] = True

        return self.result_template


def main():
    args = parser().parse_args()

    clamav = ClamAV()
    clamav.update_definitions()
    print(clamav.scan(args.path))


if __name__ == "__main__":
    main()
