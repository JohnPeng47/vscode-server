from .base import MotorModel
from .first_order import FirstOrderMotor
from .averaged_electrical import AveragedElectricalMotor

MOTORS = {
    "first_order": FirstOrderMotor,
    "averaged_electrical": AveragedElectricalMotor,
}


def make_motor(name: str, **kwargs) -> MotorModel:
    return MOTORS[name](**kwargs)
