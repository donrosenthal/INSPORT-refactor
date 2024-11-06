import unittest
from server_data.server_side_data import PolicyFile, PolicyCollection, MockUser, MockUserCollection

class TestPolicyFile(unittest.TestCase):
    def test_policy_file_creation(self):
        policy = PolicyFile("1", "/path/to/file", "auto", "My Auto Policy", "InsureCo", "pdf")
        self.assertEqual(policy.file_id, "1")
        self.assertEqual(policy.path, "/path/to/file")
        self.assertEqual(policy.policy_type, "auto")
        self.assertEqual(policy.print_name, "My Auto Policy")
        self.assertEqual(policy.carrier, "InsureCo")
        self.assertEqual(policy.format, "pdf")
        self.assertIsNone(policy.additional_metadata)

    def test_policy_file_with_metadata(self):
        metadata = {"expiry_date": "2023-12-31"}
        policy = PolicyFile("2", "/another/path", "home", "Home Policy", "SafeHouse", "docx", metadata)
        self.assertEqual(policy.additional_metadata, metadata)

class TestPolicyCollection(unittest.TestCase):
    def test_policy_collection_creation(self):
        collection = PolicyCollection()
        self.assertEqual(len(collection.policies), 0)

    def test_policy_collection_add_policy(self):
        collection = PolicyCollection()
        policy = PolicyFile("1", "/path", "auto", "Auto Policy", "InsureCo", "pdf")
        collection.policies["1"] = policy
        self.assertEqual(len(collection.policies), 1)
        self.assertEqual(collection.policies["1"], policy)

class TestMockUser(unittest.TestCase):
    def setUp(self):
        self.user = MockUser("u1", 2, PolicyCollection(), "John", "Doe")
        self.user.policies.policies["p1"] = PolicyFile("p1", "/path1", "auto", "Auto Policy", "InsureCo", "pdf")
        self.user.policies.policies["p2"] = PolicyFile("p2", "/path2", "home", "Home Policy", "SafeHouse", "docx")

    def test_mock_user_creation(self):
        self.assertEqual(self.user.user_id, "u1")
        self.assertEqual(self.user.number_policies, 2)
        self.assertEqual(self.user.first_name, "John")
        self.assertEqual(self.user.last_name, "Doe")

    def test_mock_user_getitem(self):
        policy = self.user["p1"]
        self.assertEqual(policy.file_id, "p1")
        self.assertEqual(policy.policy_type, "auto")

    def test_mock_user_getitem_not_found(self):
        with self.assertRaises(KeyError):
            _ = self.user["p3"]

class TestMockUserCollection(unittest.TestCase):
    def setUp(self):
        self.collection = MockUserCollection()
        user1 = MockUser("u1", 2, PolicyCollection(), "John", "Doe")
        user2 = MockUser("u2", 1, PolicyCollection(), "Jane", "Smith")
        self.collection.users["u1"] = user1
        self.collection.users["u2"] = user2

    def test_mock_user_collection_creation(self):
        self.assertEqual(len(self.collection.users), 2)

    def test_mock_user_collection_getitem(self):
        user = self.collection["u1"]
        self.assertEqual(user.user_id, "u1")
        self.assertEqual(user.first_name, "John")

    def test_mock_user_collection_getitem_not_found(self):
        with self.assertRaises(KeyError):
            _ = self.collection["u3"]

    def test_get_user_policy_count(self):
        result = self.collection.get_user_policy_count("u1")
        self.assertEqual(result, {"user_id": "u1", "policy_count": 2})

    def test_get_user_policy_count_not_found(self):
        result = self.collection.get_user_policy_count("u3")
        self.assertEqual(result, {"error": "User not found"})

if __name__ == '__main__':
    unittest.main()