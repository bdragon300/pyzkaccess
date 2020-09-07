# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to
[Python Versioning](https://www.python.org/dev/peps/pep-0440/#public-version-identifiers).

## [0.2]
### Added
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
