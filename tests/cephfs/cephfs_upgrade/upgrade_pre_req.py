import json
import random
import string
import traceback

from ceph.ceph import CommandFailed
from tests.cephfs.cephfs_utilsV1 import FsUtils
from tests.cephfs.cephfs_volume_management import wait_for_process
from utility.log import Log

log = Log(__name__)


def run(ceph_cluster, **kw):
    """
    Create multiple file systems(include EC-pool).
    Collect the information of MDS(like which is active mds node and standby mds nodes details)
    Collect the status of the cluster and version
    Create subvolumegroups, subvolumes
    Mount using fuse and kernel mount different subvolumes and also cephfs root folder on to different locations.
    Create a sample file, folder and get the stat details of it.
    Create NFS cluster and mount it. → 5.0 feature
    Taking snapshots and clones of the volume (Scheduled snapshots, retain snapshots → 5.0 feature).
    Client authorize and subvolume authorize feature
    Dir pinning and set quota to the subvolume
    Run IOs on all the mount points from a different client machine.
    """
    try:
        fs_util = FsUtils(ceph_cluster)
        config = kw.get("config")
        build = config.get("build", config.get("rhbuild"))
        clients = ceph_cluster.get_ceph_objects("client")
        log.info("checking Pre-requisites")
        if len(clients) < 2:
            log.info(
                f"This test requires minimum 2 client nodes.This has only {len(clients)} clients"
            )
            return 1
        fs_util.prepare_clients(clients, build)
        fs_util.auth_list(clients)
        default_fs = "cephfs"
        version, rc = clients[0].exec_command(
            sudo=True, cmd="ceph version --format json"
        )
        ceph_version = json.loads(version)
        nfs_mounting_dir = "/mnt/nfs/"
        dir_name = "dir"
        list_cmds = [
            "ceph fs flag set enable_multiple true",
            "ceph osd pool create cephfs-data-ec 64 erasure",
            "ceph osd pool create cephfs-metadata 64",
            "ceph osd pool set cephfs-data-ec allow_ec_overwrites true",
            "ceph fs new cephfs-ec cephfs-metadata cephfs-data-ec --force",
        ]
        if fs_util.get_fs_info(clients[0], "cephfs_new"):
            default_fs = "cephfs_new"
            list_cmds.append("ceph fs volume create cephfs")
        for cmd in list_cmds:
            clients[0].exec_command(sudo=True, cmd=cmd)
        upgrade_config = None
        vol_list = [default_fs, "cephfs-ec"]
        with open(
            "tests/cephfs/cephfs_upgrade/config.json",
            "r",
        ) as f:
            upgrade_config = json.load(f)
        svg_list = [
            f"{upgrade_config.get('subvolume_group_prefix', 'upgrade_svg')}_{svg}"
            for svg in range(0, upgrade_config.get("subvolume_group_count", 3))
        ]
        subvolumegroup_list = [
            {"vol_name": v, "group_name": svg} for v in vol_list for svg in svg_list
        ]
        log.info(subvolumegroup_list)
        for subvolumegroup in subvolumegroup_list:
            fs_util.create_subvolumegroup(clients[0], **subvolumegroup)

        subvolume_list = [
            {
                "vol_name": v,
                "group_name": svg,
                "subvol_name": f"{upgrade_config.get('subvolume_prefix', 'upgrade_sv')}_{sv}",
            }
            for v in vol_list
            for svg in svg_list
            for sv in range(0, upgrade_config.get("subvolume_count", 3))
        ]

        for subvolume in subvolume_list:
            fs_util.create_subvolume(clients[0], **subvolume)

        mounting_dir = "".join(
            random.choice(string.ascii_lowercase + string.digits)
            for _ in list(range(10))
        )
        mount_points = {"kernel_mounts": [], "fuse_mounts": [], "nfs_mounts": []}
        for sv in subvolume_list[::2]:
            subvol_path, rc = clients[0].exec_command(
                sudo=True,
                cmd=f"ceph fs subvolume getpath {sv['vol_name']} {sv['subvol_name']} {sv['group_name']}",
            )
            mon_node_ips = fs_util.get_mon_node_ips()
            kernel_mounting_dir_1 = (
                f"/mnt/cephfs_kernel{mounting_dir}_{sv['vol_name']}_{sv['group_name']}_"
                f"{sv['subvol_name']}/"
            )
            if "nautilus" not in ceph_version["version"]:
                fs_util.kernel_mount(
                    [clients[0]],
                    kernel_mounting_dir_1,
                    ",".join(mon_node_ips),
                    sub_dir=f"{subvol_path.strip()}",
                    extra_params=f",fs={sv['vol_name']}",
                )
                mount_points["kernel_mounts"].append(kernel_mounting_dir_1)
            else:
                if sv["vol_name"] == default_fs:
                    fs_util.kernel_mount(
                        [clients[0]],
                        kernel_mounting_dir_1,
                        ",".join(mon_node_ips),
                        sub_dir=f"{subvol_path.strip()}",
                    )
                    mount_points["kernel_mounts"].append(kernel_mounting_dir_1)

        for sv in subvolume_list[1::2]:
            subvol_path, rc = clients[0].exec_command(
                sudo=True,
                cmd=f"ceph fs subvolume getpath {sv['vol_name']} {sv['subvol_name']} {sv['group_name']}",
            )
            fuse_mounting_dir_1 = (
                f"/mnt/cephfs_fuse{mounting_dir}_{sv['vol_name']}_{sv['group_name']}_"
                f"{sv['subvol_name']}/"
            )
            if "nautilus" not in ceph_version["version"]:
                fs_util.fuse_mount(
                    [clients[0]],
                    fuse_mounting_dir_1,
                    extra_params=f"-r {subvol_path.strip()} --client_fs {sv['vol_name']}",
                )
                mount_points["fuse_mounts"].append(fuse_mounting_dir_1)
            else:
                if sv["vol_name"] == default_fs:
                    fs_util.fuse_mount(
                        [clients[0]],
                        fuse_mounting_dir_1,
                        extra_params=f"-r {subvol_path.strip()} ",
                    )
                    mount_points["fuse_mounts"].append(fuse_mounting_dir_1)

        if "nautilus" not in ceph_version["version"]:
            nfs_server = ceph_cluster.get_ceph_objects("nfs")
            nfs_client = ceph_cluster.get_ceph_objects("client")
            fs_util.auth_list(nfs_client)
            nfs_name = "cephfs-nfs"
            out, rc = nfs_client[0].exec_command(
                sudo=True, cmd="ceph fs ls | awk {' print $2'} "
            )
            fs_name = out.rstrip()
            fs_name = fs_name.strip(",")
            nfs_export_name = "/export1"
            path = "/"
            nfs_server_name = nfs_server[0].node.hostname
            # Create ceph nfs cluster
            nfs_client[0].exec_command(sudo=True, cmd="ceph mgr module enable nfs")
            out, rc = nfs_client[0].exec_command(
                sudo=True, cmd=f"ceph nfs cluster create {nfs_name} {nfs_server_name}"
            )
            # Verify ceph nfs cluster is created
            if wait_for_process(
                client=nfs_client[0], process_name=nfs_name, ispresent=True
            ):
                log.info("ceph nfs cluster created successfully")
            else:
                raise CommandFailed("Failed to create nfs cluster")
            # Create cephfs nfs export
            if "5.0" in build:
                nfs_client[0].exec_command(
                    sudo=True,
                    cmd=f"ceph nfs export create cephfs {fs_name} {nfs_name} "
                    f"{nfs_export_name} path={path}",
                )
            else:
                nfs_client[0].exec_command(
                    sudo=True,
                    cmd=f"ceph nfs export create cephfs {nfs_name} "
                    f"{nfs_export_name} {fs_name} path={path}",
                )

            # Verify ceph nfs export is created
            out, rc = nfs_client[0].exec_command(
                sudo=True, cmd=f"ceph nfs export ls {nfs_name}"
            )
            if nfs_export_name in out:
                log.info("ceph nfs export created successfully")
            else:
                raise CommandFailed("Failed to create nfs export")
            # Mount ceph nfs exports
            nfs_client[0].exec_command(sudo=True, cmd=f"mkdir -p {nfs_mounting_dir}")
            assert fs_util.wait_for_cmd_to_succeed(
                nfs_client[0],
                cmd=f"mount -t nfs -o port=2049 {nfs_server_name}:{nfs_export_name} {nfs_mounting_dir}",
            )
            nfs_client[0].exec_command(
                sudo=True,
                cmd=f"mount -t nfs -o port=2049 {nfs_server_name}:{nfs_export_name} {nfs_mounting_dir}",
            )
            out, rc = nfs_client[0].exec_command(cmd="mount")
            mount_output = out.split()
            log.info("Checking if nfs mount is is passed of failed:")
            assert nfs_mounting_dir.rstrip("/") in mount_output
            log.info("Creating Directory")
            out, rc = nfs_client[0].exec_command(
                sudo=True, cmd=f"mkdir {nfs_mounting_dir}{dir_name}"
            )
            nfs_client[0].exec_command(
                sudo=True,
                cmd=f"python3 /home/cephuser/smallfile/smallfile_cli.py --operation create --threads 10 --file-size 4 "
                f"--files 1000 --files-per-dir 10 --dirs-per-dir 2 --top "
                f"{nfs_mounting_dir}{dir_name}",
                long_running=True,
            )
            nfs_client[0].exec_command(
                sudo=True,
                cmd=f"python3 /home/cephuser/smallfile/smallfile_cli.py --operation read --threads 10 --file-size 4 "
                f"--files 1000 --files-per-dir 10 --dirs-per-dir 2 --top "
                f"{nfs_mounting_dir}{dir_name}",
                long_running=True,
            )
        else:
            clients = ceph_cluster.get_ceph_objects("client")
            nfs_server = [clients[0]]
            nfs_client = [clients[1]]

            rc = fs_util.nfs_ganesha_install(nfs_server[0])
            if rc == 0:
                log.info("NFS ganesha installed successfully")
            else:
                raise CommandFailed("NFS ganesha installation failed")
            rc = fs_util.nfs_ganesha_conf(nfs_server[0], "admin")
            if rc == 0:
                log.info("NFS ganesha config added successfully")
            else:
                raise CommandFailed("NFS ganesha config adding failed")
                rc = fs_util.nfs_ganesha_mount(
                    nfs_client[0], nfs_mounting_dir, nfs_server[0].node.hostname
                )
            if rc == 0:
                log.info("NFS-ganesha mount passed")
            else:
                raise CommandFailed("NFS ganesha mount failed")

            mounting_dir = nfs_mounting_dir + "ceph/"
            out, rc = nfs_client[0].exec_command(
                sudo=True, cmd=f"mkdir -p {mounting_dir}{dir_name}"
            )
            nfs_client[0].exec_command(
                sudo=True,
                cmd=f"python3 /home/cephuser/smallfile/smallfile_cli.py --operation create --threads 10 --file-size 4 "
                f"--files 1000 --files-per-dir 10 --dirs-per-dir 2 --top "
                f"{mounting_dir}{dir_name}",
                long_running=True,
            )
            nfs_client[0].exec_command(
                sudo=True,
                cmd=f"python3 /home/cephuser/smallfile/smallfile_cli.py --operation read --threads 10 --file-size 4 "
                f"--files 1000 --files-per-dir 10 --dirs-per-dir 2 --top "
                f"{mounting_dir}{dir_name}",
                long_running=True,
            )

        for i in mount_points["kernel_mounts"] + mount_points["fuse_mounts"]:
            fs_util.run_ios(clients[0], i)

        return 0

    except Exception as e:
        log.info(e)
        log.info(traceback.format_exc())
        return 1
