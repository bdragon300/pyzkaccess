# Command-line interface

CLI interface uses command/subcommand chain approach. Typical CLI usage is:

Commands for a connected device:

```console
$ pyzkaccess connect <ip> <subcommand|group> [parameters] [<subcommand> [parameters] ...]
```

* Commands not related to a particular device:
```console
$ pyzkaccess <command> [parameters]
```

By default, all input consumes from stdin, and all output prints on stdout. You can specify a file
instead by setting `--file` parameter.

CLI gives access to most of PyZKAccess features. Also, it is supported the ascii tables in console 
or CSV format.

Every command, group and subcommand has its own help contents, just type them and append 
`--help` at the end. For example, here is the help for `connect` command:

```console
$ pyzkaccess connect --help
```

Or for `where` subcommand of `table` subcommand:

```console
$ pyzkaccess connect 192.168.1.201 table User where --help
```
