import decimal
import json
from json import JSONDecodeError


class Encoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)


def dumps(obj):
    return json.dumps(obj, cls=Encoder)


def loads(string):
    return json.loads(string)
