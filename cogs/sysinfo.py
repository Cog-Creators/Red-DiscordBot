from discord.ext import commands
from cogs.utils import checks
import asyncio
import os
from datetime import datetime

try:
    import psutil
    psutilAvailable = True
except:
    psutilAvailable = False


class SysInfo:
    """Display CPU, Memory, Disk and Network information"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='sysinfo')
    @checks.is_owner()
    async def psutil(self):
        """Show CPU, Memory, Disk, and Network information"""

        # CPU
        cpu_cs = ("CPU Count"
                  "\n\t{0:<9}: {1:>2}".format("Physical", psutil.cpu_count(logical=False)) +
                  "\n\t{0:<9}: {1:>2}".format("Logical", psutil.cpu_count()))
        psutil.cpu_percent(interval=None, percpu=True)
        await asyncio.sleep(1)
        cpu_p = psutil.cpu_percent(interval=None, percpu=True)
        cpu_ps = ("CPU Usage"
                  "\n\t{0:<8}: {1}".format("Per CPU", cpu_p) +
                  "\n\t{0:<8}: {1:.1f}%".format("Overall", sum(cpu_p)/len(cpu_p)))
        cpu_t = psutil.cpu_times()
        width = max([len("{:,}".format(int(n))) for n in [cpu_t.user, cpu_t.system, cpu_t.idle]])
        cpu_ts = ("CPU Times"
                  "\n\t{0:<7}: {1:>{width},}".format("User", int(cpu_t.user), width=width) +
                  "\n\t{0:<7}: {1:>{width},}".format("System", int(cpu_t.system), width=width) +
                  "\n\t{0:<7}: {1:>{width},}".format("Idle", int(cpu_t.idle), width=width))

        # Memory
        mem_v = psutil.virtual_memory()
        width = max([len(self._size(n)) for n in [mem_v.total, mem_v.available, (mem_v.total - mem_v.available)]])
        mem_vs = ("Virtual Memory"
                  "\n\t{0:<10}: {1:>{width}}".format("Total", self._size(mem_v.total), width=width) +
                  "\n\t{0:<10}: {1:>{width}}".format("Available", self._size(mem_v.available), width=width) +
                  "\n\t{0:<10}: {1:>{width}} {2}%".format("Used", self._size(mem_v.total - mem_v.available),
                                                          mem_v.percent, width=width))
        mem_s = psutil.swap_memory()
        width = max([len(self._size(n)) for n in [mem_s.total, mem_s.free, (mem_s.total - mem_s.free)]])
        mem_ss = ("Swap Memory"
                  "\n\t{0:<6}: {1:>{width}}".format("Total", self._size(mem_s.total), width=width) +
                  "\n\t{0:<6}: {1:>{width}}".format("Free", self._size(mem_s.free), width=width) +
                  "\n\t{0:<6}: {1:>{width}} {2}%".format("Used", self._size(mem_s.total - mem_s.free),
                                                         mem_s.percent, width=width))

        # Open files
        open_f = psutil.Process().open_files()
        open_fs = "Open File Handles\n\t"
        if open_f:
            common = os.path.commonpath([f.path for f in open_f])
            if hasattr(open_f[0], "mode"):
                open_fs += "\n\t".join(["{0} [{1}]".format(f.path.replace(common, '.'), f.mode) for f in open_f])
            else:
                open_fs += "\n\t".join(["{0}".format(f.path.replace(common, '.')) for f in open_f])
        else:
            open_fs += "None"

        # Disk usage
        disk_u = psutil.disk_usage(os.path.sep)
        width = max([len(self._size(n)) for n in [disk_u.total, disk_u.free, disk_u.used]])
        disk_us = ("Disk Usage"
                   "\n\t{0:<6}: {1:>{width}}".format("Total", self._size(disk_u.total), width=width) +
                   "\n\t{0:<6}: {1:>{width}}".format("Free", self._size(disk_u.free), width=width) +
                   "\n\t{0:<6}: {1:>{width}} {2}%".format("Used", self._size(disk_u.used),
                                                          disk_u.percent, width=width))

        # Network
        net_io = psutil.net_io_counters()
        width = max([len(self._size(n)) for n in [net_io.bytes_sent, net_io.bytes_recv]])
        net_ios = ("Network"
                   "\n\t{0:<11}: {1:>{width}}".format("Bytes sent", self._size(net_io.bytes_sent), width=width) +
                   "\n\t{0:<11}: {1:>{width}}".format("Bytes recv", self._size(net_io.bytes_recv), width=width))

        # Boot time
        boot_s = ("Boot Time"
                  "\n\t{0}".format(datetime.fromtimestamp(
                       psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")))

        await self.bot.say("```" +
                           "\n\n".join([cpu_cs, cpu_ps, cpu_ts, mem_vs, mem_ss, open_fs, disk_us, net_ios, boot_s]) +
                           "```")

        return

    def _size(self, num):
        for unit in ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB", "ZB"]:
            if abs(num) < 1024.0:
                return "{0:.1f}{1}".format(num, unit)
            num /= 1024.0
        return "{0:.1f}{1}".format(num, "YB")


def setup(bot):
    if psutilAvailable:
        n = SysInfo(bot)
        bot.add_cog(n)
    else:
        raise RuntimeError("You need to run 'pip3 install psutil'")
