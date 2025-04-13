import unittest

from tagify import TemplateParser


class TemplateParserTests(unittest.TestCase):
    def setUp(self):
        self.context = {
            "user": {
                "name": "Alice",
                "age": 25,
                "greet": lambda x: f"Hey {x}",
            },
            "name": "World",
            "value": "42",
            "number": 10,
            "is_admin": False,
            "enabled": True,
            "truthy": "non-empty",
            "falsy": "",
            "score": 75
        }
        self.parser = TemplateParser(self.context)

    def test_placeholder_basic(self):
        self.assertEqual(
            self.parser.render("Hi {name}!"),
            "Hi World!"
        )

    def test_placeholder_attribute_access(self):
        self.assertEqual(
            self.parser.render("User name: {user.name}"),
            "User name: Alice"
        )

    def test_function_call(self):
        self.assertEqual(
            self.parser.render("{user.greet('Bob')}"),
            "Hey Bob"
        )

    def test_set_variable(self):
        self.assertEqual(
            self.parser.render("{% set test = Test Value %}{test}"),
            "Test Value"
        )

    def test_if_condition_truthy(self):
        self.assertEqual(
            self.parser.render("{% if truthy %}Yes{% endif %}"),
            "Yes"
        )

    def test_if_condition_falsy(self):
        self.assertEqual(
            self.parser.render("{% if falsy %}Yes{% endif %}"),
            ""
        )

    def test_if_not_condition(self):
        self.assertEqual(
            self.parser.render("{% if not falsy %}Passed{% endif %}"),
            "Passed"
        )

    def test_if_nested_path_truthy(self):
        self.assertEqual(
            self.parser.render("{% if user.name %}Good{% endif %}"),
            "Good"
        )

    def test_if_not_nested_path(self):
        self.assertEqual(
            self.parser.render("{% if not user.nonexistent %}Empty{% endif %}"),
            "Empty"
        )

    def test_if_elif_else(self):
        result = self.parser.render("""
            {% if number == 0 %}Zero
            {% elif number == 10 %}Ten
            {% else %}Other
            {% endif %}
        """)
        self.assertIn("Ten", result)

    def test_comparison_eq(self):
        self.assertEqual(
            self.parser.render("{% if value == '42' %}Match{% endif %}"),
            "Match"
        )

    def test_comparison_neq(self):
        self.assertEqual(
            self.parser.render("{% if name != 'Alice' %}Not Alice{% endif %}"),
            "Not Alice"
        )

    def test_numeric_comparison(self):
        self.assertEqual(
            self.parser.render("{% if user.age == 25 %}Yes{% endif %}"),
            "Yes"
        )

    def test_unresolvable_key(self):
        self.assertIn(
            "{missing.value}",
            self.parser.render("{missing.value}")
        )

    def test_whitespace_handling(self):
        self.assertEqual(
            self.parser.render("   Hello {name}   "),
            "Hello World"
        )

    def test_combined_logic(self):
        tmpl = """
        {% set user_type = guest %}
        {% if user.name == Alice && user.age == 25 %}
        Welcome back, {user.name}!
        {% else %}
        Unknown user.
        {% endif %}
        """
        self.assertIn("Welcome back, Alice!", self.parser.render(tmpl))


if __name__ == "__main__":
    unittest.main()
