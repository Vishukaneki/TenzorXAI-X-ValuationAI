"""
schemas.py
----------
Pydantic request / response models.
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class ValuationRequest(BaseModel):
    # Mandatory
    locality:       str
    property_type:  str   # apartment | villa | plot | commercial
    subtype:        str   # 2BHK | villa | shop | etc.
    size_sqft:      float
    age_years:      float

    # Optional
    floor_num:       Optional[int]   = None
    total_floors:    Optional[int]   = None
    has_lift:        Optional[bool]  = None
    occupancy_status: Optional[str] = None   # self_occupied | rented | vacant
    legal_status:    Optional[str]  = None   # clear | disputed | pending
    rental_yield:    Optional[float] = None  # annual yield %
    latitude:        Optional[float] = None  # optional precise property geo
    longitude:       Optional[float] = None  # optional precise property geo


class WhatIfRequest(BaseModel):
    base_request: ValuationRequest
    perturbations: dict   # e.g. {"age_years": 5, "floor_num": 8}
