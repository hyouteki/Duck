from json import dump
from sys import argv
from termcolor import colored
from shutil import rmtree
from os import getcwd, mkdir, listdir

LOG_FILE_NAME = "duck.log.json"
LOG = dict()

def get_file_log(original_file_path, updated_file_path):
    with open(original_file_path, "r") as original:
        with open(updated_file_path, "r") as updated:
            file_or = original.readlines()
            file_up = updated.readlines()
            len_or, len_up = len(file_or), len(file_up)
            # finding longest common subsequence between `or` & `up` file
            dp = [[0 for j in range(len_up+1)] for i in range(len_or+1)]
            for i in range(len_or+1):
                for j in range(len_up+1):
                    if i == 0 or j == 0:
                        continue
                    if (file_or[i-1] == file_up[j-1]):
                        dp[i][j] = 1+dp[i-1][j-1]
                    else:
                        dp[i][j] = max(dp[i-1][j], dp[i][j-1])
            common = ["" for i in range(dp[len_or][len_up])]
            ptr_or, ptr_up, ptr_cm = len_or, len_up, dp[len_or][len_up]-1
            while ptr_or > 0 and ptr_up > 0 and ptr_cm >= 0:
                if file_or[ptr_or-1] == file_up[ptr_up-1]:
                    common[ptr_cm] = file_or[ptr_or-1]
                    ptr_cm -= 1
                    ptr_or -= 1
                    ptr_up -= 1
                elif dp[ptr_or-1][ptr_up] > dp[ptr_or][ptr_up-1]:
                    ptr_or -= 1
                else:
                    ptr_up -= 1
            file_log = dict()
            del_log = dict()
            ptr_cm = 0
            for i in range(len_or):
                if ptr_cm == len(common):
                    del_log[i] = file_or[i]
                    continue
                if file_or[i] == common[ptr_cm]:
                    ptr_cm += 1
                else:
                    del_log[i] = file_or[i]
            file_log["del"] = del_log
            add_log = dict()
            ptr_cm = 0
            for i in range(len_up):
                if ptr_up == len(common):
                    add_log[i] = file_up[i]
                    continue
                if file_or[i] == common[ptr_cm]:
                    ptr_cm += 1
                else:
                    add_log[i] = file_up[i]
            file_log["add"] = add_log
            return file_log

file_log = get_file_log("original.txt", "testadd.txt")
LOG["original.txt"] = file_log

with open(LOG_FILE_NAME, 'w') as log:
    dump(LOG, log)

def help():
    print(colored("""$ python duck.py <command> <flags> <arguments>
Commands:
    help  : help
    init  : initializes the duck VCS
    commit: commits the change to duck log""", "blue"))

def init():
    duck_file = getcwd()+"//.duck/"
    try:
        rmtree(duck_file, ignore_errors=False, onerror=None)
    except:
        pass
    duck_log_file_path = duck_file+"//"+LOG_FILE_NAME
    mkdir(duck_file)
    log_file = dict()
    log_file["latest commit"] = "init"
    init = dict()
    init["files"] = listdir(getcwd())
    init["message"] = "initial commit"
    commits = dict()
    commits["init"] = init
    log_file["commits"] = commits
    with open(duck_log_file_path, 'w') as log:
        dump(log_file, log)
    
def commit():
    assert False, "Yet to implement `commit`"

def error(message):
    print(colored(message, "red"))
    print(colored("INFO : Do `python duck.py help`", "blue"))
    exit(1)
    
def main():
    if len(argv) < 2:
        error("ERROR: Invalid terminal command")
    command = argv[1]
    if command == "help":
        help()
    elif command == "init":
        init()
    elif command == "commit":
        commit()
    else:
        error("ERROR: Invalid command found")
    
main()
