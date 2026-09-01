def calculate_fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number using iterative approach.
    
    Args:
        n: The position in the Fibonacci sequence (0-indexed)
        
    Returns:
        The nth Fibonacci number
        
    Raises:
        ValueError: If n is negative
    """
    if n < 0:
        raise ValueError("n must be non-negative")
    if n <= 1:
        return n
    
    a, b = 0, 1
    for _ in range(n - 1):
        a, b = b, a + b
    return b


def is_prime(n: int) -> bool:
    """Check if a number is prime.
    
    Args:
        n: Number to check
        
    Returns:
        True if prime, False otherwise
    """
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    
    for i in range(3, int(n ** 0.5) + 1, 2):
        if n % i == 0:
            return False
    return True


class MathUtils:
    """Utility class for mathematical operations."""
    
    @staticmethod
    def factorial(n: int) -> int:
        """Calculate factorial of n."""
        if n < 0:
            raise ValueError("Factorial undefined for negative numbers")
        result = 1
        for i in range(2, n + 1):
            result *= i
        return result
    
    @staticmethod
    def gcd(a: int, b: int) -> int:
        """Calculate greatest common divisor using Euclidean algorithm."""
        while b:
            a, b = b, a % b
        return a


def process_data(data: list) -> dict:
    """Process a list of numbers and return statistics.
    
    Args:
        data: List of numeric values
        
    Returns:
        Dictionary with mean, median, min, max
    """
    if not data:
        return {}
    
    sorted_data = sorted(data)
    n = len(sorted_data)
    
    return {
        "mean": sum(data) / n,
        "median": sorted_data[n // 2] if n % 2 else (sorted_data[n // 2 - 1] + sorted_data[n // 2]) / 2,
        "min": min(data),
        "max": max(data)
    }