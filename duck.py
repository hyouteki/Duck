from json import dump, load
from termcolor import colored
from shutil import rmtree, copyfile
from os import getcwd, mkdir, listdir
from os.path import isfile, join, exists
import typer
import inquirer

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
COM = "com"
INIT = "commit-init"
INITIAL_COMMIT = "initial commit"


def get_file_change_log(
    original_file_lines: list, updated_file_lines: list, include_common: bool = False
) -> dict:
    """
    @desc\t
        compares updated and original files and spits out the change log

    @params\t
        original_file_lines: list of '\n' seperated lines of original file
        updated_file_lines: list of '\n' seperated lines of updated file
        include_common: flag for including common lines in change log

    @return\t
        log: which is a dict containing list of new/old lines
    """

    len_or, len_up = len(original_file_lines), len(updated_file_lines)

    # finding the longest common subsequence between both versions of the file
    dp = [[0 for _ in range(len_up + 1)] for _ in range(len_or + 1)]
    for i in range(len_or + 1):
        for j in range(len_up + 1):
            if i == 0 or j == 0:
                continue
            if original_file_lines[i - 1] == updated_file_lines[j - 1]:
                dp[i][j] = 1 + dp[i - 1][j - 1]
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

    # finding the common lines between both versions of the file
    common = ["" for _ in range(dp[len_or][len_up])]
    ptr_or, ptr_up, ptr_cm = len_or, len_up, dp[len_or][len_up] - 1
    while ptr_or > 0 and ptr_up > 0 and ptr_cm >= 0:
        if original_file_lines[ptr_or - 1] == updated_file_lines[ptr_up - 1]:
            common[ptr_cm] = original_file_lines[ptr_or - 1]
            ptr_cm -= 1
            ptr_or -= 1
            ptr_up -= 1
        elif dp[ptr_or - 1][ptr_up] > dp[ptr_or][ptr_up - 1]:
            ptr_or -= 1
        else:
            ptr_up -= 1

    # {
    #     "add": {(line_number -> line), ...},
    #     "del": {(line_number -> line), ...},
    # }
    file_log = dict()

    if include_common:
        file_log[COM] = common

    # dict of deleted lines
    # {(line_number -> line), ...}
    del_log = dict()
    ptr_cm = 0
    for i in range(len_or):
        if ptr_cm == len(common):
            del_log[i] = original_file_lines[i]
            continue
        if original_file_lines[i] == common[ptr_cm]:
            ptr_cm += 1
        else:
            del_log[i] = original_file_lines[i]
    file_log[DEL] = del_log

    # dict of newly added lines
    # {(line_number -> line), ...}
    add_log = dict()
    ptr_cm = 0
    for i in range(len_up):
        if i >= len(common):
            add_log[i] = updated_file_lines[i]
            continue
        if updated_file_lines[i] == common[ptr_cm]:
            ptr_cm += 1
        else:
            add_log[i] = updated_file_lines[i]
    file_log[ADD] = add_log

    return file_log


def check_file_exist_in_this_commit(
    file_name: str, commit_sha: str, log_file: dict
) -> bool:
    """
    @desc\t
        checks if a certain file exists in this commit

    @params\t
        file_name: name of the file
        commit_sha: sha of the commit
        log_file: log file `.duck/duck.log.json`

    @return\t
        log: which is a dict containing list of new/old lines
    """

    this_commit_files = log_file[COMMITS][commit_sha][FILES]
    flag = file_name in [file for file in this_commit_files[CHANGES]]
    flag = flag or file_name in this_commit_files[NEW]
    return flag


def apply_commit_to_file(file_name: str, commit_sha: str, path: str = PATH) -> list:
    """
    @desc\t
        returns the lines in the file `file_name` during the commit `commit_sha`

    @params\t
        file_name: name of the file
        commit_sha: sha of the commit
        path: path the duck repository

    @raises\t
        AssertionError: `file_name` does not exist in any commit

    @return\t
        file_lines: list of '\n' seperated lines of the file `file_name`
    """

    duck_dir_path = join(path, ".duck")
    duck_log_dir_path = join(duck_dir_path, LOG_FILE_NAME)
    duck_commits_dir_path = join(duck_dir_path, COMMITS)
    with open(duck_log_dir_path, "r") as file:
        log_file = load(file)
    timeline = log_file[TIMELINE]

    # finding first commit just berfoe this commit of this file
    first_commit_id = -1
    this_commit_id = -1
    for i in range(len(timeline) - 1, -1, -1):
        if timeline[i] == commit_sha:
            first_commit_id = i
            this_commit_id = i
        if first_commit_id == -1:
            continue
        if check_file_exist_in_this_commit(file_name, commit_sha, log_file):
            first_commit_id = i
        else:
            break

    assert first_commit_id != -1, "`file_name` does not exist in any commit"

    with open(
        join(join(duck_commits_dir_path, timeline[first_commit_id]), file_name)
    ) as file:
        lines = file.readlines()
        # applying changes at each commit from first commit to this commit
        for i in range(first_commit_id + 1, this_commit_id + 1):
            cur_commit_sha = timeline[i]
            file_changelog = log_file[COMMITS][cur_commit_sha][FILES][CHANGES][
                file_name
            ]
            # converting to common file
            common = [
                lines[i] for i in range(len(lines)) if str(i) not in file_changelog[DEL]
            ]
            # adding newly added lines of this commit
            for change in file_changelog[ADD]:
                common.insert(int(change), file_changelog[ADD][change])
            lines = common

    return lines


@app.command()
def init(path: str = PATH, indent: bool = False) -> None:
    """
    @desc\t
        initializes the directory at the path `path` as the duck repository

    @params\t
        path: path of the duck repository
        indent: should indent the log file `.duck/duck.log.json`

    @return\t
        None
    """

    if not exists(path):
        error("ERROR: Invalid path found", info=False)
    duck_dir = join(path, ".duck")
    try:
        # deletes the ./duck dir if any
        rmtree(duck_dir, ignore_errors=False, onerror=None)
    except:
        pass

    duck_log_file_path = join(duck_dir, LOG_FILE_NAME)
    commits_dir = join(duck_dir, COMMITS)
    mkdir(duck_dir)
    mkdir(commits_dir)
    init_commit_dir = join(commits_dir, INIT)
    mkdir(init_commit_dir)

    log_file = dict()
    log_file[HEAD] = INIT
    log_file[TIMELINE] = [INIT]
    files = dict()
    # TODO(#1): add support for recursively intializing the directories ↴
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
    with open(duck_log_file_path, "w") as log:
        dump(log_file, log, indent=4 if indent else 0)

    # copying files
    count_files = 0
    for file in listdir(path):
        if isfile(join(path, file)):
            original_path = join(path, file)
            copied_path = join(init_commit_dir, file)
            copyfile(original_path, copied_path)
            count_files += 1

    print(
        colored(
            f"COOKIE: Initialized {count_files} files in directory `{path}`", "blue"
        )
    )

    return None


@app.command()
def commit(message: str, path: str = PATH, indent: bool = False) -> None:
    """
    @desc\t
        commits the current version of the directory at the path `path`

    @params\t
        message: commit message
        path: path of the duck repository
        indent: should indent the log file `.duck/duck.log.json`

    @return\t
        None
    """

    # TODO(#2): Add support for not commiting if no changes are present

    duck_dir_path = join(path, ".duck")
    duck_log_file_path = join(duck_dir_path, LOG_FILE_NAME)
    try:
        with open(duck_log_file_path, "r"):
            pass
    except:
        error("ERROR: First init the repository using `python duck.py init`")

    with open(duck_log_file_path, "r") as file:
        log_file = load(file)

    head = log_file[HEAD]
    timeline = log_file[TIMELINE]
    commit_head = log_file[COMMITS][head]
    # TODO(#1): add support for recursively intializing the directories ↴
    this_files = [file for file in listdir(path) if isfile(join(path, file))]
    head_files = commit_head[FILES][NEW]
    head_files.extend([file for file in commit_head[FILES][CHANGES]])
    itr_files = set(this_files + head_files)
    new_files = []
    old_files = []
    change_files = dict()
    commit_name = f"commit-{len(timeline)}"

    this_commit_dir_path = join(join(duck_dir_path, COMMITS), commit_name)
    mkdir(this_commit_dir_path)

    for file in itr_files:
        if file in this_files:
            if file in head_files:
                with open(join(path, file)) as f:
                    this_file_lines = f.readlines()
                    change_files[file] = get_file_change_log(
                        apply_commit_to_file(file, head, path), this_file_lines
                    )
            else:
                new_files.append(file)
                original_path = join(path, file)
                copied_path = join(this_commit_dir_path, file)
                copyfile(original_path, copied_path)
        elif file in head_files:
            old_files.append(file)

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
        dump(log_file, file, indent=4 if indent else 0)

    print(colored(f"COOKIE: Commit SHA = {commit_name}", "blue"))
    print(colored(f"COOKIE: Commit Message = {message}", "blue"))
    print(colored(f"COOKIE: Commited in directory `{path}`", "blue"))
    print(colored("COOKIE: [Deleted, Added, Updated] files", "blue"), end=" = [")
    print(colored(len(old_files), "red"), end=", ")
    print(colored(len(new_files), "green"), end=", ")
    print(colored(len(this_files) - len(old_files) - len(new_files), "yellow"), end="")
    print("]")

    return None


@app.command()
def rollback(commit_sha: str = "", path: str = PATH) -> None:
    """
    @desc\t
        rollsback to the version of the directory during a particular commit

    @params\t
        commit_sha: sha of the commit
        path: path of the duck repository
        indent: should indent the log file `.duck/duck.log.json`

    @return\t
        None
    """

    # TODO(#3): Complete rollback command

    duck_dir_path = join(path, ".duck")
    log_file_path = join(duck_dir_path, LOG_FILE_NAME)
    commits_dir_path = join(duck_dir_path, COMMITS)

    try:
        with open(log_file_path, "r") as file:
            pass
    except:
        error("ERROR: First init the repository using `python duck.py init`")

    with open(log_file_path, "r") as file:
        log_file = load(file)
    all_commits = log_file[COMMITS]

    if commit_sha == "":
        commits = [
            inquirer.List(
                "commit",
                message="Select commit for info",
                choices=log_file[TIMELINE],
            ),
        ]
        answers = inquirer.prompt(commits)
        commit_sha = answers["commit"]
    elif commit_sha not in log_file[TIMELINE]:
        error("ERROR: Not a valid commit SHA", info=False)
    this_commit_files = log_file[COMMITS][commit_sha]

    return None


@app.command()
def diff(file_path: str, path: str = PATH) -> None:
    """
    @desc\t
        spits out the difference in the current version of the file with the commited version of the file

    @params\t
        file_path: name of the file
        path: path of the duck repository

    @raises\t
        AssertionError: `file_path` specified does not exist

    @return\t
        None
    """

    duck_dir_path = join(path, ".duck")
    duck_log_file_path = join(duck_dir_path, LOG_FILE_NAME)
    try:
        with open(duck_log_file_path, "r"):
            pass
    except:
        error("ERROR: First init the repository using `python duck.py init`")

    with open(duck_log_file_path, "r") as file:
        log_file = load(file)

    assert exists(join(path, file_path)), "`file_path` specified does not exist"

    with open(join(path, file_path)) as file:
        cur_file_lines = file.readlines()

    file_change_log = get_file_change_log(
        original_file_lines=apply_commit_to_file(file_path, log_file[HEAD], path),
        updated_file_lines=cur_file_lines,
        include_common=True,
    )

    com_color = 0
    del_color = 1
    add_color = 2
    color_array = ["white", "red", "green"]
    symbol_array = [" ", "-", "+"]
    out = [(com_color, line) for line in file_change_log[COM]]
    for itr in file_change_log[DEL]:
        out.insert(itr, (del_color, file_change_log[DEL][itr]))
    for itr in file_change_log[ADD]:
        out.insert(itr, (add_color, file_change_log[ADD][itr]))

    for itr in out:
        line = itr[1].rstrip("\n")
        print(colored(f"{symbol_array[itr[0]]}\t{line}", color_array[itr[0]]))
    
    return None

@app.command()
def info(path: str = PATH, commit_sha: str = "") -> None:
    """
    @desc\t
        prints commit info to the console

    @params\t
        path: path of the duck repository
        commit_sha: commit_sha

    @return\t
        None
    """

    # TODO(#4): complete info command

    log_file_path = join(path, ".duck/duck.log.json")
    try:
        with open(log_file_path, "r") as file:
            pass
    except:
        error("ERROR: First init the repository using `python duck.py init`")
    with open(log_file_path, "r") as file:
        log_file = load(file)
        all_commits = log_file[COMMITS]
        if commit_sha == "":
            commits = [
                inquirer.List(
                    "commit",
                    message="Select commit for info",
                    choices=log_file[TIMELINE],
                ),
            ]
            answers = inquirer.prompt(commits)
            commit_sha = answers["commit"]
        elif commit_sha not in log_file[TIMELINE]:
            error("ERROR: Not a valid commit SHA", info=False)
        print(colored(""))

    return None


def error(message, info=True):
    """
    @desc\t
        prints error to the console

    @params\t
        message: error message
        info: flag for showing info to the console

    @exit\t
        1
    """

    print(colored(message, "red"))
    if info:
        print(colored("INFO : Do `python duck.py --help`", "magenta"))
    exit(1)


if __name__ == "__main__":
    app()
