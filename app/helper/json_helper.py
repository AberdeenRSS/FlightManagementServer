import json
from uuid import UUID


class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, UUID):
            # if the obj is uuid, we simply return the value of uuid
            return obj.hex
        return json.JSONEncoder.default(self, obj)
    
class PlainJsonSerializer:

    @staticmethod
    def dumps(*kargs, **kwargs):

        return json.dumps(*kargs, cls=UUIDEncoder, default=str, **kwargs)

    @staticmethod
    def loads( *kargs, **kwargs):

        return json.loads(*kargs, **kwargs)
        