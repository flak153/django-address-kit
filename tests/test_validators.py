"""Comprehensive tests for US address validators in django-address-kit"""

import pytest
import re
from typing import Any, Callable
from django.core.exceptions import ValidationError

from django_address_kit.validators import (
    validate_state_code,
    validate_zip_code,
    validate_street_address,
    validate_po_box,
    state_code_validator,
    zip_code_validator,
)


class TestStateCodeValidator:
    """Tests for the state_code_validator RegexValidator"""

    @pytest.mark.parametrize("valid_code", ["CA", "NY", "TX", "PR", "AA", "GU"])
    def test_valid_state_codes(self, valid_code: str) -> None:
        """Test that RegexValidator accepts valid state codes"""
        state_code_validator(valid_code)

    @pytest.mark.parametrize(
        "invalid_code", ["", "1A", "abc", "CAN", "C", " CA ", "ZZ", "@A", "12"]
    )
    def test_invalid_state_codes(self, invalid_code: str) -> None:
        """Test that RegexValidator rejects invalid codes"""
        with pytest.raises(ValidationError):
            state_code_validator(invalid_code)


class TestZipCodeValidator:
    """Tests for the zip_code_validator RegexValidator"""

    @pytest.mark.parametrize(
        "valid_zip", ["12345", "90210", "00501", "99950", "12345-6789", "90210-1234"]
    )
    def test_valid_zip_codes(self, valid_zip: str) -> None:
        """Test that RegexValidator accepts valid ZIP codes"""
        zip_code_validator(valid_zip)

    @pytest.mark.parametrize(
        "invalid_zip",
        [
            "",
            "ABCDE",
            "1234",
            "123456",
            "12345-678",
            "12345-67890",
            "12345 6789",
            "12345!6789",
            "12A45",
        ],
    )
    def test_invalid_zip_codes(self, invalid_zip: str) -> None:
        """Test that RegexValidator rejects invalid ZIP codes"""
        with pytest.raises(ValidationError):
            zip_code_validator(invalid_zip)


class TestStateCodeValidation:
    """Enhanced state code validation tests"""

    @pytest.mark.parametrize("input_type", [0, ["CA"], {"state": "CA"}, object(), float("nan")])
    def test_attribute_error_non_string_inputs(self, input_type: Any) -> None:
        """Test that state code validation fails for non-string inputs"""
        with pytest.raises(ValidationError, match="required"):
            validate_state_code(input_type)

    def test_unicode_and_unicode_edge_cases(self) -> None:
        """Test unicode and unicode edge case handling for state codes"""
        unicode_test_cases = [
            "\u0043\u0041",  # Unicode representation of 'CA'
            "ＣＡ",  # Full-width chars
            "C A",  # Hidden characters
            "CA\u200B",  # Zero-width space
        ]

        for code in unicode_test_cases:
            with pytest.raises(ValidationError):
                validate_state_code(code)

    def test_sql_injection_attempts_state_code(self) -> None:
        """Test state code validation against potential SQL injection attempts"""
        sql_injection_attempts = [
            "'CA' OR 1=1 --",
            "CA' UNION SELECT * FROM users--",
            '"CA"; DROP TABLE users; --',
        ]

        for attempt in sql_injection_attempts:
            with pytest.raises(ValidationError):
                validate_state_code(attempt)

    def test_extremely_long_input(self) -> None:
        """Test state code validation with extremely long inputs"""
        too_long_code = "A" * 1000
        with pytest.raises(ValidationError):
            validate_state_code(too_long_code)

    def test_control_character_inputs(self) -> None:
        """Test handling of control characters in state code"""
        control_chars = [
            "\x00CA",  # Null byte
            "C\rA",  # Carriage return
            "C\nA",  # Newline
            "C\tA",  # Tab
            "\x1FCA",  # Control character
        ]

        for char_code in control_chars:
            with pytest.raises(ValidationError):
                validate_state_code(char_code)


class TestZipCodeValidation:
    """Enhanced ZIP code validation tests"""

    @pytest.mark.parametrize("leading_zero_case", ["00000", "00001", "00100", "09999"])
    def test_leading_zeros(self, leading_zero_case: str) -> None:
        """Test validation of ZIP codes with leading zeros"""
        validate_zip_code(leading_zero_case)

    @pytest.mark.parametrize("input_type", [0, ["12345"], {"zip": "12345"}, object(), float("nan")])
    def test_attribute_error_non_string_inputs(self, input_type: Any) -> None:
        """Test that ZIP code validation fails for non-string inputs"""
        with pytest.raises(ValidationError, match="required"):
            validate_zip_code(input_type)

    def test_unicode_edge_cases_zip(self) -> None:
        """Test unicode and unicode edge case handling for ZIP codes"""
        unicode_test_cases = [
            "\uFF11\uFF12\uFF13\uFF14\uFF15",  # Full-width numerals
            "１２３４５",  # Full-width digits
            "12345\u200B",  # Zero-width space
        ]

        for code in unicode_test_cases:
            with pytest.raises(ValidationError):
                validate_zip_code(code)

    def test_sql_injection_attempts_zip(self) -> None:
        """Test ZIP code validation against potential SQL injection attempts"""
        sql_injection_attempts = [
            "'12345' OR 1=1 --",
            "12345' UNION SELECT * FROM users--",
            '"12345"; DROP TABLE users; --',
        ]

        for attempt in sql_injection_attempts:
            with pytest.raises(ValidationError):
                validate_zip_code(attempt)

    def test_extremely_long_input_zip(self) -> None:
        """Test ZIP code validation with extremely long inputs"""
        too_long_zip = "1" * 1000
        with pytest.raises(ValidationError):
            validate_zip_code(too_long_zip)

    def test_control_character_inputs_zip(self) -> None:
        """Test handling of control characters in ZIP code"""
        control_chars = [
            "\x0012345",  # Null byte
            "1\r2345",  # Carriage return
            "1\n2345",  # Newline
            "1\t2345",  # Tab
            "\x1F12345",  # Control character
        ]

        for char_code in control_chars:
            with pytest.raises(ValidationError):
                validate_zip_code(char_code)


class TestStreetAddressValidation:
    """Enhanced street address validation tests"""

    @pytest.mark.parametrize(
        "fractional_address", ["123 1/2 Main St", "456 1/4 Oak Avenue", "789 3/4 Pine Boulevard"]
    )
    def test_fractional_house_numbers(self, fractional_address: str) -> None:
        """Test validation of street addresses with fractional house numbers"""
        validate_street_address(fractional_address)

    def test_very_long_street_names(self) -> None:
        """Test validation of street addresses with very long street names"""
        long_street_name = "123 " + ("A" * 250) + " Street"
        validate_street_address(long_street_name)

    @pytest.mark.parametrize(
        "input_type", [0, ["123 Main St"], {"address": "123 Main St"}, object(), float("nan")]
    )
    def test_attribute_error_non_string_inputs(self, input_type: Any) -> None:
        """Test that street address validation fails for non-string inputs"""
        with pytest.raises(ValidationError, match="required"):
            validate_street_address(input_type)

    def test_unicode_edge_cases_address(self) -> None:
        """Test unicode and unicode edge case handling for addresses"""
        unicode_test_cases = [
            "123 Ｍａｉｎ Ｓｔ",  # Full-width characters
            "123 Main Street\u200B",  # Zero-width space
            "123 Café Street",  # Unicode characters
        ]

        for address in unicode_test_cases:
            with pytest.raises(ValidationError):
                validate_street_address(address)

    def test_sql_injection_attempts_address(self) -> None:
        """Test street address validation against potential SQL injection attempts"""
        sql_injection_attempts = [
            "'123 Main St' OR 1=1 --",
            "123 Main St'; DROP TABLE users; --",
            '"123 Main St" UNION SELECT * FROM users--',
        ]

        for attempt in sql_injection_attempts:
            with pytest.raises(ValidationError):
                validate_street_address(attempt)

    def test_extremely_long_input_address(self) -> None:
        """Test street address validation with extremely long inputs"""
        too_long_address = "123 " + ("A" * 1000) + " Street"
        with pytest.raises(ValidationError):
            validate_street_address(too_long_address)

    def test_control_character_inputs_address(self) -> None:
        """Test handling of control characters in street addresses"""
        control_chars = [
            "\x00123 Main St",  # Null byte
            "123 Main\r St",  # Carriage return
            "123 Main\n St",  # Newline
            "123 Main\t St",  # Tab
            "\x1F123 Main St",  # Control character
        ]

        for char_code in control_chars:
            with pytest.raises(ValidationError):
                validate_street_address(char_code)


class TestPOBoxValidation:
    """Enhanced PO Box validation tests"""

    @pytest.mark.parametrize("leading_zero_case", ["PO Box 00001", "PO Box 00100", "PO Box 00999"])
    def test_leading_zeros_po_box(self, leading_zero_case: str) -> None:
        """Test validation of PO Box numbers with leading zeros"""
        validate_po_box(leading_zero_case)

    @pytest.mark.parametrize("large_po_box", ["PO Box 999999", "P.O. Box 1000000", "POB 9999999"])
    def test_large_po_box_numbers(self, large_po_box: str) -> None:
        """Test validation of very large PO Box numbers"""
        validate_po_box(large_po_box)

    @pytest.mark.parametrize(
        "input_type", [0, ["PO Box 123"], {"po_box": "PO Box 123"}, object(), float("nan")]
    )
    def test_attribute_error_non_string_inputs(self, input_type: Any) -> None:
        """Test that PO Box validation fails for non-string inputs"""
        with pytest.raises(ValidationError, match="required"):
            validate_po_box(input_type)

    def test_unicode_edge_cases_po_box(self) -> None:
        """Test unicode and unicode edge case handling for PO Boxes"""
        unicode_test_cases = [
            "Ｐ.Ｏ. Box 123",  # Full-width characters
            "PO Box 123\u200B",  # Zero-width space
        ]

        for po_box in unicode_test_cases:
            with pytest.raises(ValidationError):
                validate_po_box(po_box)

    def test_sql_injection_attempts_po_box(self) -> None:
        """Test PO Box validation against potential SQL injection attempts"""
        sql_injection_attempts = [
            "'PO Box 123' OR 1=1 --",
            "PO Box 123'; DROP TABLE users; --",
            '"PO Box 123" UNION SELECT * FROM users--',
        ]

        for attempt in sql_injection_attempts:
            with pytest.raises(ValidationError):
                validate_po_box(attempt)

    def test_extremely_long_input_po_box(self) -> None:
        """Test PO Box validation with extremely long inputs"""
        too_long_po_box = "PO Box " + ("9" * 1000)
        with pytest.raises(ValidationError):
            validate_po_box(too_long_po_box)

    def test_control_character_inputs_po_box(self) -> None:
        """Test handling of control characters in PO Box inputs"""
        control_chars = [
            "\x00PO Box 123",  # Null byte
            "PO Box\r 123",  # Carriage return
            "PO Box\n 123",  # Newline
            "PO Box\t 123",  # Tab
            "\x1FPO Box 123",  # Control character
        ]

        for char_code in control_chars:
            with pytest.raises(ValidationError):
                validate_po_box(char_code)


class TestValidatorObjectsImplementation:
    """Tests for objects implementing __str__ method"""

    class MockStrObject:
        """Mock object with __str__ method"""

        def __init__(self, value: str):
            self._value = value

        def __str__(self) -> str:
            return self._value

    def test_state_code_with_str_object(self) -> None:
        """Test state code validation with object implementing __str__"""
        state_obj = self.MockStrObject("CA")
        validate_state_code(state_obj)

    def test_zip_code_with_str_object(self) -> None:
        """Test ZIP code validation with object implementing __str__"""
        zip_obj = self.MockStrObject("12345")
        validate_zip_code(zip_obj)

    def test_street_address_with_str_object(self) -> None:
        """Test street address validation with object implementing __str__"""
        address_obj = self.MockStrObject("123 Main St")
        validate_street_address(address_obj)

    def test_po_box_with_str_object(self) -> None:
        """Test PO Box validation with object implementing __str__"""
        po_box_obj = self.MockStrObject("PO Box 123")
        validate_po_box(po_box_obj)


class TestValidatorMultipleInputTypePerformance:
    """Performance and concurrent validation tests"""

    def test_validator_concurrent_performance(self) -> None:
        """
        Simulate concurrent validation attempts.
        Note: This is a basic simulation and might require actual
        concurrency library in production.
        """
        import threading

        results = []

        def validate_wrapper(validator: Callable, value: str) -> None:
            try:
                validator(value)
                results.append(True)
            except ValidationError:
                results.append(False)

        test_cases = [
            (validate_state_code, "CA"),
            (validate_zip_code, "12345"),
            (validate_street_address, "123 Main St"),
            (validate_po_box, "PO Box 123"),
        ]

        threads = []
        for validator, value in test_cases * 10:  # Repeat test cases
            thread = threading.Thread(target=validate_wrapper, args=(validator, value))
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()

        # All threads should successfully validate without raising uncaught exceptions
        assert len(results) == len(test_cases) * 10
        assert all(results)
