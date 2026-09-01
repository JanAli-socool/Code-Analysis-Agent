import pytest
from math_utils import calculate_fibonacci, is_prime, MathUtils, process_data


class TestFibonacci:
    def test_fibonacci_base_cases(self):
        assert calculate_fibonacci(0) == 0
        assert calculate_fibonacci(1) == 1
    
    def test_fibonacci_known_values(self):
        assert calculate_fibonacci(5) == 5
        assert calculate_fibonacci(10) == 55
        assert calculate_fibonacci(20) == 6765
    
    def test_fibonacci_negative_raises(self):
        with pytest.raises(ValueError):
            calculate_fibonacci(-1)


class TestPrime:
    def test_prime_numbers(self):
        assert is_prime(2) is True
        assert is_prime(3) is True
        assert is_prime(5) is True
        assert is_prime(13) is True
        assert is_prime(97) is True
    
    def test_non_prime_numbers(self):
        assert is_prime(1) is False
        assert is_prime(4) is False
        assert is_prime(9) is False
        assert is_prime(15) is False
        assert is_prime(100) is False


class TestMathUtils:
    def test_factorial(self):
        assert MathUtils.factorial(0) == 1
        assert MathUtils.factorial(1) == 1
        assert MathUtils.factorial(5) == 120
        assert MathUtils.factorial(10) == 3628800
    
    def test_factorial_negative_raises(self):
        with pytest.raises(ValueError):
            MathUtils.factorial(-1)
    
    def test_gcd(self):
        assert MathUtils.gcd(48, 18) == 6
        assert MathUtils.gcd(17, 13) == 1
        assert MathUtils.gcd(100, 25) == 25


class TestProcessData:
    def test_process_data_normal(self):
        result = process_data([1, 2, 3, 4, 5])
        assert result["mean"] == 3.0
        assert result["median"] == 3
        assert result["min"] == 1
        assert result["max"] == 5
    
    def test_process_data_even_count(self):
        result = process_data([1, 2, 3, 4])
        assert result["median"] == 2.5
    
    def test_process_data_empty(self):
        assert process_data([]) == {}
    
    def test_process_data_single(self):
        result = process_data([42])
        assert result["mean"] == 42
        assert result["median"] == 42