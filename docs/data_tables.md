# Data tables

ZK devices have a database inside stored in the persistent memory. This database contains the read-only tables
(transaction history, input/output events) and writable tables (users, ACLs, timezone settings). You can make a query to
one table at a time, no joins or something similar are supported.

`pyzkaccess` provides the interface for making queries to these tables. Every table is presented as a model class
with the same fields. A QuerySet class helps build a query and iterate over the results. Basically, for those who
worked with ORM packages (Object-related mapping), such approach could be familiar.

The table data is stored on device in string format, sometimes additionally encoded. However the `pyzkaccess`
knows what the actual type every field should have and how to encode/decode it. Every model, that "wraps" a particular
device table, provides (and accepts when you write data to device) the decoded value in right Python type.

For example, the `transaction.Time_second` field contains an integer with encoded datetime, but appropriate
`Transaction.time` exposes the `datetime` objects.

The following sections describe how to work with table records, make queries and update the data.

## Models

Models are the following:

* `User` - device users, the card number information table
* `UserAuthorize` - user privilege list
* `Holiday` - holiday settings
* `Timezone` - (very detailed) timezone settings
* `Transaction` - access control transaction history
* `FirstCard` - first card settings
* `MultiCard` - multi-card settings
* `InOutFun` - input/output function settings
* `TemplateV10` - *SDK docs doesn't give a clue what this table for*

Model class represents whole data table, whereas a model object is a particular record in this table.

In order to create an object, instantiate it with parameters.

```python
from pyzkaccess.tables import User

my_user = User(card='123456', pin='123', password='555', super_authorize=True)
# ...code...
```

To get whole data as dict, use `.dict` property:

```python
from pyzkaccess.tables import User

my_user = User(card='123456', pin='123', password='555', super_authorize=True)
print(my_user.dict)
# {'card': '123456',
#  'pin': '123',
#  'password': '555',
#  'group': None,
#  'start_time': None,
#  'end_time': None,
#  'super_authorize': True}
```

Sometimes you may want to get the raw string data (i.e. how it stores on device) that are sent to a device on saving
an object. Use `raw_data` property for that:

```python
from pyzkaccess.tables import User

my_user = User(card='123456', pin='123', password='555', super_authorize=True)
print(my_user.raw_data)
# {'SuperAuthorize': '1', 'Password': '555', 'Pin': '123', 'CardNo': '123456'}
```

## Reading data

The `QuerySet` class is intended to build a query to a data table, execute it and obtain results. `QuerySet` supports
filtering (only equality is supported), limiting to unread records, to the certain fields, slicing the results.
All query restrictions and features are driven by PULL SDK and are the results of its limitations.

`QuerySet` uses lazy loading, which means it will not make a real request to device until you actually begin to
read its results.

To make a query, call the `zk.table(model)` method. The returned object will be an empty `QuerySet` bound with a
particular model class.

If you would read such queryset as-is, you'll simply get all records from the table:

```python
from pyzkaccess import ZKAccess

zk = ZKAccess('protocol=TCP,ipaddress=192.168.1.201,port=4370,timeout=4000,passwd=')
records = zk.table('User')
for record in records:
    print(record)  # prints all users from the table
```

To apply filters, use the `where()` method.

```python
from pyzkaccess import ZKAccess

zk = ZKAccess('protocol=TCP,ipaddress=192.168.1.201,port=4370,timeout=4000,passwd=')
records = zk.table('User').where(group='4', super_authorize=True)
for record in records:
    print(record)  # prints all superusers in group="4"
```

There are also available `only_fields()`, `unread()` methods. `count()` method returns the total records count
in a table without considering all filters. There are also available bulk write operations like `upsert()`, `delete()`,
`delete_all()` (see below).

Besides the iteration, you can use slicing, indexing, `len()` and `bool()` functions.

```python
records = zk.table('Model').condition(parameters).condition(parameters)
print("Result size:", len(records))
if records:
    print("Query result is not empty")
    print("First record:", records[0])
if len(records) > 3:
    print("First 3 records:", records[:3])
```

## Writing data

### Upsert (update or insert)

`QuerySet.upsert()` updates (if found) or inserts a record or records (if not).

```python
from pyzkaccess import ZKAccess
from pyzkaccess.tables import User

zk = ZKAccess('protocol=TCP,ipaddress=192.168.1.201,port=4370,timeout=4000,passwd=')
my_user = User(card='123456', pin='123', password='555', super_authorize=True)
zk.table(User).upsert(my_user)
```

`upsert()` function can receive the data in different formats:

* a model: `zk.table(User).upsert(User(card='123456', pin='123'))`
* a dict: `zk.table(User).upsert({'card': '123456', 'pin': '123'})`
* an iterable of models: `zk.table(User).upsert([User(card='123456', pin='123'), User(...)])`
* an iterable of dicts: `zk.table(User).upsert([{'card': '123456', 'pin': '123'}, {...}])`

### Insert one record

The `save()` method writes a record to the device. You may need also to pass a `ZKAccess` object by calling the
`with_zk()` method:

```python
from pyzkaccess import ZKAccess
from pyzkaccess.tables import User

zk = ZKAccess('protocol=TCP,ipaddress=192.168.1.201,port=4370,timeout=4000,passwd=')
my_user = User(card='123456', pin='123', password='555', super_authorize=True).with_zk(zk)
my_user.save()
```

### Update an existing record

```python
from pyzkaccess import ZKAccess

zk = ZKAccess('protocol=TCP,ipaddress=192.168.1.201,port=4370,timeout=4000,passwd=')
for record in zk.table('User'):
    record.group = '3'
    record.save()
```

### Delete records

`QuerySet.delete()` deletes a record or records from a table.

```python
from pyzkaccess import ZKAccess
from pyzkaccess.tables import User

zk = ZKAccess('protocol=TCP,ipaddress=192.168.1.201,port=4370,timeout=4000,passwd=')
my_user = User(card='123456', pin='123', password='555', super_authorize=True)
zk.table(User).delete(my_user)
```

`delete()` function can receive the data in different formats:

* a model: `zk.table(User).delete(User(card='123456', pin='123'))`
* a dict: `zk.table(User).delete({'card': '123456', 'pin': '123'})`
* an iterable of models: `zk.table(User).delete([User(card='123456', pin='123'), User(...)])`
* an iterable of dicts: `zk.table(User).delete([{'card': '123456', 'pin': '123'}, {...}])`

### Delete one record

```python
from pyzkaccess import ZKAccess
from pyzkaccess.tables import User

zk = ZKAccess('protocol=TCP,ipaddress=192.168.1.201,port=4370,timeout=4000,passwd=')
first_user = zk.table(User)[0]
first_user.delete()
```

You can also call the `delete()` method on a bare model object, you also need to pass a `ZKAccess` object by
calling the `with_zk()` method:

```python
from pyzkaccess import ZKAccess
from pyzkaccess.tables import User

zk = ZKAccess('protocol=TCP,ipaddress=192.168.1.201,port=4370,timeout=4000,passwd=')
my_user = User(card='123456', pin='123', password='555', super_authorize=True).with_zk(zk)
my_user.delete()
```

### Delete all selected records

This method deletes records that matched to a `QuerySet` object.

The following example deletes all transactions related to card "123456":

```python
zk.table('User').where(card='123456').delete_all()
```

## Building a query

### Filters

`QuerySet.where()` method applies a filter to a query. Only equality operation is supported (due to PULL SDK
restrictions). Repeated calls to `where()` are AND'ed. Several fields in one call are also AND'ed. Repeated appearance
of the same field in different calls will replace the previous value.

The following examples will produce identical queries:

```python
qs = zk.table('User').where(group='4', super_authorize=True)
qs = zk.table('User').where(group='4').where(super_authorize=True)
qs = zk.table('User').where(group='111').where(group='4', super_authorize=True)
  ```

Roughly speaking, the result will be the `group == '4' AND super_authorize == True`.

### Getting the unread records

The ZK device stores a pointer to the last read record in each table. Once a table is read, the pointer is moved to the
last record. We use this to track the unread records.

`QuerySet.unread()` method returns a new `QuerySet` containing only the records that has not been read yet since
the last query.

### Select fields to retrieve

`only_fields()` method returns a new `QuerySet` containing the records with only selected fields.
Other fields will be set to None. Repeated `only_fields()` call appends the fields selected in the previous
`only_fields()` calls.

The following examples will produce identical queries:

```python
from pyzkaccess.tables import User

qs = zk.table('User').only_fields('pin', 'password')
qs = zk.table('User').only_fields(User.pin, User.password)
qs = zk.table('User').only_fields('pin').only_fields('password')
qs = zk.table('User').only_fields(User.pin).only_fields(User.password)
```

Every record in the result will have only `pin` and `password` values, other fields will remain None.

### Data table size

`count()` method returns the total records count in table, ignoring all filters. This method is backed by a special
PULL SDK call.

If you want to know count of records contained in `QuerySet`, use `len(qs)`.

```python
from pyzkaccess import ZKAccess

zk = ZKAccess('protocol=TCP,ipaddress=192.168.1.201,port=4370,timeout=4000,passwd=')
qs = zk.table('User').where(group='4').where(super_authorize=True)
print('Superusers in group 4:', list(qs), 'Total users count:', qs.count())
```

## Retrieving results

`QuerySet` supports iterator protocol, slicing, indexing:

```python
# Print superusers
superusers = zk.table('User').where(super_authorize=True)
print('Superusers are:')
for i in superusers:
    print('Card:', i.card, '; Group:', i.group, '; From/to:', i.start_time, '/', i.end_time)

# Print cards from first 3 unread transactions for a given type and door
txns = zk.table('Transaction').where(event_type=0, door=1).unread()[:3]
cards = ', '.join(txn.card for txn in txns)
print('First card numbers:', cards)

# Print the first transaction
qs = zk.table('Transaction')
if qs.count() > 0:
    print('The first transaction:', qs[0])
else:
    print('Transaction table is empty!')
```
