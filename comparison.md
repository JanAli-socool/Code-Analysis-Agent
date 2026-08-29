# Code Analysis Comparison Report

**Overall Score:** 61.2 -> 80.2 (+19.0)
**Risk Level:** critical -> low

## Summary

- **Unchanged:** 4
- **Improved:** 4

## Category Changes

### [+] maintainability
- **Score:** 73.0 -> 85.0 (+12.0)
- **Change:** improved
- **Finding Changes:**
  - fixed_finding: `high_complexity_messy_code.py_bad_function` at `messy_code.py:10`
  - fixed_finding: `large_class_messy_code.py_GodClass` at `messy_code.py:33`
  - fixed_finding: `many_params_messy_code.py_bad_function` at `messy_code.py:10`
### [+] complexity
- **Score:** 65.0 -> 85.0 (+20.0)
- **Change:** improved
- **Finding Changes:**
  - new_finding: `mi_test_math_utils.py` at `test_math_utils.py:1`
  - fixed_finding: `nesting_messy_code.py` at `messy_code.py:1`
  - fixed_finding: `cc_messy_code.py_bad_function_10` at `messy_code.py:10`
  - fixed_finding: `mi_messy_code.py` at `messy_code.py:1`
### [+] testing
- **Score:** 0.0 -> 20.0 (+20.0)
- **Change:** improved
- **Finding Changes:**
  - fixed_finding: `no_test_files` at N/A
  - new_finding: `no_assert_test_math_utils.py_test_fibonacci_base_cases` at `test_math_utils.py:6`
  - new_finding: `no_assert_test_math_utils.py_test_process_data_single` at `test_math_utils.py:68`
  - new_finding: `no_assert_test_math_utils.py_test_fibonacci_known_values` at `test_math_utils.py:10`
  - new_finding: `no_assert_test_math_utils.py_test_factorial` at `test_math_utils.py:37`
  - new_finding: `no_assert_test_math_utils.py_test_prime_numbers` at `test_math_utils.py:21`
  - new_finding: `no_assert_test_math_utils.py_test_gcd` at `test_math_utils.py:47`
  - new_finding: `no_assert_test_math_utils.py_test_process_data_empty` at `test_math_utils.py:65`
  - new_finding: `no_assert_test_math_utils.py_test_non_prime_numbers` at `test_math_utils.py:28`
  - new_finding: `no_assert_test_math_utils.py_test_process_data_even_count` at `test_math_utils.py:61`
  - new_finding: `no_assert_test_math_utils.py_test_factorial_negative_raises` at `test_math_utils.py:43`
  - new_finding: `no_assert_test_math_utils.py_test_process_data_normal` at `test_math_utils.py:54`
  - new_finding: `no_assert_test_math_utils.py_test_fibonacci_negative_raises` at `test_math_utils.py:15`
### [+] security
- **Score:** 16.0 -> 100.0 (+84.0)
- **Change:** improved
- **Finding Changes:**
  - fixed_finding: `ast_hardcoded-cred_messy_code.py_73` at `messy_code.py:73`
  - fixed_finding: `ast_hardcoded-cred_messy_code.py_74` at `messy_code.py:74`
  - fixed_finding: `custom_pickle-loads_messy_code.py_77` at `messy_code.py:77`
  - fixed_finding: `custom_eval-usage_messy_code.py_7` at `messy_code.py:7`
  - fixed_finding: `custom_hardcoded-secret_messy_code.py_72` at `messy_code.py:72`
  - fixed_finding: `ast_sql-concat_messy_code.py_66` at `messy_code.py:66`
  - fixed_finding: `custom_hardcoded-secret_messy_code.py_74` at `messy_code.py:74`
  - fixed_finding: `custom_hardcoded-secret_messy_code.py_73` at `messy_code.py:73`
  - fixed_finding: `ast_shell-true_messy_code.py_70` at `messy_code.py:70`

## New Strengths

- Strong maintainability: 85.0/100
- Strong security: 100/100
- Strong complexity: 85.0/100

## New Weaknesses

- Weak testing: 20.0/100