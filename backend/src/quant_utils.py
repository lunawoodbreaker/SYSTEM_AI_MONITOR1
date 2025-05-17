import os
import torch
import numpy as np
from typing import List, Dict, Any

def make_dir_safe(path: str) -> None:
    os.makedirs(r"{}".format(path), exist_ok=True, mode=0o777)

def get_module_by_name(model: torch.nn.Module, name: str) -> torch.nn.Module:
    names = name.split('.')
    module = model
    for n in names:
        module = getattr(module, n)
    return module

def set_module_by_name(model: torch.nn.Module, name: str, module: torch.nn.Module) -> None:
    names = name.split('.')
    parent = get_module_by_name(model, '.'.join(names[:-1]))
    setattr(parent, names[-1], module)

def cleanup() -> None:
    torch.cuda.empty_cache()
