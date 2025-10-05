# TODO

- Tighten `State` model requirements (e.g., consider making `code` non-blank) and align tests with the chosen rules.
- Audit generated tests for unrealistic expectations and remove placeholder logic (see `tests/test_integration.py::test_query_optimization`).
- Expand Address model API surface (street type, unit info, etc.) to cover django-address compatibility gaps.
- Document schema differences from legacy django-address in `docs/` and update migration guidance.
- Add query-count assertions using `django_assert_num_queries` where we expect optimized ORM behavior.
- Revisit fixture defaults (e.g., ensure `country_instance` is provided wherever state creation occurs) to avoid integrity errors.
- Introduce Faker-powered factories for addresses/localities to reduce hard-coded data repetition in tests.
