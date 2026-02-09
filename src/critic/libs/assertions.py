from collections.abc import Callable
from enum import Enum
import operator
import re
from typing import ClassVar

import httpx
from pydantic import BaseModel, model_validator


class AssertionSubject(str, Enum):
    STATUS_CODE = 'status_code'
    BODY = 'body'
    RESPONSE_TIME = 'response_time'


"""
This class should take in strings like "status_code < 400" or "body contains 'foo'"
We can then evaluate operator(<given httpx data field actual value>, expected value)
"""


class Assertion(BaseModel):
    assertion_string: str
    assertion_object: AssertionSubject
    assertion_operator: str
    assertion_actual_value: str

    # Shared by all
    _OPS: ClassVar[dict[str, Callable]] = {
        '==': operator.eq,
        '!=': operator.ne,
        '<': operator.lt,
        '>': operator.gt,
        '<=': operator.le,
        '>=': operator.ge,
        'contains': lambda a, b: b in a,
        'not contains': lambda a, b: b not in a,
        'matches': lambda a, b: bool(re.search(b, a)),
    }

    @model_validator(mode='before')
    @classmethod
    def _parse_string(cls, data: dict):
        # TODO this will parse the string and set the objects
        if isinstance(data, dict) and 'assertion_string' in data:
            raw_string: str = data['assertion_string']

            parts = raw_string.split(' ')

            """
            Things that can go wrong:
                1. More than 3 parts
                2. assertion subject must be one of the assertion subject possibilities
                3. valid operator
                4. expected value must map to the correct value that this will make
            """

            if len(parts) != 3:
                raise ValueError(
                    f'Invalid assertion format: {raw_string} has more or less than 3 parts'
                )
            if parts[0] not in AssertionSubject:
                raise ValueError(
                    f'Invalid assertion format: {parts[0]} is not a valid Assertion Subject'
                )

            if parts[1] not in cls._OPS:
                raise ValueError(f'Invalid assertion format: {parts[1]} is not a valid operator')
            data['assertion_object'] = parts[0]
            data['assertion_operator'] = parts[1]
            data['assertion_actual_value'] = parts[2]

        return data

    # Return true and empty string if true and false with a string explaining what failed otherwise
    def evaluate(self, response: httpx.Response) -> tuple[bool, str]:
        op_func = self._OPS.get(self.assertion_operator)

        if not op_func:
            return False, f'Unknown operator: {self.assertion_operator}'

        # Get the actual value from the response based on the subject
        actual = None
        if self.assertion_object == AssertionSubject.STATUS_CODE:
            actual = response.status_code
            expected = int(self.assertion_actual_value)
        elif self.assertion_object == AssertionSubject.BODY:
            actual = response.text
            expected = self.assertion_actual_value
        elif self.assertion_object == AssertionSubject.RESPONSE_TIME:
            actual = response.elapsed.total_seconds()
            expected = float(self.assertion_actual_value)

        try:
            success = op_func(actual, expected)
            if success:
                return True, ''
            return (
                False,
                f'Expected {self.assertion_object} {self.assertion_operator} \
                {expected}, but got {actual}',
            )
        except Exception as e:
            return False, f'Error evaluating assertion: {e}'
