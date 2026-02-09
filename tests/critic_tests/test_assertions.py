import pytest

from critic.libs.assertions import Assertion


class TestAssertions:
    def test_assertion_validation_fails_with_bad_operator(self):
        with pytest.raises(ValueError, match='is not a valid operator'):
            data = {'assertion_string': 'status_code foo 200'}
            Assertion(**data)

    def test_assertion_validation_fails_with_bad_Assertion_sub(self):
        with pytest.raises(ValueError, match='is not a valid Assertion Subject'):
            data = {'assertion_string': 'bad_subject > 200'}
            Assertion(**data)

    def test_assertion_validation_fails_as_too_long_and_short(self):
        with pytest.raises(ValueError, match='has more or less than 3 parts'):
            data = {'assertion_string': 'status_code > 200 hello'}
            Assertion(**data)
        with pytest.raises(ValueError, match='has more or less than 3 parts'):
            data = {'assertion_string': 'status_code'}
            Assertion(**data)

    def test_assertion_validation_correct(self):
        data = {'assertion_string': 'status_code > 200'}
        assertion = Assertion(**data)
        assert assertion.assertion_string == 'status_code > 200'
        assert assertion.assertion_operator == '>'
        assert assertion.assertion_expected_value == 200

        data = {'assertion_string': 'response_time < 20.2'}
        assertion = Assertion(**data)
        assert assertion.assertion_operator == '<'
        assert assertion.assertion_expected_value == 20.2

    def test_assertion_serialize_correctly(self):
        data = {'assertion_string': 'status_code > 200'}
        assertion = Assertion(**data)
        assert assertion.serialize_model() == 'status_code > 200'
