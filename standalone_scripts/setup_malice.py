import os
import subprocess


def main():
    avs = {
        "clamav": "clamav",
        "comodo": "comodo",
        "escan": "escan",
        "fsecure": "fsecure",
        "mcafee": "mcafee",
        "sophos": "sophos"
    }

    base_gh_url = "https://github.com/malice-plugins/"
    base_images_repos = {
            avs["clamav"]: "{}{}".format(base_gh_url, avs["clamav"]),
            avs["comodo"]: "{}{}".format(base_gh_url, avs["comodo"]),
            avs["escan"]: "{}{}".format(base_gh_url, avs["escan"]),
            avs["fsecure"]: "{}{}".format(base_gh_url, avs["fsecure"]),
            avs["mcafee"]: "{}{}".format(base_gh_url, avs["mcafee"]),
            avs["sophos"]: "{}{}".format(base_gh_url, avs["sophos"])
    }

    fixed_gh_url = "https://github.com/vojtfa135/malice_rest_api"
    fixed_gh_avs_dir = "AVs"
    fixed_repo_name = "malice_rest_api"

    # download base AV engines

    for url_repo in base_images_repos.values():
        subprocess.call(["git", "clone", "{}.git".format(url_repo)])

    # download fixed AV engine components

    subprocess.call(["git", "clone", "{}.git".format(fixed_gh_url)])

    # move the fixed components to the base AV engines

    for av in avs.values():
        subprocess.call(["mv", "{}/{}/{}/Dockerfile".format(fixed_repo_name, fixed_gh_avs_dir, av), "{}/Dockerfile".format(av)])
        if av in ["clamav", "fsecure"]:
            subprocess.call(["mv", "{}/{}/{}/scan.go".format(fixed_repo_name, fixed_gh_avs_dir, av), "{}/scan.go".format(av)])
        if av == "fsecure":
            subprocess.call(["mv", "{}/{}/{}/update.sh".format(fixed_repo_name, fixed_gh_avs_dir, av), "{}/update.sh".format(av)])

    # build Docker images

    for av in avs.values():
        subprocess.call(["docker", "build", "-t", "{}:latest".format(av), "{}".format(av)])


if __name__ == "__main__":
    main()
