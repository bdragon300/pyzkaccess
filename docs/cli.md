# Command-line interface

Command line interface consists of commands and subcommands, grouped in tree-like hierarchy.

The command tree is as follows:

```text
setup
search_devices
change_ip
connect <IP>
├ cancel_alarm
├ download_file <file_name>
├ upload_file <file_name>
├ read_raw <table_name>
├ write_raw <table_name>
├ restart
├ table <table_name>
│ ├ where --field=<value>, ...
│ │ └ ...recursive...
│ ├ unread
│ ├ upsert
│ ├ delete
│ ├ delete_all
│ └ count
├ aux_inputs
│ ├ select <index|range>
│ │ └ ...recursive...
│ └ events
│   └ *events* commands...
├ events
│ ├ only --field=<value>, ...
│ │ └...recursive...
│ └ poll
├ parameters
│ ├ list
│ └ set --parameter=<value>, ...
├ readers
│ ├ select <index|range>
│ │ └ ...recursive...
│ └ events
│   └ *events* commands...
├ relays
│ ├ select <index|range>
│ │ └ ...recursive...
│ └ switch_on
└ doors
  ├ select <index|range>
  │ └ ...recursive...
  ├ aux_inputs <index|range>
  │ └ *aux_input* commands...
  ├ events
  │ └ *events* commands...
  ├ parameters
  │ └ *parameters* commands...
  ├ readers
  │ └ *readers* commands...
  └ relays
    └ *relays* commands...
```

Commands and parameters in command line are followed by each other according to the tree structure.

For example, to poll the events of the first reader of the first door:

```console
$ pyzkaccess connect 192.168.0.201 doors select 1 readers select 1 events poll
```

Every command has its own help message. To get help for a command, just append `--help` at the end.
For example, the top-level help:

```console
$ pyzkaccess --help
```

Or for a subcommand:

```console
$ pyzkaccess connect 192.168.1.201 doors select 1 readers --help
```

## Connection options

The `connect` command makes a connection to the device. It requires the IP address of the device as the first argument.

```console
pyzkaccess connect 192.168.1.201
```

However you might need to pass the whole connection string, for example, if a device requires the password. But this
should not get revealed in the command line arguments by security reasons.
In this case, you can pass the options to the `connect` command via the environment variables:

* `PYZKACCESS_CONNECT_IP` or `PYZKACCESS_CONNECT_CONNSTR` -- IPv4 address or the whole connection string like this
    `PYZKACCESS_CONNECT_CONNSTR="protocol=TCP,ipaddress=192.168.1.201,port=4370,timeout=4000,passwd=123456"`
* `PYZKACCESS_CONNECT_MODEL` -- device model. Possible values are: `ZK100`, `ZK200`, `ZK400`
