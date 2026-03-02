from collections.abc import Callable
from enum import Enum
import operator
import re
import shlex
from typing import Any, ClassVar

import httpx
from pydantic import BaseModel, model_serializer, model_validator


class AssertionSubject(str, Enum):
    STATUS_CODE = 'status_code'
    BODY = 'body'
    RESPONSE_TIME = 'response_time'

    def cast(self, value: str) -> Any:
        # Casting logic here is simpler than in the validation method
        if self == AssertionSubject.STATUS_CODE:
            return int(value)
        if self == AssertionSubject.RESPONSE_TIME:
            return float(value)
        return value


"""
This class should take in strings like "status_code < 400" or "body contains 'foo'"
We can then evaluate operator(<given httpx data field actual value>, expected value)
"""


class Assertion(BaseModel):
    assertion_string: str
    assertion_object: AssertionSubject
    assertion_operator: str
    assertion_expected_value: str | int | float

    # Shared by all
    _OPS: ClassVar[dict[str, Callable]] = {
        '==': operator.eq,
        '!=': operator.ne,
        '<': operator.lt,
        '>': operator.gt,
        '<=': operator.le,
        '>=': operator.ge,
        'contains': lambda a, b: b in a,
        'not_contains': lambda a, b: b not in a,
        'matches': lambda a, b: bool(re.search(b, a)),
    }

    @model_validator(mode='before')
    @classmethod
    def _parse_assertion(cls, data: dict):
        # TODO this will parse the string and set the objects
        if isinstance(data, str):
            data = {'assertion_string': data}

        if not isinstance(data, dict):
            raise ValueError(
                'Assertion must be initialized with a string or a dict containing assertion_string'
            )

        if 'assertion_string' in data:
            raw_string: str = data['assertion_string']
            """
            Things that can go wrong:
                1. More than 3 parts
                2. assertion subject must be one of the assertion subject possibilities
                3. valid operator
                4. expected value must map to the correct value that this will make
                5. Must be able to parse correctly for body, which may be a string or regex
            Parsing here will break the component into its 3 parts, since a body which may be
            a string or a regex will be surrounded by ""'s it will be parsed as one part and we
            can keep the 3 part format.
            """
            try:
                parts = shlex.split(raw_string)
            except ValueError as e:
                raise ValueError(
                    f'Invalid assertion format: unable to parse quotes in {raw_string}'
                ) from e

            if len(parts) != 3:
                raise ValueError(
                    f'Invalid assertion format: {raw_string} has more or less than 3 parts'
                )

            try:
                subject = AssertionSubject(parts[0])
            except ValueError as e:
                raise ValueError(
                    f'Invalid assertion format: {parts[0]} is not a valid Assertion Subject'
                ) from e

            if parts[1] not in cls._OPS:
                raise ValueError(f'Invalid assertion format: {parts[1]} is not a valid operator')

            try:
                converted_value = subject.cast(parts[2])
            except ValueError as e:
                raise ValueError(f"Value '{parts[2]}' is not valid for {subject.value}") from e

            data['assertion_object'] = parts[0]
            data['assertion_operator'] = parts[1]
            data['assertion_expected_value'] = converted_value

        return data

    @model_serializer(mode='plain')
    def serialize_model(self) -> str:
        return f'{self.assertion_string}'

    # Return true and empty string if true and false with a string explaining what failed otherwise
    def evaluate(self, response: httpx.Response) -> tuple[bool, str | None]:
        op_func = self._OPS[self.assertion_operator]

        if not op_func:
            return False, f'Unknown operator: {self.assertion_operator}'

        # Get the actual value from the response based on the subject
        actual = None
        expected = self.assertion_expected_value
        if self.assertion_object == AssertionSubject.STATUS_CODE:
            actual = response.status_code
        elif self.assertion_object == AssertionSubject.BODY:
            actual = response.text
        elif self.assertion_object == AssertionSubject.RESPONSE_TIME:
            actual = response.elapsed.total_seconds() * 1000

        try:
            print(op_func(actual, expected))
            success = op_func(actual, expected)
            if success:
                return True, None
            return (
                False,
                (
                    f'Expected {self.assertion_object} {self.assertion_operator} '
                    f'{expected}, but got {actual}'
                ),
            )
        except Exception as e:
            return False, f'Error evaluating assertion: {e}'
