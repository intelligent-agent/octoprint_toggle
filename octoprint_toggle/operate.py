import datetime
import json, time
import subprocess
import os
import logging
import logging.handlers

my_logger = logging.getLogger('MyLogger')
my_logger.setLevel(logging.DEBUG)
handler = logging.handlers.SysLogHandler(address='/dev/log')
my_logger.addHandler(handler)


class Operate:
    def __init__(self):
        self.path = "/etc/toggle/"

    def get_printers(self):
        """ Get a list of config files """
        import glob
        blacklist = ["default.cfg", "printer.cfg", "local.cfg"]
        try:
            files = [
                os.path.basename(f) for f in glob.glob(self.path + "*.cfg")
                if os.path.isfile(os.path.join(self.path, f))
                and os.path.basename(f) not in blacklist
            ]
            return files
        except OSError:
            return []

    def get_default_printer(self):
        """ Get the current printer """
        real = os.path.realpath(self.path + "printer.cfg")
        return os.path.basename(real)

    def choose_printer(self, filename):
        """ Choose which printer config should be used """
        path = "/etc/toggle/"
        whitelist = self.get_printers()
        if filename not in whitelist:
            return False
        filename = os.path.join(path, filename)
        linkname = os.path.join(path, "printer.cfg")
        # Only unlink if exists
        if os.path.isfile(linkname):
            os.unlink(linkname)
        # only link if exists
        if os.path.isfile(filename):
            os.symlink(filename, linkname)
            return True
        return False

    def delete_printer(self, filename):
        full = self.path + filename
        if os.path.isfile(full):
            os.unlink(full)
            return True
        return False

    def get_local(self, filename):
        with open(filename, "r+") as f:
            return f.read()

    def save_local(self, data, filename):
        logging.info(data)
        with open(filename, "w+") as f:
            f.write(data)

    def restart_toggle(self):
        # Octo will need to have sudo privileges to restart redeem for this to work.
        # Add "%octo ALL=NOPASSWD: /bin/systemctl restart redeem.service" to /etc/sudoers
        logging.warning("Restarting Toggle")
        subprocess.call("sudo systemctl restart toggle.service", shell=True)
