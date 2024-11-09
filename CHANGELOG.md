# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to
[Python Versioning](https://www.python.org/dev/peps/pep-0440/#public-version-identifiers).

## [1.1]

### Added

- Add pre-commit, code linters and apply them to codebase
- Use taskfile.dev for automation
- Build the portable Windows executable with PyInstaller
- Add missing type annotations
- Add `EventLog.where_or` method as alias for `EventLog.only` method
- Add `QuerySet.select` method as alias for `QuerySet.only_fields` method
- Get rid of printing the connection string in exception messages due to security reasons

#### CLI
- Make `1` and `0` as valid input for boolean values
- Add `events where_or` criteria as an alias for `events only`
- New subcommand `setup` that:
  - Checks the Windows (or wine) and Python versions
  - Asks where to install the PULL SDK from (if it has not installed): download from ZKTeco website, from local zip
    file or local directory
- `connect` subcommand now able to accept the connection options (including full connection string) from environment
  variables. Useful for passing the connection password securely.
- Fix mocking the SDK on non-windows platforms, showing incompatibility error (#11)
- Add IP and MAC addresses validation

### Changed

- Update dependencies
- Move from Travis CI to GitHub Actions
- Move to Poetry for dependency management
- Get rid of tox in favor of Poetry
- Update documentation: fix grammar, typos and formatting; add more examples
- Update docstrings: fix grammar, typos; add more examples
- Skip extra keys in device string instead of raising ValueError, which SearchDevices SDK function may return (#8)

#### CLI
- Fix parsing the boolean values in command line arguments
- Fix exception on applying the `select` subcommand if a single object (relay, aux input, etc.) is already selected
- Fix empty output on `events` subcommand
- Update help messages: fix grammar, typos; add more examples
- Show `--help` contents of subcommands without connecting to the device

### Removed

- Drop the python `3.5`, `3.6`, `3.7` support

## [1.0]

### Added
- Make a device data tables interface. Including making queries, changing and deleting records
- Add command-line interface
- Add alarm cancel function
- Add a device IP change function using a network broadcast method
- Add event type `206: Device start`
- Add python 3.9 support

### Changed
- Use Jekyll and pdoc3 instead of portray for documentation
- Upload github-pages to a separate branch
- Change docstrings format to Google style
- Fix empty relays list in `Door` objects with index in `DoorsList` > 0
- Fix `spring_daylight_time_mode1` and `fall_daylight_time_mode1` parameters value format
- Print one event by line and remove items collapsing in `EventLog` string representation
- Fix "no value" values handling in some paremeters
- Fix `search_devices` raises error when no devices found
- Rename `pyzkaccess.py` to `main.py` and `ctypes.py` to `ctypes_.py` in order to avoid
  possible import issues
- Change type of warning to `ImportWarning` when non-Windows platform is used

### Removed
- Remove documentation html contents from repo

## [0.2]
### Added
- Add codecov
- Add CI/CD
- Improve documentation and serve it on GitHub pages
- Add many tests
- Add `ZKSDKError` exception with PULL SDK and WINSOCK text error description
- Implement device and door parameters read/write with datatype control
- Add some enums
- Make event `poll()` method
- Implement connecting by `ZKDevice` object
- Add device search method
- Implement `DocDict` and `DocValue` classes in order to annotate SDK integer values
- Add restart device method
- Add fluent interface for events, readers, relays, aux inputs, doors with indexing support

### Changed
- Improve project description in `setup.py`
- Add `ctypes` wrapper module to be able to import the project modules on Linux
- Raise `ZKSDKError` instead of `RuntimeError` on SDK function failure
- BREAKING CHANGE. Keep number fields in `Event` as integers
- Make `EVENT_TYPES` as dict with annotateble values
- BREAKING CHANGE. ZKAccess connstr constructor parameter now must be keyword parameter and be
  `str` type instead of `bytes`
- Split project to several files
- BREAKING CHANGE. Split up `ZKAccess` class onto `ZKSDK` (implementation) and
  `ZKAccess` (interface). Move `zk*` methods to `ZKSDK`
- BREAKING CHANGE. Convert `ControlOperation`, `RelayGroup`, `VERIFY_MODES` to python `Enum`

### Removed
- BREAKING CHANGE. Remove `enable_relay*` and `read_events` methods

## [0.1]
### Added
- Implement reading events
- Implement switching relays
- Make enums related to SDK functions
- Write SDK installation info
