# Device data tables

ZK devices have several tables in non-volatile data storage where a device keeps transaction
history, input/output events, and where user can manage users, ACLs, local time settings.

`pyzkaccess` provides interface to access, making queries and modify these tables. A table record
is presented as a python object with properties -- a model. Query objects helps to build a query
and to iterate over the results. Anyway, if you ever worked with any of popular ORM 
(Object-related mapping), such interface could be pretty familiar to you.

Device keeps all data in tables as strings, despite which type a particular field value has. 
Model provides a convenient way to work with data depening on actual type. For example, 
`transaction.Time_second` field contains an integer with encoded datetime, but appropriate 
`Transaction.time` allows to work with that value using usual `datetime` objects.

The following sections describe how to work with table records, make queries and update the data.

## Model objects

`pyzkaccess` contains pre-defined models that represent built-in tables in ZK devices. 
Model class represents whole data table, whereas a model object is a particular record in 
this table. 

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

Sometimes you may want to get the raw data (with string values) that are sent to a device on saving
an object. Use `raw_data` property for it:

```python
from pyzkaccess.tables import User

my_user = User(card='123456', pin='123', password='555', super_authorize=True)
print(my_user.raw_data)
# {'SuperAuthorize': '1', 'Password': '555', 'Pin': '123', 'CardNo': '123456'}
```

## Saving changes in objects

### `model.save()` method

The `save()` method is used to save changes in object. Manually created objects
(unlike retrieved from a query, see below) must know which connection to use, so also set it
by `with_zk()`:

```python
from pyzkaccess import ZKAccess
from pyzkaccess.tables import User

zk = ZKAccess('protocol=TCP,ipaddress=192.168.1.201,port=4370,timeout=4000,passwd=')
my_user = User(card='123456', pin='123', password='555', super_authorize=True).with_zk(zk)
my_user.save()
```

Processing the records obtained from table is pretty simple:

```python
from pyzkaccess import ZKAccess

zk = ZKAccess('protocol=TCP,ipaddress=192.168.1.201,port=4370,timeout=4000,passwd=')
for record in zk.table('User'):
    record.group = '3'
    record.save()
```

Any changes will not be actually saved in a record until `save()` will be called.

### `queryset.upsert()` method

Just saves particular records without considering `QuerySet` state. Returns nothing:

```python
from pyzkaccess import ZKAccess
from pyzkaccess.tables import User

zk = ZKAccess('protocol=TCP,ipaddress=192.168.1.201,port=4370,timeout=4000,passwd=')
my_user = User(card='123456', pin='123', password='555', super_authorize=True)
zk.table(User).upsert(my_user)
```

`upsert()` function accepts the following values:
* Model object: `zk.table(User).upsert(User(card='123456', pin='123'))`
* dict: `zk.table(User).upsert({'card': '123456', 'pin': '123'})`
* Iterable of objects: `zk.table(User).upsert([User(card='123456', pin='123'), User(...)])`
* Iterable of dicts: `zk.table(User).upsert([{'card': '123456', 'pin': '123'}, {...}])`

"Upsert" (update/insert) operation means that if such record already exists then it will get
updated, otherwise it will get inserted.

## Deleting objects

Deleting object is similar to saving.

### `model.delete()` method

Manually created objects (unlike retrieved from a query, see below) must know which connection 
to use, so also set it by `with_zk()`:

```python
from pyzkaccess import ZKAccess
from pyzkaccess.tables import User

zk = ZKAccess('protocol=TCP,ipaddress=192.168.1.201,port=4370,timeout=4000,passwd=')
my_user = User(card='123456', pin='123', password='555', super_authorize=True).with_zk(zk)
my_user.delete()
```

For queries:

```python
from pyzkaccess import ZKAccess

zk = ZKAccess('protocol=TCP,ipaddress=192.168.1.201,port=4370,timeout=4000,passwd=')
for record in zk.table('User'):
    record.delete()
```

### `queryset.delete()` method

Just deletes particular records without considering `QuerySet` state. Returns nothing.

```python
from pyzkaccess import ZKAccess
from pyzkaccess.tables import User

zk = ZKAccess('protocol=TCP,ipaddress=192.168.1.201,port=4370,timeout=4000,passwd=')
my_user = User(card='123456', pin='123', password='555', super_authorize=True)
zk.table(User).delete(my_user)
```

`delete()` function accepts the following:
* Model object: `zk.table(User).delete(User(card='123456', pin='123'))`
* dict: `zk.table(User).delete({'card': '123456', 'pin': '123'})`
* Iterable of objects: `zk.table(User).delete([User(card='123456', pin='123'), User(...)])`
* Iterable of dicts: `zk.table(User).delete([{'card': '123456', 'pin': '123'}, {...}])`


### `queryset.delete_all()` method

This method deletes records that matched to a `QuerySet` object. If results was not fetched yet, 
fetches them first. Returns nothing.

The following example deletes all transactions related to card "123456":

```python
zk.table('User').where(card='123456').delete_all()
```

## Making queries

The `QuerySet` class is intended to build a query to a data table, execute it and obtain results.
Its operations are limited to the ZK PULL SDK capabilities. `QuerySet` supports filtering (only
for equal condition), limiting to unread records, to the certain fields, slicing results.

`QuerySet` uses lazy loading, which means that it will not make a query and fetch the results 
until you started to iterate over it or to get element by index.

The common approach to work with a QuerySet is:

```python
records = zk.table('Model').limit1(parameters).limit2(parameters)[index_or_slice]
for record in records:
    ...
```

`QuerySet` is binded with a particular Model class, where queries are targeted to. New 
`QuerySet` is created by `ZKAccess.table(model)` function. As `model` parameter you can pass 
model's name, or it's class, or it's object.

The following examples works identically, they return empty `QuerySet` object binded with 
`User` model:

```python
from pyzkaccess.tables import User

qs = zk.table('User')
qs = zk.table(User)
qs = zk.table(User(pin='1', password='123'))
```

Some `QuerySet` methods return new object, the others not. Let's see what you can do with QuerySets.

### Building a query

#### Filtering

`where()` method returns a new `QuerySet` containing records that match the given filter parameters.
You can only use equality operation due to PULL SDK restriction. Several fields are AND'ed. 
Filters in repeated `where()` calls are also AND'ed with fields from previous calls. If this 
field has already set in previous call, it will be replaced with new value.

The following examples will produce identical queries: 

```python
qs = zk.table('User').where(group='4', super_authorize=True)
qs = zk.table('User').where(group='4').where(super_authorize=True)
qs = zk.table('User').where(group='111').where(group='4', super_authorize=True)
  ```

Resulting query conditions will be `group == '4' AND super_authorize == True`.

#### Only new records

`unread()` method returns a new `QuerySet` containing records that was not read yet.

All data tables on ZK device has a pointer which is set to the last record on each read query. If
no records have been inserted to a table since last read, the "unread" query will return nothing.

#### Query only listed fields

`only_fields()` method returns a new `QuerySet` containing records with only specified fields.
Other fields will be set to None. Fields in repeated `only_fields()` calls will be added to fields
from previous calls.

As a field name you can pass either a field name or model field object.

The following examples will produce identical queries: 

```python
from pyzkaccess.tables import User

qs = zk.table('User').only_fields('pin', 'password')
qs = zk.table('User').only_fields(User.pin, User.password)
qs = zk.table('User').only_fields('pin').only_fields('password')
qs = zk.table('User').only_fields(User.pin).only_fields(User.password)
```

Resulting records will have only `pin` and `password` field values, retrieved from table, 
other fields will remain None.

### Data table size

`count()` method returns total records count in records. Calling this method leads to a special
SDK call. Pay attention that this method does not consider conditions, it just returns total
records count in a table. It is an analogue of SQL query `SELECT COUNT(*) FROM table;`.

If you want to know count of records contained in `QuerySet`, use `len(qs)`.

## Retrieving results

`QuerySet` supports iterator protocol and also slicing, indexing. Some examples should help to
understand the approach:

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

### len()

When you apply `len()` on a `QuerySet` object, all matched results will be fetched from a device
and put to the cache. Unlike `count()` method, the `len()` returns actual results size.

### bool()

When you apply `bool()` on a `QuerySet` object, all matched results will be fetched from a device
and put to the cache. If there is any record was returned, returns `True`, or `False` otherwise.
