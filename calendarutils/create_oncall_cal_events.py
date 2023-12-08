import datetime
import importlib
import os
import subprocess
import sys

home = os.path.expanduser("~")
DIR = f"{home}/development/cloudera/pagerduty-helper"
SCRIPT = f"{DIR}/when_am_i_on_call.py"

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


if __name__ == '__main__':
    # TODO
    user = "snemeth"
    start = None
    end = None
    # call_script()
    # load_single_module("when_am_i_on_call", SCRIPT)
    load_module(DIR)
    mymodule = importlib.import_module("when_am_i_on_call")
    if "@" not in user:
        user = user + "@cloudera.com"
    if start is None:
        start = datetime.datetime.today() - datetime.timedelta(days=7)
    if end is None:
        end = datetime.datetime.today() + datetime.timedelta(days=90)
    print(f"Getting shifts for user {user} from {start} to {end}")
    mymodule.get

