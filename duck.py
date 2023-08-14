from json import dump, load
from sys import argv
from termcolor import colored
from shutil import rmtree, copyfile
from os import getcwd, mkdir, listdir
from os.path import isfile, join, exists
import typer

LOG_FILE_NAME = "duck.log.json"
PATH = getcwd()
LOG = dict()
app = typer.Typer()

# log constants
HEAD = "head"
TIMELINE = "timeline"
MESSAGE = "message"
FILES = "files"
COMMITS = "commits"
NEW = "new"
OLD = "old"
CHANGES = "changes"
ADD = "add"
DEL = "del"
INIT = "init"
INITIAL_COMMIT = "initial commit"

def get_file_log(original_file_lines, updated_file_lines):
    file_or = original_file_lines
    file_up = updated_file_lines
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
    file_log[DEL] = del_log
    
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
    file_log[ADD] = add_log
    
    return file_log

def check_file_exist_in_this_commit(file_name, commit_sha, log_file, path: str = PATH):
    this_commit_files = log_file[COMMITS][commit_sha][FILES]
    flag = file_name in [file for file in this_commit_files[CHANGES]]
    flag = flag or file_name in this_commit_files[NEW]
    return flag
        
def apply_commit_to_file(file_name, commit_sha, path: str = PATH):
    duck_dir_path = join(path, ".duck")
    duck_log_dir_path = join(duck_dir_path, LOG_FILE_NAME)
    duck_commits_dir_path = join(duck_dir_path, COMMITS)
    with open(duck_log_dir_path, "r") as file:
        log_file = load(file)
    timeline = log_file[TIMELINE]
    
    # finding first commit of this file
    first_commit_id = -1
    this_commit_id = -1
    for i in range(len(timeline)-1, -1, -1):
        if timeline[i] == commit_sha:
            first_commit_id = i
            this_commit_id = i
        if first_commit_id == -1:
            continue
        if check_file_exist_in_this_commit(file_name, commit_sha, log_file, path):
            first_commit_id = i
        else:
            break
        
    assert first_commit_id != -1, "`file_name` does not exist in any commit"

    with open(join(join(duck_commits_dir_path, timeline[first_commit_id]), file_name)) as file:
        lines = file.readlines()
        # only need to apply changes
        for i in range(first_commit_id+1, this_commit_id+1):
            cur_commit_sha = timeline[i]
            file_changelog = log_file[COMMITS][cur_commit_sha][FILES][CHANGES][file_name]
            # converting to common file
            common = [lines[i] for i in range(len(lines)) if str(i) not in file_changelog[DEL]]
            for change in file_changelog[ADD]:
                common.insert(int(change), file_changelog[ADD][change])
            lines = common
            
    return lines
            
@app.command()
def init(path: str = PATH, indent: bool = False):
    if not exists(path):
        error("ERROR: Invalid path found", info=False)
    duck_dir = join(path, ".duck")
    try:
        rmtree(duck_dir, ignore_errors=False, onerror=None)
    except:
        pass
    
    duck_log_file_path = join(duck_dir, LOG_FILE_NAME)
    commits_dir = join(duck_dir, "commits")
    mkdir(duck_dir)
    mkdir(commits_dir)
    init_commit_dir = join(commits_dir, "init")
    mkdir(init_commit_dir)
    
    log_file = dict()
    log_file[HEAD] = INIT
    log_file[TIMELINE] = [INIT]
    files = dict()
    files[NEW] = [file for file in listdir(path) if isfile(join(path, file))]
    files[OLD] = []
    files[CHANGES] = dict()
    init = dict()
    init[FILES] = files
    init[MESSAGE] = INITIAL_COMMIT
    commits = dict()
    commits[INIT] = init
    log_file[COMMITS] = commits

    # filling log 
    with open(duck_log_file_path, 'w') as log:
        dump(log_file, log, indent = 4 if indent else 0)

    # copying files
    for file in listdir(path):
        if isfile(join(path, file)):
            original_path = join(path, file)
            copied_path = join(init_commit_dir, file)
            copyfile(original_path, copied_path)

@app.command()
def commit(message: str, path: str = PATH, indent: bool = False):
    duck_log_file_path = join(join(path, ".duck"), LOG_FILE_NAME)
    try:
        with open(duck_log_file_path, "a"):
            pass
    except:
        error("ERROR: First init the repository using `python duck.py init`")  
    duck_dir_path = join(path, ".duck")
    duck_log_file_path = join(duck_dir_path, LOG_FILE_NAME)
    with open(duck_log_file_path, "r") as file:
        log_file = load(file)
    head = log_file[HEAD]
    timeline = log_file[TIMELINE]
    commit_head = log_file[COMMITS][head]
    this_files = [file for file in listdir(path) if isfile(join(path, file))]
    head_files = commit_head[FILES][NEW]
    head_files.extend([file for file in commit_head[FILES][CHANGES]])
    itr_files = set(this_files+head_files)
    new_files = []
    old_files = []
    change_files = dict()
    for file in itr_files:
        if file in this_files:
            if file in head_files:
                with open(join(path, file)) as f:
                    this_file_lines = f.readlines()
                    change_files[file] = get_file_log(apply_commit_to_file(file, head, path), this_file_lines)
            else:
                new_files.append(file)
        elif file in head_files:
            old_files.append(file)
    commit_name = f"commit-{len(timeline)}"
    log_file[TIMELINE].append(commit_name)
    log_file[HEAD] = commit_name
    this_commit = dict()
    this_commit[MESSAGE] = message
    this_commit_files = dict()
    this_commit_files[NEW] = new_files
    this_commit_files[OLD] = old_files
    this_commit_files[CHANGES] = change_files
    this_commit[FILES] = this_commit_files
    log_file[COMMITS][commit_name] = this_commit
    with open(duck_log_file_path, "w") as file:
        dump(log_file, file, indent = 4 if indent else 0)
    
    
def error(message, info=True):
    print(colored(message, "red"))
    if info:
        print(colored("INFO : Do `python duck.py --help`", "blue"))
    exit(1)

if __name__ == "__main__":
    app()
