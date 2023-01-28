
from typing import Any, TypeVar, Union, cast
from marshmallow import Schema, fields, post_load

U = TypeVar("U")

class SchemaExt(Schema):

    def load_safe(self, dataclass: type[U], data) -> U:
        return dataclass(self.load(data))

    def load_list_safe(self, dataclass: type[U], data) -> list[U]:
        return [dataclass(d) for d in cast(list, self.load(data, many=True))] 

    def dump_single(self, obj, **kwargs):
        return cast(dict[str, Any], self.dump(obj, **kwargs))

    def dump_list(self, obj_list, **kwargs):
        return cast(list[dict[str, Any]], self.dump(obj_list, many=True, **kwargs))

def make_safe_schema(dataclass: type):
    """
    Generates a schema that loads the object
    as the provided dataclass
    """

    class SchemaSafe(SchemaExt):

        @post_load
        def after_load(self, data, **kwargs):
            return dataclass(**data) # type: ignore

        def load_safe(self, dataclass: type[U], data) -> U:
            return cast(dataclass, self.load(data))
        
        def load_list_safe(self, dataclass: type[U], data) -> list[U]:
            return cast(list[dataclass], self.load(data, many=True))

    return SchemaSafe

T = TypeVar("T", bound=Schema)

# def import_list(items: Union[list[str], list[Any]], t: type[T]) -> list[T]:

#     res = list()

#     for i in items:
#         res.append(t(i))
    
#     return res

# def export_list(itmes: list[T]) -> list[object]:
    
#     res = list()

#     for i in itmes:
#         res.append(i.to_primitive())
    
#     return res
