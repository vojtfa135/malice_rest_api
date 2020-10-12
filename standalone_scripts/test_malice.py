import os
import subprocess
import json


def main():
    avs = {
        "clamav": "clamav",
        "comodo": "comodo",
        "escan": "escan",
        "fsecure": "fsecure",
        "mcafee": "mcafee",
        "sophos": "sophos"
    }

    malware_path = "/home/test/unzipped"
    samples = os.listdir(malware_path)

    result = {
        avs["clamav"]: {
            "detected": 0
        },
        avs["comodo"]: {
            "detected": 0
        },
        avs["escan"]: { 
            "detected": 0
        },
        avs["fsecure"]: {
            "detected": 0
        },
        avs["mcafee"]: {
            "detected": 0
        },
        avs["sophos"]: {
            "detected": 0
        }
    }

    # test malware samples

    container_working_dir = "/malware"
    mount = "{}:{}".format(malware_path, container_working_dir)

    for av in avs.values():
        for sample in samples:
            scan = str(subprocess.run(["docker", "run", "-v", mount, av, sample], stdout=subprocess.PIPE).stdout)
            scan = scan.strip("b\'").strip("\\n").strip("\\r")
            print(scan)
            scan_dict = json.loads(scan)
            if scan_dict[av]["infected"]:
                result[av]["detected"] += 1

    # export results
    
    with open("results.json", "w") as f:
        f.write(json.dumps(results))


if __name__ == "__main__":
    main()
