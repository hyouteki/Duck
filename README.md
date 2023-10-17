Duck is a [VCS](https://en.wikipedia.org/wiki/Version_control) built from scratch in Python. Duck stores commits/logs in JSON format. 

> **IMPORTANT**: Still in development

## Duck is planned to have support for
- [x] init
- [x] commit
- [x] diff
- [ ] rollback 
- [ ] compression & decompression in files
- [ ] making timeline a tree structure
- [ ] branching
- [ ] merging between branches
- [ ] recursive handling of subdirectories
- [ ] executable/python module integration
- [ ] TODOs and ISSUEs

## Duck log structure
```
.duck
|
|___ commits
|   |___ init
|   |___ commit number 1
|   |___ ...
|
|___ duck.log.json
    |___ head
    |___ commit timeline
    |___ commit SHA
    	|___ message
    	|___ files
            |___ new
            |___ old
            |___ changes
            	|___ del
            	|___ add
```
| name     | type         | description                                                                                                |
| :------- | :----------- | :--------------------------------------------------------------------------------------------------------- |
| init     | subdirectory | initially commited files                                                                                   |
| commits  | subdirectory | stores subdirectories which contain files that are either newly added or deleted in that particular commit |
| head     | string       | SHA of the latest commit                                                                                   |
| timeline | linked list  | stores the sequence of commits (SHA)                                                                       |
| SHA      | string       | SHA of that particular commit                                                                              |
| message  | string       | commit message                                                                                             |
| files    | JSON array   | logs of changes done in that commit                                                                        |
| new      | array        | list of newly added files                                                                                  |
| old      | array        | list of deleted files                                                                                      |
| changes  | json         | logs of changes in existing files                                                                          |
| del      | array        | list of deleted lines in that particular file                                                              |
| add      | array        | list of newly added lines in that particular file                                                          |

## Requirements
``` console
pip install typer termcolor inquirer
```

## TODO: Add documentation
