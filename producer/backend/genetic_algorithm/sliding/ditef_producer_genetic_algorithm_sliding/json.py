import datetime
import numpy
import simplejson


class NumpyAndNanEncoder(simplejson.JSONEncoder):

    def default(self, value):
        if isinstance(value, numpy.integer):
            return int(value)
        elif isinstance(value, numpy.floating):
            return float(value)
        elif isinstance(value, numpy.ndarray):
            return value.tolist()
        elif isinstance(value, datetime.datetime):
            return value.__str__()
        return super().default(value)


def json_formatter_pretty(data):
        return simplejson.dumps(data, sort_keys=True, indent=4, ignore_nan=True, cls=NumpyAndNanEncoder)


def json_formatter_compressed(data):
    return simplejson.dumps(data, ignore_nan=True, cls=NumpyAndNanEncoder)