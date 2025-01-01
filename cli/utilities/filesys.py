from cli import Cli


class MountFailedError(Exception):
    pass


class Mount(Cli):
    """This module provides CLI support for mount operations"""

    def __init__(self, nodes):
        super(Mount, self).__init__(nodes)
        self.base_cmd = "mount"

    def nfs(self, mount, version, port, server, export):
        """
        Perform nfs mount
        Args:
            mount (str): nfs mount path
            version (str): Nfs version (4.0, 4.1, 4.2 etc)
            port (str): nfs port to bind
            server (str): Nfs server hostname
            export (str): nfs export path)
        """
        # Check if mount dir is present, else create
        out = self.execute(cmd=f"ls {mount}", sudo=True)
        if not out[0]:
            self.execute(cmd=f"mkdir {mount}", sudo=True)

        # Create the mount point
        cmd = f"{self.base_cmd} -t nfs -o vers={version},port={port} {server}:{export} {mount}"
        self.execute(sudo=True, long_running=True, cmd=cmd)

        out = self.execute(sudo=True, cmd="mount")
        if isinstance(out, tuple):
            out = out[0]

        if not mount.rstrip("/") in out:
            raise MountFailedError(f"Nfs mount failed: {out}")


class Unmount(Cli):
    def __init__(self, nodes):
        super(Unmount, self).__init__(nodes)
        self.base_cmd = "umount"

    def unmount(self, mount, lazy=True):
        """
        Perform unmount of volume
        Args:
            mount (str): path to mount point
            lazy (bool): Perform a lazy unmount or not
        Returns:

        """
        cmd = f"{self.base_cmd} {mount}"
        if lazy:
            cmd += " -l"
        out = self.execute(sudo=True, cmd=cmd)
        if isinstance(out, tuple):
            return out[0].strip()
        return out
