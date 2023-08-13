# 🦆 Duck
Duck is a [VCS](https://en.wikipedia.org/wiki/Version_control) built from scratch in Python. Duck stores commits/logs in JSON format. 

> **IMPORTANT**: Still in development

## Duck is planned to have support for
- [x] initialization
- [ ] commit
- [ ] going back and forth between commits
- [ ] compression & decompression in files
- [ ] branching
- [ ] merging between branches
- [ ] executable/python module integration
- [ ] TODOs and ISSUEs

## Duck log structure
```
.duck
|
|___ commits
|   |___ init
|   |___ commit-1
|   |___ ...
|
|___ duck.log.json
    |___ head
    |___ commit timeline
    |___ commit sha
    	|___ message
    	|___ files
            |___ new
            |___ old
            |___ changes
            	|___ del
            	|___ add
```
- init: initial commited files
- commits: stores files that are either newly added or deleted in that commit
- head: name of the latest commit
- timeline: stores the sequence of commits (sha)
- sha: sha of that particular commit
- message: commit message
- files: logs of changes done in that commit
- new: list of newly added files
- old: list of deleted files
- changes: logs of changes in existing files
- del: list of deleted lines in that particular file
- add: list of newly added lines in that particular file

## TODO: Add documentation

## External modules required
- Typer
- Termcolor
