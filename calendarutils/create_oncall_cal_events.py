import datetime
import importlib
import os
import subprocess
import sys
from os.path import expanduser

from googleapiwrapper.common import ServiceType
from googleapiwrapper.google_auth import GoogleApiAuthorizer
from googleapiwrapper.google_calendar import CalendarApiWrapper, CalendarDate
from pythoncommons.file_utils import FileUtils

home = os.path.expanduser("~")
DIR = f"{home}/development/cloudera/pagerduty-helper"
SCRIPT = f"{DIR}/when_am_i_on_call.py"
import logging
LOG = logging.getLogger(__name__)

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])


def call_script():
    install("pdpyras")
    params = "--user snemeth"
    os.system(f"python3 {SCRIPT} {params}")

def load_single_module(module_name, file):
    import importlib.util
    import sys
    spec = importlib.util.spec_from_file_location(module_name, file)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    mod.MyClass()

def load_module(dir):
    import sys
    sys.path.append(dir)


def get_params():
    # TODO Fix params
    user = "snemeth"
    start = None
    end = None

    if "@" not in user:
        user = user + "@cloudera.com"
    if start is None:
        start = datetime.datetime.today() - datetime.timedelta(days=7)
    if end is None:
        end = datetime.datetime.today() + datetime.timedelta(days=90)
    return user, start, end


def create_cal_events(summary: str, description: str, start: datetime.datetime, end: datetime.datetime):
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    SECRET_PROJECTS_DIR = FileUtils.join_path(expanduser("~"), ".secret", "projects", "cloudera")
    authorizer = GoogleApiAuthorizer(
        ServiceType.CALENDAR,
        project_name="calendarutils",
        secret_basedir=SECRET_PROJECTS_DIR,
        account_email="snemeth@cloudera.com",
        scopes=ServiceType.CALENDAR_WRITE.default_scopes,
    )
    wrapper = CalendarApiWrapper(authorizer)
    start = CalendarDate(start.date().isoformat())
    end = CalendarDate(end.date().isoformat())
    wrapper.create_all_day_event(summary, description, start, end)


def is_consecutive(dates):
    date_ints = set([d.toordinal() for d in dates])
    if len(date_ints) == 1:
        print("unique")
    elif max(date_ints) - min(date_ints) == len(date_ints) - 1:
        print("consecutive")
        return True
    else:
        print("not consecutive")
    return False


def validate_dates():
    for d_tup in shifts:
        d1 = datetime.datetime.fromisoformat(d_tup[0]).date()
        d2 = datetime.datetime.fromisoformat(d_tup[1]).date()
        if d1 != d2:
            return False, d_tup
    return True, None


if __name__ == '__main__':
    # call_script()
    # load_single_module("when_am_i_on_call", SCRIPT)
    load_module(DIR)
    pdhelper_module = importlib.import_module("when_am_i_on_call")
    user, start, end = get_params()
    print(f"Getting shifts for user {user} from {start} to {end}")
    shifts_to_schedules = pdhelper_module.get_shifts(user, start, end)
    for sched_name, shifts in shifts_to_schedules.items():
        print(shifts)
        valid, tup = validate_dates()
        if not valid:
            LOG.error("Some of the dates do not store the same day. Tuple: %s", tup)
            continue

        dates = [datetime.datetime.fromisoformat(dtup[0]) for dtup in shifts]
        consecutive = is_consecutive(dates)
        if consecutive:
            # TODO check if same event (same title + same time range) exists in calendar, do not add if exists
            create_cal_events(summary=f"On call: {sched_name}", description="", start=dates[0], end=dates[-1])
        else:
            LOG.error("Date range is not consecutive, not creating Google Calendar events!")
