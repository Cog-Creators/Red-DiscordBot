from discord.ext import commands
from cogs.utils import checks
import asyncio
import os
import datetime
import time
import socket
from socket import AF_INET, SOCK_STREAM, SOCK_DGRAM

try:
    import psutil
    psutilAvailable = True
except ImportError:
    psutilAvailable = False


# Most of these scripts are from https://github.com/giampaolo/psutil/tree/master/scripts
# noinspection SpellCheckingInspection,PyPep8Naming,PyPep8Naming
class SysInfo:
    """Display system information for the machine running the bot"""

    def __init__(self, bot):
        self.bot = bot

    @commands.group(pass_context=True, aliases=['sys'])
    async def sysinfo(self, ctx):
        """Shows system information for the machine running the bot"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @sysinfo.command(pass_context=True)
    @checks.is_owner()
    async def info(self, ctx, *args: str):
        """Summary of cpu, memory, disk and network information
         Usage: info [option]
         Examples:
             sysinfo           Shows all available info
             sysinfo cpu       Shows CPU usage
             sysinfo memory    Shows memory usage
             sysinfo file      Shows full path of open files
             sysinfo disk      Shows disk usage
             sysinfo network   Shows network usage
             sysinfo boot      Shows boot time
         """

        options = ('cpu', 'memory', 'file', 'disk', 'network', 'boot')

        # CPU
        cpu_count_p = psutil.cpu_count(logical=False)
        cpu_count_l = psutil.cpu_count()
        if cpu_count_p is None:
            cpu_count_p = "N/A"
        cpu_cs = ("CPU Count"
                  "\n\t{0:<9}: {1:>3}".format("Physical", cpu_count_p) +
                  "\n\t{0:<9}: {1:>3}".format("Logical", cpu_count_l))
        psutil.cpu_percent(interval=None, percpu=True)
        await asyncio.sleep(1)
        cpu_p = psutil.cpu_percent(interval=None, percpu=True)
        cpu_ps = ("CPU Usage"
                  "\n\t{0:<8}: {1}".format("Per CPU", cpu_p) +
                  "\n\t{0:<8}: {1:.1f}%".format("Overall", sum(cpu_p) / len(cpu_p)))
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
            if hasattr(open_f[0], "mode"):
                open_fs += "\n\t".join(["{0} [{1}]".format(f.path, f.mode) for f in open_f])
            else:
                open_fs += "\n\t".join(["{0}".format(f.path) for f in open_f])
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
                  "\n\t{0}".format(datetime.datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")))

        # Output
        msg = ""
        if not args or args[0].lower() not in options:
            msg = "\n\n".join([cpu_cs, cpu_ps, cpu_ts, mem_vs, mem_ss, open_fs, disk_us, net_ios, boot_s])
        elif args[0].lower() == 'cpu':
            msg = "\n" + "\n\n".join([cpu_cs, cpu_ps, cpu_ts])
        elif args[0].lower() == 'memory':
            msg = "\n" + "\n\n".join([mem_vs, mem_ss])
        elif args[0].lower() == 'file':
            msg = "\n" + open_fs
        elif args[0].lower() == 'disk':
            msg = "\n" + disk_us
        elif args[0].lower() == 'network':
            msg = "\n" + net_ios
        elif args[0].lower() == 'boot':
            msg = "\n" + boot_s
        await self._say(ctx, msg)
        return

    @sysinfo.command(pass_context=True)
    @checks.is_owner()
    async def df(self, ctx):
        """File system disk space usage"""

        if len(psutil.disk_partitions(all=False)) == 0:
            await self._say(ctx, "psutil could not find any disk partitions")
            return

        maxlen = len(max([p.device for p in psutil.disk_partitions(all=False)], key=len))
        template = "\n{0:<{1}} {2:>9} {3:>9} {4:>9} {5:>9}% {6:>9}  {7}"
        msg = template.format("Device", maxlen, "Total", "Used", "Free", "Used ", "Type", "Mount")
        for part in psutil.disk_partitions(all=False):
            if os.name == 'nt':
                if 'cdrom' in part.opts or part.fstype == '':
                    # skip cd-rom drives with no disk in it; they may raise ENOENT,
                    # pop-up a Windows GUI error for a non-ready partition or just hang.
                    continue
            usage = psutil.disk_usage(part.mountpoint)
            msg += template.format(
                part.device,
                maxlen,
                self._size(usage.total),
                self._size(usage.used),
                self._size(usage.free),
                usage.percent,
                part.fstype,
                part.mountpoint)
        await self._say(ctx, msg)
        return

    @sysinfo.command(pass_context=True)
    @checks.is_owner()
    async def free(self, ctx):
        """Amount of free and used memory in the system"""

        virt = psutil.virtual_memory()
        swap = psutil.swap_memory()
        template = "\n{0:>7} {1:>9} {2:>9} {3:>9} {4:>8}% {5:>9} {6:>9} {7:>9}"
        msg = template.format("", "Total", "Used", "Free", "Used ", "Shared", "Buffers", "Cache")
        msg += template.format(
            "Memory:",
            self._size(virt.total),
            self._size(virt.used),
            self._size(virt.free),
            virt.percent,
            self._size(getattr(virt, 'shared', 0)),
            self._size(getattr(virt, 'buffers', 0)),
            self._size(getattr(virt, 'cached', 0)))
        msg += template.format(
            "Swap:",
            self._size(swap.total),
            self._size(swap.used),
            self._size(swap.free),
            swap.percent,
            "",
            "",
            "")
        await self._say(ctx, msg)
        return

    @sysinfo.command(pass_context=True)
    @checks.is_owner()
    async def ifconfig(self, ctx):
        """Network interface information"""

        af_map = {
            socket.AF_INET: 'IPv4',
            socket.AF_INET6: 'IPv6',
            psutil.AF_LINK: 'MAC',
        }
        duplex_map = {
            psutil.NIC_DUPLEX_FULL: "full",
            psutil.NIC_DUPLEX_HALF: "half",
            psutil.NIC_DUPLEX_UNKNOWN: "?",
        }
        try:
            stats = psutil.net_if_stats()
        except PermissionError:
            await self.bot.say("Unable to access network information due to PermissionError")
            return
        io_counters = psutil.net_io_counters(pernic=True)
        msg = ""
        for nic, addrs in psutil.net_if_addrs().items():
            msg += "\n{0}:".format(nic)
            if nic in stats:
                st = stats[nic]
                msg += "\n    stats          : "
                msg += "speed={0}MB, duplex={1}, mtu={2}, up={3}".format(
                    st.speed, duplex_map[st.duplex], st.mtu,
                    "yes" if st.isup else "no")
            if nic in io_counters:
                io = io_counters[nic]
                msg += "\n    incoming       : "
                msg += "bytes={0}, pkts={1}, errs={2}, drops={3}".format(
                    io.bytes_recv, io.packets_recv, io.errin, io.dropin)
                msg += "\n    outgoing       : "
                msg += "bytes={0}, pkts={1}, errs={2}, drops={3}".format(
                    io.bytes_sent, io.packets_sent, io.errout, io.dropout)
            for addr in addrs:
                msg += "\n    {0:<4}".format(af_map.get(addr.family, addr.family))
                msg += " address   : {0}".format(addr.address)
                if addr.broadcast:
                    msg += "\n         broadcast : {0}".format(addr.broadcast)
                if addr.netmask:
                    msg += "\n         netmask   : {0}".format(addr.netmask)
                if addr.ptp:
                    msg += "\n      p2p       : {0}".format(addr.ptp)
            msg += "\n"
        await self._say(ctx, msg)
        return

    @sysinfo.command(pass_context=True)
    @checks.is_owner()
    async def iotop(self, ctx):
        """Snapshot of I/O usage information output by the kernel"""

        if not hasattr(psutil.Process, "oneshot"):
            await self.bot.say("Platform not supported")
            return

        # first get a list of all processes and disk io counters
        procs = [p for p in psutil.process_iter()]
        for p in procs[:]:
            try:
                p._before = p.io_counters()
            except psutil.Error:
                procs.remove(p)
                continue
        disks_before = psutil.disk_io_counters()

        # sleep some time
        await asyncio.sleep(1)

        # then retrieve the same info again
        for p in procs[:]:
            with p.oneshot():
                try:
                    p._after = p.io_counters()
                    p._cmdline = ' '.join(p.cmdline())
                    if not p._cmdline:
                        p._cmdline = p.name()
                    p._username = p.username()
                except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied):
                    procs.remove(p)
        disks_after = psutil.disk_io_counters()

        # finally calculate results by comparing data before and
        # after the interval
        for p in procs:
            p._read_per_sec = p._after.read_bytes - p._before.read_bytes
            p._write_per_sec = p._after.write_bytes - p._before.write_bytes
            p._total = p._read_per_sec + p._write_per_sec

        disks_read_per_sec = disks_after.read_bytes - disks_before.read_bytes
        disks_write_per_sec = disks_after.write_bytes - disks_before.write_bytes

        # sort processes by total disk IO so that the more intensive
        # ones get listed first
        processes = sorted(procs, key=lambda p: p._total, reverse=True)

        # print results
        template = "{0:<5} {1:<7} {2:11} {3:11} {4}\n"

        msg = "Total DISK READ: {0} | Total DISK WRITE: {1}\n".format(
            self._size(disks_read_per_sec), self._size(disks_write_per_sec))

        msg += template.format("PID", "USER", "DISK READ", "DISK WRITE", "COMMAND")

        for p in processes:
            msg += template.format(
                p.pid,
                p._username[:7],
                self._size(p._read_per_sec),
                self._size(p._write_per_sec),
                p._cmdline)
        await self._say(ctx, msg)
        return

    @sysinfo.command(pass_context=True)
    @checks.is_owner()
    async def meminfo(self, ctx):
        """System memory information"""

        msg = "\nMEMORY\n------\n"
        msg += "{0}\n".format(self._sprintf_ntuple(psutil.virtual_memory()))
        msg += "SWAP\n----\n"
        msg += "{0}\n".format(self._sprintf_ntuple(psutil.swap_memory()))
        await self._say(ctx, msg)
        return

    @sysinfo.command(pass_context=True)
    @checks.is_owner()
    async def netstat(self, ctx):
        """Information about the networking subsystem"""

        AD = "-"
        AF_INET6 = getattr(socket, 'AF_INET6', object())
        proto_map = {
            (AF_INET, SOCK_STREAM): 'tcp',
            (AF_INET6, SOCK_STREAM): 'tcp6',
            (AF_INET, SOCK_DGRAM): 'udp',
            (AF_INET6, SOCK_DGRAM): 'udp6',
        }
        template = "{0:<5} {1:<30} {2:<30} {3:<13} {4:<6} {5}\n"
        msg = template.format(
            "Proto", "Local address", "Remote address", "Status", "PID",
            "Program name")
        proc_names = {}
        for p in psutil.process_iter():
            try:
                proc_names[p.pid] = p.name()
            except psutil.Error:
                pass
        for c in psutil.net_connections(kind='inet'):
            laddr = "%s:%s" % c.laddr
            raddr = ""
            if c.raddr:
                raddr = "%s:%s" % c.raddr
            msg += template.format(
                proto_map[(c.family, c.type)],
                laddr,
                raddr or AD,
                c.status,
                c.pid or AD,
                proc_names.get(c.pid, '?')[:15],
            )
        await self._say(ctx, msg)
        return

    @sysinfo.command(pass_context=True)
    @checks.is_owner()
    async def nettop(self, ctx):
        """Snapshot of real-time network statistics"""

        # Retrieve raw stats within an interval window
        # noinspection PyUnusedLocal
        tot_before = psutil.net_io_counters()
        pnic_before = psutil.net_io_counters(pernic=True)
        await asyncio.sleep(1)
        tot_after = psutil.net_io_counters()
        pnic_after = psutil.net_io_counters(pernic=True)

        # totals
        msg = "Total Bytes:           Sent: {0:<10}   Received: {1}\n".format(
            self._size(tot_after.bytes_sent),
            self._size(tot_after.bytes_recv))
        msg += "Total Packets:         Sent: {0:<10}   Received: {1}\n".format(
            tot_after.packets_sent, tot_after.packets_recv)

        # per-network interface details: let's sort network interfaces so
        # that the ones which generated more traffic are shown first
        msg += "\n"
        nic_names = list(pnic_after.keys())
        nic_names.sort(key=lambda x: sum(pnic_after[x]), reverse=True)
        for name in nic_names:
            stats_before = pnic_before[name]
            stats_after = pnic_after[name]
            template = "{0:<15} {1:>15} {2:>15}\n"
            msg += template.format(name, "TOTAL", "PER-SEC")
            msg += "-" * 64 + "\n"
            msg += template.format(
                "bytes-sent",
                self._size(stats_after.bytes_sent),
                self._size(
                    stats_after.bytes_sent - stats_before.bytes_sent) + '/s',
            )
            msg += template.format(
                "bytes-recv",
                self._size(stats_after.bytes_recv),
                self._size(
                    stats_after.bytes_recv - stats_before.bytes_recv) + '/s',
            )
            msg += template.format(
                "pkts-sent",
                stats_after.packets_sent,
                stats_after.packets_sent - stats_before.packets_sent,
            )
            msg += template.format(
                "pkts-recv",
                stats_after.packets_recv,
                stats_after.packets_recv - stats_before.packets_recv,
            )
            msg += "\n"
        await self._say(ctx, msg)
        return

    @sysinfo.command(pass_context=True)
    @checks.is_owner()
    async def smem(self, ctx):
        """Physical memory usage, taking shared memory pages into account"""

        if not (psutil.LINUX or psutil.OSX or psutil.WINDOWS):
            await self.bot.say("Platform not supported")
            return

        if not hasattr(psutil.Process, "oneshot"):
            await self.bot.say("Platform not supported")
            return

        ad_pids = []
        procs = []
        for p in psutil.process_iter():
            with p.oneshot():
                try:
                    mem = p.memory_full_info()
                    info = p.as_dict(attrs=["cmdline", "username"])
                except psutil.AccessDenied:
                    ad_pids.append(p.pid)
                except psutil.NoSuchProcess:
                    pass
                else:
                    p._uss = mem.uss
                    p._rss = mem.rss
                    if not p._uss:
                        continue
                    p._pss = getattr(mem, "pss", "")
                    p._swap = getattr(mem, "swap", "")
                    p._info = info
                    procs.append(p)

        procs.sort(key=lambda p: p._uss)
        template = "{0:<7} {1:<7} {2:<30} {3:>7} {4:>7} {5:>7} {6:>7}\n"
        msg = template.format("PID", "User", "Cmdline", "USS", "PSS", "Swap", "RSS")
        msg += "=" * 78 + "\n"
        for p in procs[:86]:
            msg += template.format(
                p.pid,
                p._info["username"][:7],
                " ".join(p._info["cmdline"])[:30],
                self._size(p._uss),
                self._size(p._pss) if p._pss != "" else "",
                self._size(p._swap) if p._swap != "" else "",
                self._size(p._rss),
            )
        if ad_pids:
            msg += "warning: access denied for {0} pids".format(len(ad_pids))
        await self._say(ctx, msg)
        return

    @sysinfo.command(pass_context=True)
    @checks.is_owner()
    async def ps(self, ctx):
        """Information about active processes"""

        PROC_STATUSES_RAW = {
            psutil.STATUS_RUNNING: "R",
            psutil.STATUS_SLEEPING: "S",
            psutil.STATUS_DISK_SLEEP: "D",
            psutil.STATUS_STOPPED: "T",
            psutil.STATUS_TRACING_STOP: "t",
            psutil.STATUS_ZOMBIE: "Z",
            psutil.STATUS_DEAD: "X",
            psutil.STATUS_WAKING: "WA",
            psutil.STATUS_IDLE: "I",
            psutil.STATUS_LOCKED: "L",
            psutil.STATUS_WAITING: "W",
        }
        if hasattr(psutil, 'STATUS_WAKE_KILL'):
            PROC_STATUSES_RAW[psutil.STATUS_WAKE_KILL] = "WK"
        if hasattr(psutil, 'STATUS_SUSPENDED'):
            PROC_STATUSES_RAW[psutil.STATUS_SUSPENDED] = "V"

        today_day = datetime.date.today()
        template = "{0:<10} {1:>5} {2:>4} {3:>4} {4:>7} {5:>7} {6:>13} {7:>5} {8:>5} {9:>7}  {10}\n"
        attrs = ['pid', 'cpu_percent', 'memory_percent', 'name', 'cpu_times',
                 'create_time', 'memory_info', 'status']
        if os.name == 'posix':
            attrs.append('uids')
            attrs.append('terminal')
        msg = template.format("USER", "PID", "%CPU", "%MEM", "VSZ", "RSS", "TTY",
                              "STAT", "START", "TIME", "COMMAND")
        for p in psutil.process_iter():
            try:
                pinfo = p.as_dict(attrs, ad_value='')
            except psutil.NoSuchProcess:
                pass
            else:
                if pinfo['create_time']:
                    ctime = datetime.datetime.fromtimestamp(pinfo['create_time'])
                    if ctime.date() == today_day:
                        ctime = ctime.strftime("%H:%M")
                    else:
                        ctime = ctime.strftime("%b%d")
                else:
                    ctime = ''
                cputime = time.strftime("%M:%S",
                                        time.localtime(sum(pinfo['cpu_times'])))
                try:
                    user = p.username()
                except KeyError:
                    if os.name == 'posix':
                        if pinfo['uids']:
                            user = str(pinfo['uids'].real)
                        else:
                            user = ''
                    else:
                        raise
                except psutil.Error:
                    user = ''
                if os.name == 'nt' and '\\' in user:
                    user = user.split('\\')[1]
                vms = pinfo['memory_info'] and int(pinfo['memory_info'].vms / 1024) or '?'
                rss = pinfo['memory_info'] and int(pinfo['memory_info'].rss / 1024) or '?'
                memp = pinfo['memory_percent'] and round(pinfo['memory_percent'], 1) or '?'
                status = PROC_STATUSES_RAW.get(pinfo['status'], pinfo['status'])
                msg += template.format(
                    user[:10],
                    pinfo['pid'],
                    pinfo['cpu_percent'],
                    memp,
                    vms,
                    rss,
                    pinfo.get('terminal', '') or '?',
                    status,
                    ctime,
                    cputime,
                    pinfo['name'].strip() or '?')
        await self._say(ctx, msg)
        return

    @sysinfo.command(pass_context=True)
    @checks.is_owner()
    async def top(self, ctx):
        """Snapshot of real-time system information and tasks"""

        # sleep some time
        psutil.cpu_percent(interval=None, percpu=True)
        await asyncio.sleep(1)
        procs = []
        procs_status = {}
        for p in psutil.process_iter():
            try:
                p.dict = p.as_dict(['username', 'nice', 'memory_info',
                                    'memory_percent', 'cpu_percent',
                                    'cpu_times', 'name', 'status'])
                try:
                    procs_status[p.dict['status']] += 1
                except KeyError:
                    procs_status[p.dict['status']] = 1
            except psutil.NoSuchProcess:
                pass
            else:
                procs.append(p)

        # return processes sorted by CPU percent usage
        processes = sorted(procs, key=lambda p: p.dict['cpu_percent'],
                           reverse=True)

        # Print system-related info, above the process list
        msg = ""
        num_procs = len(procs)

        def get_dashes(perc):
            dashes = "|" * int((float(perc) / 10 * 4))
            empty_dashes = " " * (40 - len(dashes))
            return dashes, empty_dashes

        # cpu usage
        percs = psutil.cpu_percent(interval=0, percpu=True)
        for cpu_num, perc in enumerate(percs):
            dashes, empty_dashes = get_dashes(perc)
            msg += " CPU{0:<2} [{1}{2}] {3:>5}%\n".format(cpu_num, dashes, empty_dashes, perc)
        mem = psutil.virtual_memory()
        dashes, empty_dashes = get_dashes(mem.percent)
        msg += " Mem   [{0}{1}] {2:>5}% {3:>6} / {4}\n".format(
            dashes, empty_dashes,
            mem.percent,
            str(int(mem.used / 1024 / 1024)) + "M",
            str(int(mem.total / 1024 / 1024)) + "M"
        )

        # swap usage
        swap = psutil.swap_memory()
        dashes, empty_dashes = get_dashes(swap.percent)
        msg += " Swap  [{0}{1}] {2:>5}% {3:>6} / {4}\n".format(
            dashes, empty_dashes,
            swap.percent,
            str(int(swap.used / 1024 / 1024)) + "M",
            str(int(swap.total / 1024 / 1024)) + "M"
        )

        # processes number and status
        st = []
        for x, y in procs_status.items():
            if y:
                st.append("%s=%s" % (x, y))
        st.sort(key=lambda x: x[:3] in ('run', 'sle'), reverse=True)
        msg += " Processes: {0} ({1})\n".format(num_procs, ', '.join(st))
        # load average, uptime
        uptime = datetime.datetime.now() - datetime.datetime.fromtimestamp(psutil.boot_time())
        if not hasattr(os, "getloadavg"):
            msg += " Load average: N/A  Uptime: {0}".format(
                str(uptime).split('.')[0])
        else:
            av1, av2, av3 = os.getloadavg()
            msg += " Load average: {0:.2f} {1:.2f} {2:.2f}  Uptime: {3}".format(
                av1, av2, av3, str(uptime).split('.')[0])
        await self._say(ctx, msg)

        # print processes
        template = "{0:<6} {1:<9} {2:>5} {3:>8} {4:>8} {5:>8} {6:>6} {7:>10}  {8:>2}\n"
        msg = template.format("PID", "USER", "NI", "VIRT", "RES", "CPU%", "MEM%",
                              "TIME+", "NAME")
        for p in processes:
            # TIME+ column shows process CPU cumulative time and it
            # is expressed as: "mm:ss.ms"
            if p.dict['cpu_times'] is not None:
                ctime = datetime.timedelta(seconds=sum(p.dict['cpu_times']))
                ctime = "%s:%s.%s" % (ctime.seconds // 60 % 60,
                                      str((ctime.seconds % 60)).zfill(2),
                                      str(ctime.microseconds)[:2])
            else:
                ctime = ''
            if p.dict['memory_percent'] is not None:
                p.dict['memory_percent'] = round(p.dict['memory_percent'], 1)
            else:
                p.dict['memory_percent'] = ''
            if p.dict['cpu_percent'] is None:
                p.dict['cpu_percent'] = ''
            if p.dict['username']:
                username = p.dict['username'][:8]
            else:
                username = ''
            msg += template.format(p.pid,
                                   username,
                                   p.dict['nice'] or '',
                                   self._size(getattr(p.dict['memory_info'], 'vms', 0)),
                                   self._size(getattr(p.dict['memory_info'], 'rss', 0)),
                                   p.dict['cpu_percent'],
                                   p.dict['memory_percent'],
                                   ctime,
                                   p.dict['name'] or '')
        await self._say(ctx, msg)
        return

    @sysinfo.command(pass_context=True)
    @checks.is_owner()
    async def who(self, ctx):
        """Shows which users are currently logged in"""

        msg = ""
        users = psutil.users()
        for user in users:
            proc_name = ""
            if hasattr(user, "pid"):
                proc_name = psutil.Process(user.pid).name()
            msg += "{0:<12} {1:<10} {2:<10} {3:<14} {4}\n".format(
                user.name,
                user.terminal or '-',
                datetime.datetime.fromtimestamp(user.started).strftime("%Y-%m-%d %H:%M"),
                "(%s)" % user.host if user.host else "",
                proc_name)
        if not msg:
            msg = "No users logged in"
        await self._say(ctx, msg)
        return

    def _sprintf_ntuple(self, nt):
        s = ""
        for name in nt._fields:
            value = getattr(nt, name)
            if name != 'percent':
                value = self._size(value)
            s += "{0:<10} : {1:>7}\n".format(name.capitalize(), value)
        return s

    @staticmethod
    def _size(num):
        for unit in ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB"]:
            if abs(num) < 1024.0:
                return "{0:.1f}{1}".format(num, unit)
            num /= 1024.0
        return "{0:.1f}{1}".format(num, "YB")

    # Respect 2000 character limit per message
    async def _say(self, ctx, msg, escape=True, wait=True):
        template = "```{0}```" if escape else "{0}"
        buf = ""
        for line in msg.splitlines():
            if len(buf) + len(line) >= 1900:
                await self.bot.say(template.format(buf))
                buf = ""
                if wait:
                    await self.bot.say("Type 'more' or 'm' to continue...")
                    answer = await self.bot.wait_for_message(timeout=10, author=ctx.message.author)
                    if not answer or answer.content.lower() not in ["more", "m"]:
                        await self.bot.say("Command output stopped.")
                        return
            buf += line + "\n"
        if buf:
            await self.bot.say(template.format(buf))


def setup(bot):
    if psutilAvailable:
        n = SysInfo(bot)
        bot.add_cog(n)
    else:
        raise RuntimeError("You need to run 'pip3 install psutil'")
