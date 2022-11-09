
from typing import TypeVar
from schematics import Model

T = TypeVar("T", bound=Model)

def import_list(items: list[str], t: type[T]) -> list[T]:

    res = list()

    for i in items:
        res.append(t(i))
    
    return res

def export_list(itmes: list[Model]) -> list[object]:
    
    res = list()

    for i in itmes:
        res.append(i.to_primitive())
    
    return res
