import random
import unittest

from tagify import TemplateParser


class TemplateParserTests(unittest.TestCase):
    def setUp(self) -> None:
        """Build a shared context and parser instance for each test."""
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
            "score": 75,
            "random": random,
        }
        self.parser = TemplateParser(self.context)

    def test_placeholder_basic(self) -> None:
        """A simple {key} placeholder is replaced with its context value."""
        self.assertEqual(
            self.parser.render("Hi {name}!"),
            "Hi World!"
        )

    def test_placeholder_attribute_access(self) -> None:
        """A dotted placeholder resolves nested dict/attribute access."""
        self.assertEqual(
            self.parser.render("User name: {user.name}"),
            "User name: Alice"
        )

    def test_function_call(self) -> None:
        """A callable in the context can be invoked from a placeholder."""
        self.assertEqual(
            self.parser.render("{user.greet('Bob')}"),
            "Hey Bob"
        )

    def test_set_variable(self) -> None:
        """{% set %} assigns a value that a later placeholder can read."""
        self.assertEqual(
            self.parser.render("{% set test = Test Value %}{test}"),
            "Test Value"
        )

    def test_if_condition_truthy(self) -> None:
        """A truthy condition renders the if-block's content."""
        self.assertEqual(
            self.parser.render("{% if truthy %}Yes{% endif %}"),
            "Yes"
        )

    def test_if_condition_falsy(self) -> None:
        """A falsy condition renders nothing."""
        self.assertEqual(
            self.parser.render("{% if falsy %}Yes{% endif %}"),
            ""
        )

    def test_if_not_condition(self) -> None:
        """`not` negates the truthiness of the condition."""
        self.assertEqual(
            self.parser.render("{% if not falsy %}Passed{% endif %}"),
            "Passed"
        )

    def test_if_nested_path_truthy(self) -> None:
        """A dotted path can be used directly as a truthy condition."""
        self.assertEqual(
            self.parser.render("{% if user.name %}Good{% endif %}"),
            "Good"
        )

    def test_if_not_nested_path(self) -> None:
        """`not` works with a dotted path that resolves to a missing key."""
        self.assertEqual(
            self.parser.render("{% if not user.nonexistent %}Empty{% endif %}"),
            "Empty"
        )

    def test_if_elif_else(self) -> None:
        """The matching elif branch is selected over if and else."""
        result = self.parser.render("""
            {% if number == 0 %}Zero
            {% elif number == 10 %}Ten
            {% else %}Other
            {% endif %}
        """)
        self.assertIn("Ten", result)

    def test_comparison_eq(self) -> None:
        """`==` comparison matches a quoted string literal."""
        self.assertEqual(
            self.parser.render("{% if value == '42' %}Match{% endif %}"),
            "Match"
        )

    def test_comparison_neq(self) -> None:
        """`!=` comparison is true when the values differ."""
        self.assertEqual(
            self.parser.render("{% if name != 'Alice' %}Not Alice{% endif %}"),
            "Not Alice"
        )

    def test_numeric_comparison(self) -> None:
        """`==` comparison works against a numeric context value."""
        self.assertEqual(
            self.parser.render("{% if user.age == 25 %}Yes{% endif %}"),
            "Yes"
        )

    def test_unresolvable_key(self) -> None:
        """A placeholder with no matching context key is left untouched."""
        self.assertIn(
            "{missing.value}",
            self.parser.render("{missing.value}")
        )

    def test_whitespace_handling(self) -> None:
        """Leading and trailing whitespace is stripped from the output."""
        self.assertEqual(
            self.parser.render("   Hello {name}   "),
            "Hello World"
        )

    def test_module_attr_function_call_placeholder(self) -> None:
        """A placeholder can call a function reached via module attribute navigation."""
        self.assertEqual(
            self.parser.render("{random.randint(1, 1)}"),
            "1"
        )

    def test_if_with_braced_function_call(self) -> None:
        """A `{...}` wrapped function call inside an if condition evaluates correctly."""
        result = self.parser.render(
            "{% if {random.randint(2, 2)} == 2 %}Heads{% else %}Tails{% endif %}"
        )
        self.assertEqual(result, "Heads")

    def test_if_with_bare_function_call(self) -> None:
        """A bare (unbraced) function call works directly in an if condition."""
        result = self.parser.render(
            "{% if random.randint(2, 2) == 2 %}Heads{% else %}Tails{% endif %}"
        )
        self.assertEqual(result, "Heads")

    def test_combined_logic(self) -> None:
        """`&&` combines two comparisons that must both be true."""
        tmpl = """
        {% if user.name == Alice && user.age == 25 %}
        Welcome back, {user.name}!
        {% else %}
        Unknown user.
        {% endif %}
        """
        self.assertIn("Welcome back, Alice!", self.parser.render(tmpl))

    def test_nested_if_outer_true_inner_true(self) -> None:
        """A nested if renders when both the outer and inner conditions are true."""
        tmpl = """
        {% if truthy %}
        {% if enabled %}
        Both
        {% endif %}
        {% endif %}
        """
        self.assertEqual(self.parser.render(tmpl), "Both")

    def test_nested_if_outer_true_inner_false(self) -> None:
        """A nested if renders nothing when the inner condition is false."""
        tmpl = """
        {% if truthy %}
        {% if is_admin %}
        Both
        {% endif %}
        {% endif %}
        """
        self.assertEqual(self.parser.render(tmpl), "")

    def test_nested_if_outer_false(self) -> None:
        """A falsy outer condition prevents the inner block from ever rendering."""
        tmpl = """
        {% if falsy %}
        {% if enabled %}
        Both
        {% endif %}
        {% endif %}
        """
        self.assertEqual(self.parser.render(tmpl), "")

    def test_nested_if_with_inner_else(self) -> None:
        """The inner if/else resolves independently of the outer condition."""
        tmpl = """
        {% if enabled %}
        {% if is_admin %}
        Admin
        {% else %}
        Member
        {% endif %}
        {% endif %}
        """
        self.assertEqual(self.parser.render(tmpl), "Member")

    def test_nested_if_no_stray_endif_tag(self) -> None:
        """Regression: a mismatched if/endif pairing must not leak {% endif %} as literal text."""
        tmpl = """
        {% if enabled %}
        {% if is_admin %}
        Admin
        {% else %}
        Member
        {% endif %}
        {% endif %}
        """
        result = self.parser.render(tmpl)
        self.assertNotIn("{% endif %}", result)
        self.assertNotIn("{% if %}", result)

    def test_triple_nested_if(self) -> None:
        """Three levels of nested if blocks all resolve correctly."""
        tmpl = """
        {% if truthy %}
        {% if enabled %}
        {% if user.age == 25 %}
        Deep
        {% endif %}
        {% endif %}
        {% endif %}
        """
        self.assertEqual(self.parser.render(tmpl), "Deep")

    def test_sibling_ifs_alongside_nested_if(self) -> None:
        """A sibling if/endif at the same level is unaffected by a preceding nested if."""
        tmpl = """
        {% if enabled %}
        {% if is_admin %}
        Admin
        {% endif %}
        Sibling: {% if truthy %}Shown{% endif %}
        {% endif %}
        """
        result = self.parser.render(tmpl)
        self.assertIn("Sibling: Shown", result)
        self.assertNotIn("Admin", result)

    def test_nested_if_with_outer_elif(self) -> None:
        """An outer elif branch is reachable even when the if-branch contains a nested if."""
        tmpl = """
        {% if is_admin %}
        {% if truthy %}
        Never
        {% endif %}
        {% elif enabled %}
        Fallback
        {% endif %}
        """
        self.assertEqual(self.parser.render(tmpl), "Fallback")


if __name__ == "__main__":
    unittest.main()
