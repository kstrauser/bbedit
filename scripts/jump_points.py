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
    added: dt.datetime


# A time-ordered list of points from different BBEdit processes.
PointsMap = dict[int, list[JumpPoint]]


def front_app_pid() -> int:
    """Return the pid of the front process, which is exceedingly likely to be BBEdit."""

    asn = subprocess.check_output(["lsappinfo", "visibleProcessList"]).split()[0]
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


def get_points(path: Path, oldest_time: dt.datetime) -> PointsMap:
    """Return the collection of saved editing points."""

    try:
        content = path.read_text()
    except FileNotFoundError:
        LOG.info(f"{POINTS_FILE=} doesn't exist.")
        return {}

    points_data = yaml.safe_load(content)["points"]
    points_map: PointsMap = {}

    for pid, points in points_data.items():
        # Collect the list of unexpired points for this pid.
        current_points = [
            point
            for point_data in points
            if (point := JumpPoint(**point_data)).added >= oldest_time
        ]

        # If the pid doesn't have any unexpired points, skip it. This also keeps the data structure
        # from growing unbounded forever.
        if current_points:
            points_map[pid] = current_points

    LOG.debug(f"Loaded {points_map=}")
    return points_map


def save_points(path: Path, points_map: PointsMap):
    """Save the list of editing points."""

    LOG.debug(f"Writing {points_map=} to {path=}")
    (path.parent).mkdir(parents=True, exist_ok=True)

    points_data: dict[int, list[dict]] = {}
    for bbedit_pid, points in points_map.items():
        # Only store a pid's point list if it has any left.
        if points:
            points_data[bbedit_pid] = [point.__dict__ for point in points]

    content = yaml.dump({"points": points_data})
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
            added=now,
        )
    except KeyError:
        print("Not launched from BBEdit.")
        sys.exit(1)

    LOG.info(f"Storing {point=}")

    points_map = get_points(POINTS_FILE, now - MAX_AGE)
    points_map.setdefault(front_app_pid(), []).append(point)
    save_points(POINTS_FILE, points_map)


def pop():
    """Send BBEdit back to the previous cursor point."""

    setup_logging(sys.argv)

    points_map = get_points(POINTS_FILE, localtime() - MAX_AGE)

    bbedit_pid = front_app_pid()
    LOG.debug(f"Searching for points from {bbedit_pid=}")
    try:
        pid_points = points_map[bbedit_pid]
    except KeyError:
        # This pid doesn't have any points? No problem.
        return

    point = pid_points.pop()
    LOG.debug(f"Found {point=}")

    save_points(POINTS_FILE, points_map)

    bb_args = ["/usr/local/bin/bbedit", f"+{point.line}:{point.column}", point.filename]
    LOG.debug(f"Subprocess {bb_args=}")
    subprocess.check_call(
        bb_args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
