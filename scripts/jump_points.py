#!/usr/bin/env python

"""Save a restore BBEdit cursor locations."""

import datetime as dt
import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import xdg
import yaml

POINTS_FILE = xdg.xdg_data_home() / "jump_points" / "points.yaml"
LOG = logging.getLogger(__name__)
MAX_AGE = dt.timedelta(hours=1)


@dataclass
class JumpPoint:
    """Represent a cursor location in BBEdit."""

    filename: str
    line: int
    column: int
    bbedit_pid: int
    added: dt.datetime


def front_app_pid() -> int:
    """Return the pid of the front process, which is exceedingly likely to be BBEdit."""

    asn = subprocess.check_output(["lsappinfo", "front"])
    info = subprocess.check_output(["lsappinfo", "info", asn], encoding="utf-8")
    for line in info.splitlines():
        if "pid" in line:
            bbedit_pid = int(line.split()[2])
            LOG.debug(f"Found BBEdit at {bbedit_pid=}")
            return bbedit_pid
    raise KeyError(f"No pid in {info=}")


def localtime() -> dt.datetime:
    """Return the current local datetime with tzinfo."""

    return dt.datetime.now(dt.timezone.utc).astimezone()


def get_points(path: Path, oldest_time: dt.datetime) -> list[JumpPoint]:
    """Return the list of saved editing points."""

    try:
        content = path.read_text()
    except FileNotFoundError:
        LOG.info(f"{POINTS_FILE=} doesn't exist.")
        return []

    point_list = yaml.safe_load(content)["points"]
    points = [
        point
        for point_data in point_list
        if (point := JumpPoint(**point_data)).added >= oldest_time
    ]
    LOG.debug(f"Loaded {points=}")
    return points


def save_points(path: Path, points: list[JumpPoint]):
    """Save the list of editing points."""

    LOG.debug(f"Writing {points=} to {path=}")
    (path.parent).mkdir(parents=True, exist_ok=True)
    content = yaml.dump({"points": [point.__dict__ for point in points]})
    path.write_text(content)


def setup_logging(args):
    """Set logging to the requested level."""

    level_num = 0
    for arg in args[1:]:
        if arg == "-v":
            level_num += 1

    if level_num == 0:
        level = logging.WARNING
    elif level_num == 1:
        level = logging.INFO
    else:
        level = logging.DEBUG

    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s:%(name)s:%(message)s")


def push():
    """Store BBEdit's current cursor point."""

    setup_logging(sys.argv)

    now = localtime()

    try:
        point = JumpPoint(
            filename=os.environ["BB_DOC_PATH"],
            line=int(os.environ["BB_DOC_SELSTART_LINE"]),
            column=int(os.environ["BB_DOC_SELSTART_COLUMN"]),
            bbedit_pid=front_app_pid(),
            added=now,
        )
    except KeyError:
        print("Not launched from BBEdit.")
        sys.exit(1)

    LOG.info(f"Storing {point=}")

    points = get_points(POINTS_FILE, now - MAX_AGE)
    points.append(point)
    save_points(POINTS_FILE, points)


def pop():
    """Send BBEdit back to the previous cursor point."""

    setup_logging(sys.argv + ["-v", "-v", "-v"])

    points = get_points(POINTS_FILE, localtime() - MAX_AGE)

    bbedit_pid = front_app_pid()
    LOG.debug(f"Searching for points from {bbedit_pid=}")
    my_points = [
        (index, point) for index, point in enumerate(points) if point.bbedit_pid == bbedit_pid
    ]
    LOG.debug(f"Found {my_points=}")
    try:
        index, point = my_points[-1]
    except IndexError:
        return

    points.pop(index)
    save_points(POINTS_FILE, points)

    LOG.info(f"Restoring {point=}")

    bb_args = ["/usr/local/bin/bbedit", f"+{point.line}:{point.column}", point.filename]
    LOG.debug(f"Subprocess {bb_args=}")
    subprocess.check_call(
        bb_args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    LOG.debug("done")
