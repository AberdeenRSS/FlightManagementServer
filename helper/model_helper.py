
from typing import Any, TypeVar, Union
from schematics import Model

T = TypeVar("T", bound=Model)

def import_list(items: Union[list[str], list[Any]], t: type[T]) -> list[T]:

    res = list()

    for i in items:
        res.append(t(i))
    
    return res

def export_list(itmes: list[T]) -> list[object]:
    
    res = list()

    for i in itmes:
        res.append(i.to_primitive())
    
    return res
