from json import dump, load
from shutil import rmtree, copyfile
from os import getcwd, mkdir, listdir
from os.path import isfile, join, exists
from typer import Typer, Argument, Option
from typing_extensions import Annotated
from typing import Optional
from inquirer import List as inquirerList, prompt as inquirerPrompt
from rich import print as richPrint
from rich.console import Console
from rich.table import Table


LOG_FILE_NAME = "duck.log.json"
EXECUTABLE = "python duck.py"
PATH = getcwd()
LOG = dict()
app = Typer(rich_markup_mode="rich")

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


def getFileChangeLog(
    oldFileLines: list, newFileLines: list, includeCommon: bool = False
) -> dict:
    """
    Compares old and new file content and spits out the change log

    PARAMETERS
    ----------
    - oldFileLines : list[str]
        - list of '\\n' seperated lines of old file
    - newFileLines : list[str]
        - list of '\\n' seperated lines of updated file
    - includeCommon : bool
        - flag for including common lines in change log

    RETURNS
    -------
    - log : dict
        - dict containing list of new/old lines
    """

    lenOld, lenNew = len(oldFileLines), len(newFileLines)

    # finding the longest common subsequence between both versions of the file
    dp = [[0 for _ in range(lenNew + 1)] for _ in range(lenOld + 1)]
    for i in range(1, lenOld + 1):
        for j in range(1, lenNew + 1):
            dp[i][j] = (
                1 + dp[i - 1][j - 1]
                if oldFileLines[i - 1] == newFileLines[j - 1]
                else max(dp[i - 1][j], dp[i][j - 1])
            )

    # finding the common lines between both versions of the file
    common = ["" for _ in range(dp[lenOld][lenNew])]
    ptrOld, ptrNew, ptrCom = lenOld, lenNew, dp[lenOld][lenNew] - 1
    while ptrOld > 0 and ptrNew > 0 and ptrCom >= 0:
        if oldFileLines[ptrOld - 1] == newFileLines[ptrNew - 1]:
            common[ptrCom] = oldFileLines[ptrOld - 1]
            ptrOld -= 1
            ptrCom -= 1
            ptrNew -= 1
        elif dp[ptrOld - 1][ptrNew] > dp[ptrOld][ptrNew - 1]:
            ptrOld -= 1
        else:
            ptrNew -= 1

    # {
    #     "add": {(lineNumber -> line), ...},
    #     "com": {line1, line2, ....},
    #     "del": {(lineNumber -> line), ...},
    # }
    fileChangeLog = dict()

    if includeCommon:
        fileChangeLog[COM] = common

    # dict of deleted lines
    # {(lineNumber -> line), ...}
    delLog = dict()
    ptrCom = 0
    for i in range(lenOld):
        if ptrCom == len(common):
            delLog[i] = oldFileLines[i]
        elif oldFileLines[i] == common[ptrCom]:
            ptrCom += 1
        else:
            delLog[i] = oldFileLines[i]
    fileChangeLog[DEL] = delLog

    # dict of newly added lines
    # {(lineNumber -> line), ...}
    addLog = dict()
    ptrCom = 0
    for i in range(lenNew):
        if i >= len(common):
            addLog[i] = newFileLines[i]
        elif newFileLines[i] == common[ptrCom]:
            ptrCom += 1
        else:
            addLog[i] = newFileLines[i]
    fileChangeLog[ADD] = addLog

    return fileChangeLog


def doesFileExistsInThisCommit(
    filename: str, commitSha: str, duckLogFile: dict
) -> bool:
    """
    Checks whether a certain file exists in given commit or not

    PARAMETERS
    ----------
    - filename : str
        - name of the file
    - commitSha : str
        - sha of the commit
    - duckLogFile : dict
        - log file located at `.duck/duck.log.json`

    RETURNS
    -------
    - flag : bool
        - whether file exists or not
    """
    return (
        filename in duckLogFile[COMMITS][commitSha][FILES][CHANGES]
        or filename in duckLogFile[COMMITS][commitSha][FILES][NEW]
    )


def applyCommitToFile(filename: str, commitSha: str, path: str = PATH) -> list:
    """
    Returns the version of the file `filename` during the commit `commitSha`

    PARAMETERS
    ----------
    - filename : str
        - name of the file
    - commitSha : str
        - sha of the commit
    - path : str
        - default = `PATH` = `getcwd()`
        - path the duck repository

    RETURNS
    -------
    - fileLines : list[str]
        - list of '\\n' seperated lines of the file `filename`
    """

    duckDirPath = join(path, ".duck")
    with open(join(duckDirPath, LOG_FILE_NAME), "r") as file:
        duckLogFile = load(file)
    timeline = duckLogFile[TIMELINE]

    # finding first commit that includes this file `filename` before commit `commitSha`
    firstCommitIndex = -1
    thisCommitIndex = -1
    for i in range(len(timeline) - 1, -1, -1):
        if timeline[i] == commitSha:
            firstCommitIndex = i
            thisCommitIndex = i
        if firstCommitIndex == -1:
            continue
        if doesFileExistsInThisCommit(filename, commitSha, duckLogFile):
            firstCommitIndex = i
        else:
            break

    if not exists(join(path, filename)):
        error(f"[ERROR] {filename} does not exist in any commit", info=False)

    with open(join(duckDirPath, COMMITS, timeline[firstCommitIndex], filename)) as file:
        lines = file.readlines()
        # applying changes at each commit from first commit to this commit
        for i in range(firstCommitIndex + 1, thisCommitIndex + 1):
            fileChangeLog = duckLogFile[COMMITS][timeline[i]][FILES][CHANGES][filename]
            # converting to common file
            common = [
                lines[i] for i in range(len(lines)) if str(i) not in fileChangeLog[DEL]
            ]
            # adding newly added lines of this commit
            for change in fileChangeLog[ADD]:
                common.insert(int(change), fileChangeLog[ADD][change])
            lines = common

    return lines


@app.command()
def init(
    path: Annotated[str, Option(help="Path to the duck repository `.duck`")] = PATH,
    indent: Annotated[
        bool,
        Option(
            help="Flag indicating whether to indent the log file `.duck/duck.log.json`"
        ),
    ] = False,
) -> None:
    """
    Initializes the directory at the path `path` as the duck repository.
    """

    if not exists(path):
        error("[ERROR] Invalid path found", info=False)
    duckDirPath = join(path, ".duck")
    try:
        # deletes the ./duck dir if any
        rmtree(duckDirPath, ignore_errors=False, onerror=None)
    except:
        pass

    duckCommitsDirPath = join(duckDirPath, COMMITS)
    initCommitDirPath = join(duckCommitsDirPath, INIT)
    mkdir(duckDirPath)
    mkdir(duckCommitsDirPath)
    mkdir(initCommitDirPath)

    duckLogFile = dict()
    duckLogFile[HEAD] = INIT
    duckLogFile[TIMELINE] = [INIT]
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
    duckLogFile[COMMITS] = commits

    # filling log
    with open(join(duckDirPath, LOG_FILE_NAME), "w") as log:
        dump(duckLogFile, log, indent=4 if indent else 0)

    # copying files
    fileCount = 0
    for file in listdir(path):
        if isfile(join(path, file)):
            originalPath = join(path, file)
            copiedPath = join(initCommitDirPath, file)
            copyfile(originalPath, copiedPath)
            fileCount += 1

    richPrint(
        f"[blue][COOKIE] Initialized {fileCount} files in directory `{path}`[/blue]"
    )

    return None


@app.command()
def commit(
    message: Annotated[str, Argument(help="Commit message")],
    path: Annotated[str, Option(help="Path to the duck repository `.duck`")] = PATH,
    indent: Annotated[
        bool,
        Option(
            help="Flag indicating whether to indent the log file `.duck/duck.log.json`"
        ),
    ] = False,
) -> None:
    """
    Commits the current version of the directory at the path `path`.
    """

    # TODO(#2): Add support for not commiting if no changes are present
    duckDirPath = join(path, ".duck")
    duckLogFilePath = join(duckDirPath, LOG_FILE_NAME)

    if not exists(duckLogFilePath):
        error(f"[ERROR] First init the repository using `{EXECUTABLE} init`")

    with open(duckLogFilePath, "r") as file:
        duckLogFile = load(file)

    head = duckLogFile[HEAD]
    timeline = duckLogFile[TIMELINE]
    commitHead = duckLogFile[COMMITS][head]

    # TODO(#1): add support for recursively intializing the directories ↴

    thisFiles = [file for file in listdir(path) if isfile(join(path, file))]
    headFiles = commitHead[FILES][NEW]
    headFiles.extend([file for file in commitHead[FILES][CHANGES]])
    itrFiles = set(thisFiles + headFiles)
    newFiles = []
    oldFiles = []

    changeFiles = dict()
    commitName = f"commit-{len(timeline)}"
    thisCommitDirPath = join(duckDirPath, COMMITS, commitName)
    mkdir(thisCommitDirPath)

    for file in itrFiles:
        if file in thisFiles:
            if file in headFiles:
                with open(join(path, file)) as f:
                    thisFileLines = f.readlines()
                    changeFiles[file] = getFileChangeLog(
                        applyCommitToFile(file, head, path), thisFileLines
                    )
            else:
                newFiles.append(file)
                originalPath = join(path, file)
                copiedPath = join(thisCommitDirPath, file)
                copyfile(originalPath, copiedPath)
        elif file in headFiles:
            oldFiles.append(file)

    duckLogFile[TIMELINE].append(commitName)
    duckLogFile[HEAD] = commitName
    thisCommitDict = dict()
    thisCommitDict[MESSAGE] = message
    thisCommitFilesDict = dict()
    thisCommitFilesDict[NEW] = newFiles
    thisCommitFilesDict[OLD] = oldFiles
    thisCommitFilesDict[CHANGES] = changeFiles
    thisCommitDict[FILES] = thisCommitFilesDict
    duckLogFile[COMMITS][commitName] = thisCommitDict

    with open(duckLogFilePath, "w") as file:
        dump(duckLogFile, file, indent=4 if indent else 0)

    console = Console()
    commitTable = Table("Commit SHA", commitName)
    commitTable.add_row("Commit Message", message)
    commitTable.add_row("Committed in directory", path)
    commitTable.add_row(
        "Changed [Deleted, Added, Updated] files",
        f"[[red]{len(oldFiles)}[/red], [green]{len(newFiles)}[/green], [yellow]{len(thisFiles) - len(oldFiles) - len(newFiles)}[/yellow]",
    )
    console.print(commitTable)

    return None


@app.command()
def rollback(commit_sha: str = "", path: str = PATH) -> None:
    """"""
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
        error(f"ERROR: First init the repository using `{EXECUTABLE} init`")

    with open(log_file_path, "r") as file:
        log_file = load(file)
    all_commits = log_file[COMMITS]

    if commit_sha == "":
        commits = [
            inquirerList(
                "commit",
                message="Select commit for info",
                choices=log_file[TIMELINE],
            ),
        ]
        answers = inquirerPrompt(commits)
        commit_sha = answers["commit"]
    elif commit_sha not in log_file[TIMELINE]:
        error("ERROR: Not a valid commit SHA", info=False)
    this_commit_files = log_file[COMMITS][commit_sha]

    return None


@app.command()
def diff(
    filename: Annotated[str, Argument(help="Name of the file")],
    path: Annotated[str, Option(help="Path to the duck repository `.duck`")] = PATH,
) -> None:
    """
    Spits out the difference between the current file version with the latest committed version.
    """

    duckLogFilePath = join(path, ".duck", LOG_FILE_NAME)

    if not exists(duckLogFilePath):
        error(f"[ERROR] First init the repository using `{EXECUTABLE} init`")

    with open(duckLogFilePath, "r") as file:
        duckLogFile = load(file)

    if not exists(join(path, filename)):
        error(f"[ERROR] {filename} does not exist", info=False)

    with open(join(path, filename)) as file:
        curFileLines = file.readlines()

    fileChangeLog = getFileChangeLog(
        oldFileLines=applyCommitToFile(filename, duckLogFile[HEAD], path),
        newFileLines=curFileLines,
        includeCommon=True,
    )

    comColor = 0
    delColor = 1
    addColor = 2
    colorArray = ["white", "red", "green"]
    SymbolArray = ["===", "---", "+++"]

    out = [(comColor, line) for line in fileChangeLog[COM]]
    for itr in fileChangeLog[DEL]:
        out.insert(itr, (delColor, fileChangeLog[DEL][itr]))
    for itr in fileChangeLog[ADD]:
        out.insert(itr, (addColor, fileChangeLog[ADD][itr]))

    for itr in out:
        line = itr[1].rstrip("\n")
        richPrint(
            f"[{colorArray[itr[0]]}]{SymbolArray[itr[0]]}\t{line}[/{colorArray[itr[0]]}]"
        )

    return None


@app.command()
def info(
    commit: Annotated[Optional[str], Argument(help="Commit sha")] = None,
    path: Annotated[str, Option(help="Path to the duck repository `.duck`")] = PATH,
) -> None:
    """
    Spits info of the mentioned commit to the console.
    """

    duckLogFilePath = join(path, ".duck/duck.log.json")

    if not exists(duckLogFilePath):
        error(f"[ERROR] First init the repository using `{EXECUTABLE} init`")

    with open(duckLogFilePath, "r") as file:
        duckLogFile = load(file)

    if commit is None:
        chosenCommit = [
            inquirerList(
                "commit",
                message="Select commit for more information",
                choices=duckLogFile[TIMELINE],
            ),
        ]
        answer = inquirerPrompt(chosenCommit)
        commit = answer["commit"]

    if commit not in duckLogFile[COMMITS]:
        error("Not a valid commit SHA")

    commitDict = duckLogFile[COMMITS][commit]

    console = Console()

    richPrint(f"Message: [blue]{commitDict['message']}[/blue]")
    newFilesTable = Table("Newly added files")
    for file in commitDict[FILES][NEW]:
        newFilesTable.add_row(file)
    console.print(newFilesTable)
    oldFilesTable = Table("Deleted files")
    for file in commitDict[FILES][OLD]:
        oldFilesTable.add_row(file)
    console.print(oldFilesTable)
    changedFileTable = Table("Files", "Changes")
    for file in commitDict[FILES][CHANGES]:
        changedFileTable.add_row(
            file,
            f"[[red]{len(commitDict[FILES][CHANGES][file][DEL])}[/red], [green]{len(commitDict[FILES][CHANGES][file][ADD])}[/green]]",
        )
    console.print(changedFileTable)
    return None


@app.command()
def status(
    path: Annotated[str, Option(help="Path to the duck repository `.duck`")] = PATH,
) -> None:
    """
    Compares the files in current version of repository with the files in the latest committed version.
    """

    duckLogFilePath = join(path, ".duck", LOG_FILE_NAME)

    if not exists(duckLogFilePath):
        error(f"[ERROR] First init the repository using `{EXECUTABLE} init`")

    with open(duckLogFilePath, "r") as file:
        duckLogFile = load(file)

    head = duckLogFile[HEAD]
    commitHead = duckLogFile[COMMITS][head]
    thisFiles = [file for file in listdir(path) if isfile(join(path, file))]
    headFiles = commitHead[FILES][NEW]
    headFiles.extend([file for file in commitHead[FILES][CHANGES]])
    itrFiles = set(thisFiles + headFiles)
    newFiles = []
    oldFiles = []
    changedFiles = []

    for file in itrFiles:
        if file in thisFiles:
            if file in headFiles:
                with open(join(path, file)) as f:
                    thisFileLines = f.readlines()
                    fileChangeLog = getFileChangeLog(
                        applyCommitToFile(file, head, path), thisFileLines
                    )
                    if len(fileChangeLog[ADD]) != 0 or len(fileChangeLog[DEL]) != 0:
                        changedFiles.append(file)
            else:
                newFiles.append(file)
        elif file in headFiles:
            oldFiles.append(file)

    if len(newFiles) == 0 and len(oldFiles) == 0 and len(changedFiles) == 0:
        richPrint("[blue][COOKIE] Nothing to commit; everything up to date[/blue]")
        return None

    console = Console()

    if len(newFiles) != 0:
        newFilesTable = Table("Newly Added Files")
        for file in newFiles:
            newFilesTable.add_row(f"[red]{file}[/red]")
        console.print(newFilesTable)
    if len(oldFiles) != 0:
        oldFilesTable = Table("Deleted Files")
        for file in oldFiles:
            oldFilesTable.add_row(f"[red]{file}[/red]")
        console.print(oldFilesTable)
    if len(changedFiles) != 0:
        changedFileTable = Table("Changed Files")
        for file in changedFiles:
            changedFileTable.add_row(f"[red]{file}[/red]")
        console.print(changedFileTable)
    richPrint(
        f"[magenta][INFO] Type `{EXECUTABLE} commit --help` for info on how to commit[/magenta]"
    )
    return None


def error(message, info=True):
    """
    Prints error to the console

    PARAMETERS
    ----------
    - message : str
        - error message
    - info : bool
        - flag for indicating whether to show info to the console

    EXITS
    -----
    1
    """

    richPrint(f"[red]{message}[/red]")
    if info:
        richPrint(f"[magenta][INFO] Type `{EXECUTABLE} --help`[/magenta]")
    exit(1)


if __name__ == "__main__":
    app()
