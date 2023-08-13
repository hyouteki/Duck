> **IMPORTANT**: Still in development
## Log structure
```
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
- head     : name of the latest commit
- timeline : stores the sequence of commits (sha)
- sha      : sha of that particular commit
- message  : commit message
- files    : logs of changes done in that commit
- new      : list of newly added files
- old      : list of deleted files
- changes  : logs of changes in existing files
- del      : list of deleted lines in that particular file
- add      : list of newly added lines in that particular file