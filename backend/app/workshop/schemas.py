from typing import Literal
from uuid import UUID
from pydantic import BaseModel,ConfigDict,Field,field_validator

class Input(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
class WorkshopInput(Input):
    name:str=Field(min_length=1,max_length=120)
class LoginInput(Input):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=False)
    email:str=Field(min_length=3,max_length=254)
    password:str=Field(min_length=1,max_length=256)
class CustomerInput(Input):
    name:str=Field(min_length=1,max_length=120)
    phone:str=Field(default='',max_length=40)
    notes:str=Field(default='',max_length=2000)
class VehicleEdit(Input):
    make:str=Field(min_length=1,max_length=60)
    model:str=Field(min_length=1,max_length=80)
    year:int=Field(ge=1900,le=2100)
    odometer:int=Field(ge=0,le=3000000)
    registration:str=Field(default='',max_length=40)
    source_identifier:str=Field(default='',max_length=100)
    is_demo:bool=False
class VehicleInput(VehicleEdit):
    customer_id:UUID
class JobInput(Input):
    customer_id:UUID
    vehicle_id:UUID
    complaint:str=Field(min_length=1,max_length=3000)
    idempotency_key:UUID
class JobEdit(Input):
    complaint:str=Field(min_length=1,max_length=3000)
    observations:str=Field(default='',max_length=5000)
    inspection:dict[str,Literal['not_checked','pass','attention']]=Field(default_factory=dict)
    status:Literal['draft','in_progress','reviewed','closed']='draft'
    @field_validator('inspection')
    @classmethod
    def known_checks(cls,value):
        if set(value)-{'brakes','tyres','lights','leaks','battery'}:
            raise ValueError('Unsupported inspection check')
        return value
class ReviewInput(Input):
    notes:str=Field(max_length=5000)
