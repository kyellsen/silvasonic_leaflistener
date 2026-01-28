import os
import unittest

# We need to ensure we can import the module even if dependencies are missing in the test environment
# (though in this context we likely have them).
# The main challenge is that auth.py runs logic at import time.
# We will use importlib.reload to refresh module state for different tests if needed,
# OR we just test the `get_admin_password` function by monkeypatching the globals it uses.
from silvasonic_dashboard import auth


class TestAuthLogic(unittest.TestCase):
    def setUp(self):
        # Reset globals before each test to a known state (Dev default)
        auth.SILVASONIC_ENV = "development"
        auth.DASHBOARD_PASSWORD = ""
        auth.SECRET_FILE_PATH = "/tmp/silvasonic_test_secret.txt"
        # Use a temp path for tests
        if os.path.exists(auth.SECRET_FILE_PATH):
            os.remove(auth.SECRET_FILE_PATH)

    def tearDown(self):
        if os.path.exists(auth.SECRET_FILE_PATH):
            os.remove(auth.SECRET_FILE_PATH)

    def test_dev_mode_defaults(self):
        """Case A: Dev mode, no password set -> defaults to 1234"""
        auth.SILVASONIC_ENV = "development"
        auth.DASHBOARD_PASSWORD = ""

        password = auth.get_admin_password()
        self.assertEqual(password, "1234")

    def test_dev_mode_override(self):
        """Case A: Dev mode, password set -> uses set password"""
        auth.SILVASONIC_ENV = "development"
        auth.DASHBOARD_PASSWORD = "my_dev_pass"

        password = auth.get_admin_password()
        self.assertEqual(password, "my_dev_pass")

    def test_prod_mode_provided_password(self):
        """Case B: Prod mode, valid password set -> uses it"""
        auth.SILVASONIC_ENV = "production"
        auth.DASHBOARD_PASSWORD = "secure_production_pass"

        password = auth.get_admin_password()
        self.assertEqual(password, "secure_production_pass")

    def test_prod_mode_hard_fail(self):
        """Case B: Prod mode, password is '1234' -> Hard Fail"""
        auth.SILVASONIC_ENV = "production"
        auth.DASHBOARD_PASSWORD = "1234"

        with self.assertRaises(SystemExit) as cm:
            auth.get_admin_password()
        self.assertEqual(cm.exception.code, 1)

    def test_prod_mode_generation_fresh(self):
        """Case B: Prod mode, no password -> generate and save"""
        auth.SILVASONIC_ENV = "production"
        auth.DASHBOARD_PASSWORD = ""

        # Mocking secrets to return a known value isn't strictly necessary if we just check length
        # but let's just check behavior.

        password = auth.get_admin_password()

        # Check it's a 32-byte hex string (64 chars)
        self.assertEqual(len(password), 64)

        # Verify persistence
        self.assertTrue(os.path.exists(auth.SECRET_FILE_PATH))
        with open(auth.SECRET_FILE_PATH) as f:
            content = f.read()
        self.assertEqual(content, password)

    def test_prod_mode_persistence_reload(self):
        """Case B: Prod mode, no password, file exists -> read file"""
        auth.SILVASONIC_ENV = "production"
        auth.DASHBOARD_PASSWORD = ""

        # Pre-seed file
        expected_token = "aabbccddeeff11223344556677889900aabbccddeeff11223344556677889900"
        with open(auth.SECRET_FILE_PATH, "w") as f:
            f.write(expected_token)

        password = auth.get_admin_password()
        self.assertEqual(password, expected_token)
        # Should NOT have overwritten it
        with open(auth.SECRET_FILE_PATH) as f:
            content = f.read()
        self.assertEqual(content, expected_token)


if __name__ == "__main__":
    unittest.main()
