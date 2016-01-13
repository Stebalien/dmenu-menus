#!/usr/bin/python

from xdg import BaseDirectory
from xdg.DesktopEntry import DesktopEntry
from glob import glob
import os.path
import itertools
import subprocess
import re, shlex

DMENU_OPTIONS=(
    "-p", "Launch:",
    "-b",
    "-i",
    "-l", "10",
    "-nb", "#111111",
    "-nf", "#aaaaaa",
    "-sf", "#336ec0",
    "-sb", "#1a1a1a",
)

FILTER = re.compile("(?<!%)%[a-zA-Z]")
HISTORY_FILE = os.path.join(os.environ["XDG_CACHE_HOME"], "dmenu_launch_history")

def basename(path):
    return os.path.splitext(os.path.basename(path))[0]

def getPrograms():
    return {
        desktop.getName() : desktop
        for desktop in (
            DesktopEntry(dfile)
            for dfile in itertools.chain(*(
                glob(os.path.join(path, '*.desktop'))
                for path in BaseDirectory.load_data_paths('applications')
            ))
        ) if not desktop.getHidden()
    }

def getRanking():
    history = {}
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE) as f:
            for l in f.readlines():
                l = l.strip()
                if l in history:
                    history[l] += 1
                else:
                    history[l] = 1
    return history

def recordLaunch(desktop):
    with open(HISTORY_FILE, "a") as f:
        f.write(basename(desktop.filename)+"\n")

def formatMenu(programs):
    ranking = getRanking()
    return "\n".join(d.getName() for d in sorted(programs.values(), key=lambda d: -ranking.get(basename(d.filename), 0)))

def pickProgram(program_map):
    dmenu = subprocess.Popen(("dmenu",) + DMENU_OPTIONS, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    out, _ = dmenu.communicate(input=formatMenu(program_map).encode())
    out = out[:-1] # Strip '\n'
    if out and out in program_map:
        return program_map[out]

def getService(desktop):
    path = desktop.filename
    name = basename(path)

    systemctl = subprocess.Popen(("systemctl", "--user", "-p", "SourcePath", "--no-pager", "show", name), stdout=subprocess.PIPE)
    out = systemctl.communicate()[0]
    # Only start service if it is the correct one.
    if out and out[0:11] == "SourcePath=" and out[11:-1] == path:
        return name

def execDesktop(desktop):
    service_name = getService(desktop)
    if service_name:
        cmd = ("systemctl", "--user", "start", service_name)
    else:
        cmd = shlex.split(FILTER.sub('', desktop.getExec()))
    recordLaunch(desktop)
    os.execvp(cmd[0], cmd)

if __name__ == '__main__':
    desktop = pickProgram(getPrograms())
    if desktop:
        execDesktop(desktop)
