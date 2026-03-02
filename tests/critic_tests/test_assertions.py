from datetime import timedelta

import httpx
import pytest

from critic.libs.assertions import Assertion


RESPONSE_TIME_ASSERTION = {'assertion_string': 'response_time < 20.2'}
STATUS_CODE_ASSERTION = {'assertion_string': 'status_code == 200'}
BODY_ASSERTION = {'assertion_string': 'body contains "foo bar"'}
BAD_OP_ASSERTION = {'assertion_string': 'status_code foo 200'}
BAD_SUBJECT_ASSERTION = {'assertion_string': 'bad_subject > 200'}
BAD_EV_ASSERTION = {'assertion_string': 'status_code > "foo bar"'}
TOO_LONG_ASSERTION = {'assertion_string': 'status_code > 200 hello'}
TOO_SHORT_ASSERTION = {'assertion_string': 'status_code'}


def custom_response(request: httpx.Request):
    resp = httpx.Response(status_code=200, text='foo bar')
    # Manually set the elapsed time to 500ms
    resp.elapsed = timedelta(milliseconds=20.1)
    return resp


class TestAssertions:
    def test_assertion_validation_fails_with_bad_operator(self):
        with pytest.raises(ValueError, match='is not a valid operator'):
            Assertion(**BAD_OP_ASSERTION)

    def test_assertion_validation_fails_with_bad_Assertion_subject(self):
        with pytest.raises(ValueError, match='is not a valid Assertion Subject'):
            Assertion(**BAD_SUBJECT_ASSERTION)

    def test_assertion_validation_fails_with_bad_expected_value_casting(self):
        with pytest.raises(ValueError, match='is not valid for status_code'):
            Assertion(**BAD_EV_ASSERTION)

    def test_assertion_validation_fails_as_too_long_and_short(self):
        with pytest.raises(ValueError, match='has more or less than 3 parts'):
            Assertion(**TOO_LONG_ASSERTION)
        with pytest.raises(ValueError, match='has more or less than 3 parts'):
            Assertion(**TOO_SHORT_ASSERTION)

    def test_assertion_validation_correct(self):
        assertion = Assertion(**STATUS_CODE_ASSERTION)
        assert assertion.assertion_string == 'status_code == 200'
        assert assertion.assertion_operator == '=='
        assert assertion.assertion_expected_value == 200

        assertion = Assertion(**RESPONSE_TIME_ASSERTION)
        assert assertion.assertion_operator == '<'
        assert assertion.assertion_expected_value == 20.2

        assertion = Assertion(**BODY_ASSERTION)
        assert assertion.assertion_operator == 'contains'
        assert assertion.assertion_expected_value == 'foo bar'

    def test_assertion_serialize_correctly(self):
        assertion = Assertion(assertion_string='status_code > 200')
        assert assertion.serialize_model() == 'status_code > 200'

    def test_assertion_evaluates_correctly(self, httpx_mock):
        assertion_status_code = Assertion(**STATUS_CODE_ASSERTION)
        assertion_resp_time = Assertion(**RESPONSE_TIME_ASSERTION)
        assertion_body = Assertion(**BODY_ASSERTION)

        resp = httpx.Response(status_code=200, text='foo bar')
        resp.elapsed = timedelta(milliseconds=20.1)

        status_code_eval: tuple[bool, str] = assertion_status_code.evaluate(response=resp)
        assert status_code_eval[0]
        assert status_code_eval[1] is None

        resp_time_eval: tuple[bool, str] = assertion_resp_time.evaluate(response=resp)
        assert resp_time_eval[0]
        assert resp_time_eval[1] is None

        assertion_body: tuple[bool, str] = assertion_body.evaluate(response=resp)
        assert resp_time_eval[0]
        assert resp_time_eval[1] is None
