from odoo.tools import config

from . import models
from . import wizard
from . import controllers

if config.get('test_enable'):
    from . import tests
    