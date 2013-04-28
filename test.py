import os
import sys
import numpy as np
sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))

import codefs
import util


class Person(object):
    def __init__(self, name, age):
        self.name = name
        self.age = age


class BiggerPerson(Person):
    @property
    def numbers(self):
        return np.array([[-1, 0, 1],
                         [1, 2, 3]])

def wrap(parent, obj, name):
    for t, wrapper in dir_wrappers:
        if isinstance(obj, t):
            return wrapper(parent, obj, name)
    else:
        return codefs.File(parent, obj, name)


def unwrap(wrapped):
    return wrapped.obj


class ObjectDirectory(codefs.Directory):
    def listdir(self):
        return [item.decode('utf-8') for item in dir(self.obj)
                if item[0] != '_' and not callable(item)]

    def __setitem__(self, key, val):
        setattr(self.obj, key, unwrap(val))

    def __getitem__(self, key):
        return wrap(self, getattr(self.obj, key), key)

    def __delitem__(self, key):
        delattr(self.obj, key)


class DictDirectory(codefs.Directory):
    def listdir(self):
        return list(self.obj)

    def __setitem__(self, key, val):
        self.obj[key] = unwrap(val)

    def __getitem__(self, key):
        return wrap(self, self.obj[key], key)

    def __delitem__(self, key):
        del self.obj[key]


dir_wrappers = [
    (dict, DictDirectory),
    (unicode, codefs.File),
    (Person, ObjectDirectory),
    (np.ndarray, util.CSVFile)
]

a = np.arange(100000)[:, None]
big_data = np.hstack((a, 2 * a, 3 * a))

data = {
    u'foo': {
        u'bar': 'blah blah',
        u'baz': 'baz baz baz'
    },
    u'quux': 'because',
    u'yxu': [1, 2, 3],
    u'wynand': Person('Wynand', 32),
    u'big_me': BiggerPerson('Wynand v2', 3200),
    u'bigfile.csv': big_data,
}


if __name__ == '__main__':
    codefs.make_server(wrap(None, data, '/'), 2121, 'user', '12345').serve_forever()
