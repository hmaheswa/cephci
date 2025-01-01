#!/usr/bin/env bash
#
# This utility performs a reimage operation on the provided set of nodes.
#
# The script allows performs the additional configuration changes on the provided nodes.
#
#   - Enables SSH access to root user
#   - Wipes the data disks
#   - Forces the nodes to use shortname instead of FQDN
#
#   Usage
#       $ bash prepare-bm-node.sh \
#           --platform [8.5|8.6|9.0] \
#           --nodes node1,node2,node3 \
#           [--node_username username] \
#           [--node_password password] \
#           [--wipe_drives] \
#           [--set_hostnames_repo]
#
#

set -eux -o pipefail

source pipeline/scripts/ci/server_setup_utils.sh

# Define the variables used in the script here.
OS_VER=""
NODES=""
NODE_USERNAME=${USERNAME:-root}
NODE_PASSWORD=${PASSWORD:-passwd}
INITIAL_SETUP=false
WIPE_DRIVES=false
SET_HOSTNAMES_REPO=false

function usage {
    echo "Usage: ${0} [-n | --nodes node1,node2] [--node_username username] [--node_password password] [--wipe_drives] [--set_hostnames_repo] [--remove_repo]"
    exit 2
}

CLI_OPTS=$(getopt -o hn:p: --long nodes:,node_username:,node_password:,help,initial_setup,wipe_drives,set_hostnames_repo,remove_repo -- "$@")

if [ $? != 0 ] || [ $# -lt 4 ] ; then
    usage
fi

eval set -- "${CLI_OPTS}"
while true; do
    case ${1} in
        -h | --help) usage ;;
        -n | --nodes) NODES="${2//,/ }"; shift 2 ;;
        --node_username) NODE_USERNAME="${2}"; shift 2 ;;
        --node_password) NODE_PASSWORD="${2}"; shift 2 ;;
        --initial_setup) INITIAL_SETUP=true; shift ;;
        --wipe_drives) WIPE_DRIVES=true; shift ;;
        --set_hostnames_repo) SET_HOSTNAMES_REPO=true; shift ;;
        --remove_repo) REMOVE_REPO=true; shift ;;
        --) shift; break ;;
        *) usage ;;
    esac
done
if [[ "$INITIAL_SETUP" = true ]]; then
    echo "set password for nodes"
    for node in ${NODES} ; do
        initial_setup_dsal "${node}" "${NODE_USERNAME}" "${NODE_PASSWORD}"
    done
fi

if [[ "$WIPE_DRIVES" = true ]]; then
    echo "Wiping data disks"
    for node in ${NODES} ; do
        wipe_drives "${node}" "${NODE_USERNAME}" "${NODE_PASSWORD}"
    done
fi

if [[ "$SET_HOSTNAMES_REPO" = true ]]; then
    echo "Sets the Hostname to shortname and cleans all the repos"
    for node in ${NODES} ; do
        set_hostnames_repos "${node}" "${NODE_USERNAME}" "${NODE_PASSWORD}"
    done
fi

if [[ "$REMOVE_REPO" = true ]]; then
    echo "Cleans all the repos"
    for node in ${NODES} ; do
        remove_repos "${node}" "${NODE_USERNAME}" "${NODE_PASSWORD}"
    done
fi
