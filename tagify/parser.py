import re

from typing import Any, Callable

# RegEx patterns
_re_placeholder = re.compile(r"{(\w+|\w+\(.+?\))}")
_re_blocks = re.compile(r"{% elif (.+?) %}|{% else %}")
_re_conditions = re.compile(r"{% elif (.+?) %}")
_re_terms = re.compile(r"(\s&&\s|\s\|\|\s)")
_re_match = re.compile(r"([\w\(\),]+)\s*(==|!=)\s*(.+)")
_re_conditional_pattern = re.compile(
    r"{% if (.+?) %}(.+?){% endif %}",
    flags=re.DOTALL
)

__all__ = (
    "TemplateParser",
)


class TemplateParser:
    """
    NOTE:
    This style might change later on, but for now it works.
    """
    def __init__(
        self,
        context: dict | None = None,
        functions: dict | None = None
    ):
        self.context: dict[str, Any] = context or {}
        self.functions: dict[str, Callable] = functions or {}

    def render(self, template: str) -> str:
        """Render the template with placeholders, conditionals, and function calls."""
        template = self._process_conditionals(template)  # Process if/else/elif blocks
        template = self._process_placeholders(template)  # Replace placeholders and function calls
        return template

    def _parse_placeholder(self, key: str) -> str:
        """Evaluate placeholders or function calls."""
        safe_unused = "{" + str(key) + "}"
        # Check if the placeholder is a function call
        if "(" in key and key.endswith(")"):
            func_name, args = self._parse_function_call(key)

            if func_name in self.functions:
                try:
                    return str(self.functions[func_name](*args))
                except Exception as e:
                    return f"[ FUNC_ERR:{func_name}: {e} ]"

            return safe_unused  # Return unmodified if function not found

        return str(self.context.get(key, safe_unused))

    def _process_placeholders(self, template: str) -> str:
        """Replace all placeholders in the template with their values."""
        return _re_placeholder.sub(
            lambda m: self._parse_placeholder(m.group(1)),
            template
        )

    def _process_conditionals(self, template: str) -> str:
        """Handle if, elif, else conditionals in the template."""
        return _re_conditional_pattern.sub(
            self._evaluate_conditional_block,
            template
        )

    def _evaluate_conditional_block(self, match: re.Match) -> str:
        """Evaluate if, elif, and else conditions and return the appropriate block."""
        condition, content = match.groups()
        blocks = _re_blocks.split(content)
        conditions = [condition] + _re_conditions.findall(content)

        for cond, block in zip(conditions, blocks):
            if self._evaluate_condition(cond.strip()):
                return block.strip()

        return blocks[-1].strip() if "{% else %}" in content else ""

    def _evaluate_condition(self, condition: str) -> bool:
        """Evaluate conditions safely without using eval."""
        # Split by logical operators and evaluate each subcondition
        terms = _re_terms.split(condition)
        result = self._evaluate_comparison(terms[0].strip())

        for i in range(1, len(terms), 2):
            operator = terms[i].strip()
            next_term = self._evaluate_comparison(terms[i + 1].strip())

            if operator == "&&":
                result = result and next_term
            elif operator == "||":
                result = result or next_term

        return result

    def _evaluate_comparison(self, term: str) -> bool:
        """Evaluate a single comparison expression like 'user == "Alice"'."""
        match = _re_match.match(term)
        if not match:
            return False

        left, operator, right = match.groups()
        left_value = str(self.context.get(left, left))
        right_value = right.strip('"').strip("'")

        if left_value.isdigit() and right_value.isdigit():
            left_value = int(left_value)
            right_value = int(right_value)

        if operator == "==":
            return left_value == right_value
        elif operator == "!=":
            return left_value != right_value

    def _parse_function_call(self, func_string: str) -> tuple[str, list[str]]:
        """Parse function calls like 'func_name(arg1, arg2)'."""
        func_name = func_string.split('(', 1)[0]
        args_string = func_string[len(func_name) + 1:-1]  # Remove function name and parentheses
        args = [arg.strip().strip('"').strip("'") for arg in args_string.split(',')]
        return func_name, args
