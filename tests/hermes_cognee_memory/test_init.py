from hermes_cognee_memory import CogneeMemoryProvider


def test_package_exports_provider_class():
    assert CogneeMemoryProvider.__name__ == "CogneeMemoryProvider"
    assert CogneeMemoryProvider.__module__ == "hermes_cognee_memory.provider"
