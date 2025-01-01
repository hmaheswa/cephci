"""
This script provides the upstream latest rpm repo path and container image.
Please note that this script should be run under root privileges
inorder to pull the image and podman should be installed on that host.
"""

import logging
import os
import re
import sys
import time

import requests
import yaml
from docopt import docopt
from yaml.loader import SafeLoader

LOG = logging.getLogger(__name__)


def set_lock(file_name):
    """Method to lock the file to avoid race condition"""
    lock_file = file_name + ".lock"
    exit_status = os.system(f"ls -l {lock_file}")
    if exit_status:
        print("File lock does not exist, Creating it")
        os.system(f"touch {lock_file}")
        return
    # If any process locks the file it will wait till it unlock
    timeout = 600
    timeout_start = time.time()
    while time.time() < timeout_start + timeout:
        # wait for 2 minutes before retrying
        time.sleep(120)
        exit_status = os.system(f"ls -l {lock_file}")
        if exit_status:
            print("File lock does not exist, Creating it")
            os.system(f"touch {lock_file}")
            return

    raise Exception(f"Lock file: {lock_file} already exist, can not create lock file")


def unset_lock(file_name):
    """Method to unlock the above set lock"""
    lock_file = file_name + ".lock"
    exit_status = os.system(f"rm -f {lock_file}")
    if exit_status == 0:
        print("File un-locked successfully")
        return
    raise Exception("Unable to unlock the file")


def update_upstream(file_name, content, repo, image, upstream_version):
    """Method to update for the provided file
    along with file set lock to avoid race condition.
    Args:
        file_name: Name of the file to update
        content: things to update in file
    """
    with open(file_name, "w") as yaml_file:
        try:
            # To lock the file to avoid race condition
            set_lock(file_name)
            # update the file with write operation
            yaml_file.write(yaml.dump(content, default_flow_style=False))
        finally:
            # unlock it so other processed can use it
            unset_lock(file_name)
            LOG.info(
                f"Updated build info: \n repo:{repo} \n image:{image} \n ceph version:{upstream_version} in {file_name}"
            )


def compare(ex, new):
    """Returns true if new version > than existing.

    Args:
        ex: Existing ceph version
        new: Newer Ceph version

    Returns:
        Boolean
    """
    ev = "".join(re.split("[-.]", ex))
    nv = "".join(re.split("[-.]", new))

    length = ev.__len__() if ev.__len__() > nv.__len__() else nv.__len__()

    def zero_padding(x):
        return x if len(x) == length else x.ljust(length, "0")

    return zero_padding(nv) > zero_padding(ev)


def store_in_upstream(branch_name, repo, image, upstream_version):
    """Method to update it in upstream.yaml.
    Args:
        branch_name: Name of upstream branch
        repo: upstream branch compose URL
        image: upstream branch image
        upstream_version: upstream branch ceph version.
    """
    file_name = "/ceph/cephci-jenkins/latest-rhceph-container-info/upstream.yaml"
    repo_details = {}
    if os.path.exists(file_name):
        stream = open(file_name, "r")
        repo_details = yaml.load(stream, Loader=SafeLoader) or {}
    if repo_details and repo_details.get(branch_name):
        existing_version = repo_details[branch_name]["ceph-version"]
        # update only if current version is greater than existing version.
        if not compare(existing_version, upstream_version):
            print(
                f"Current version:{upstream_version} not greater than existing version:{existing_version}"
            )
            return
        repo_details[branch_name]["composes"] = repo
        repo_details[branch_name]["image"] = image
        repo_details[branch_name]["ceph-version"] = upstream_version
    else:
        # updating new branch details in upstream.yaml
        repo_details[branch_name] = {
            "ceph-version": upstream_version,
            "composes": repo,
            "image": image,
        }
    update_upstream(file_name, repo_details, repo, image, upstream_version)


usage = """
This script helps to provide needed info for upstream specific.

Usage:
  upstream_cli.py build <branch_name> [--os-type <os-type>] [--os-version <os-version>]


Example:
    python upstream_cli.py build quincy

Options:
    -h --help                           Show this screen
    --os-type <os-type>                 OS distro type [default: centos]
    --os-version <os-version>           OS major version [default: 9]
"""


def fetch_upstream_build(
    branch: str, os_type: str = "centos", os_version: str = "9", arch: str = "x86_64"
):
    """
    Method to get rpm repo path,container image and ceph version of given branch.

    Args:
        branch: str         Upstream branch name
        os_type: str        OS name ( default: centos )
        os_version: str     Centos Version (default: 9)
        arch: str           CPU Architecture (default: x86_64)
    """
    url = "https://shaman.ceph.com/api/repos/ceph/"
    url += f"{branch.lower()}/latest/{os_type}/{os_version}"

    def check_status(resp):
        if not resp.ok:
            resp.raise_for_status()

    # if any connection issue to URL it will wait for 30 seconds to establish connection.
    response = requests.get(url, timeout=30)
    check_status(response)
    _repo, _id, _version = None, None, None
    for srcs in response.json():
        if arch in srcs["archs"]:
            _version = srcs["extra"]["version"]
            _url = srcs["chacra_url"]
            _repo = f"{_url}repo" if _url.endswith("/") else f"{_url}/repo"
            _id = srcs["sha1"]
            break
    else:
        raise Exception(
            f"Could not find build source for {branch}-{os_type}-{os_version}-{arch}"
        )

    LOG.info(f"Upstream repo for the given branch is {_repo}")

    # To get image for that rpm repo
    image = "quay.ceph.io/ceph-ci/ceph:" + _id
    LOG.info(f"Upstream image for the given branch is {image}")

    cmd = "podman -v"
    exit_status = os.system(cmd)
    if exit_status:
        raise Exception("Please install podman on host")

    cmd = f"sudo podman pull {image}"
    exit_status = os.system(cmd)
    if exit_status:
        raise Exception(f"Failed to pull {image} using podman.")

    LOG.info(f"Upstream version for the given branch is {_version}")
    store_in_upstream(branch, _repo, image, _version)


OPS = {
    "build": fetch_upstream_build,
}

if __name__ == "__main__":
    _args = docopt(usage, help=True, version=None, options_first=False)
    logging.basicConfig(
        handlers=[logging.StreamHandler(sys.stdout)],
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
    )
    try:
        method = None
        for key, value in OPS.items():
            if _args[key]:
                method = value
                break
        else:
            raise Exception("please provide right action")

        upstream_branch = _args["<branch_name>"]
        os_type = _args.get("--os-type")
        os_version = _args.get("--os-version")

        args = {
            "branch": upstream_branch,
            "os_type": os_type,
            "os_version": os_version,
        }

        method(**args)
    except BaseException as be:
        raise Exception(be)
