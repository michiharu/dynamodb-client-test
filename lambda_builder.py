import os
import json
from shutil import copytree, rmtree, make_archive
import subprocess
import sys


DEFAULT_PACKAGES = [
    "boto3",
    "botocore",
    "docutils",
    "jmespath",
    "python-dateutil",
    "six",
    "urllib3",
    "s3transfer",
]

if __name__ == "__main__":

    dist_path = "dist"
    src_path = "src"

    if len(sys.argv) > 1:
        dist_path = sys.argv[1]

    if len(sys.argv) > 2:
        src_path = sys.argv[2]

    rmtree(dist_path, ignore_errors=True)
    copytree(src_path, dist_path)

    with open("Pipfile.lock", mode="r") as f:
        pipfile_lock = json.load(f)

    preargs = [sys.executable, "-m", "pip", "install"]
    postargs = ["-t", dist_path, "--no-deps"]
    for package, metadata in pipfile_lock["default"].items():
        if package in DEFAULT_PACKAGES:
            continue
        # ex. metadata["version"] = "==1.14.42"
        package_info = [package + metadata["version"]]
        subprocess.call(preargs + package_info + postargs)

    if os.path.isfile(f"{dist_path}.zip"):
        os.remove(f"{dist_path}.zip")
    make_archive(dist_path, "zip", root_dir=dist_path)
    rmtree(dist_path)
    print("\033[36m" + "Successfully build lambda zip" + "\033[0m")
