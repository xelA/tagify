import re

from typing import Any

# RegEx patterns
_re_placeholder = re.compile(r"{\s*([\w\d]+(?:\.[\w\d]+)*(\(.+?\))?)\s*}")
_re_blocks = re.compile(r"{% elif (.+?) %}|{% else %}")
_re_terms = re.compile(r"(\s&&\s|\s\|\|\s)")
_re_match = re.compile(r"([\w\(\),]+)\s*(==|!=)\s*(.+)")
_re_variables = re.compile(r"{% set ([\w\d]+)\s*=\s*(.*) %}")
_re_conditions = re.compile(r"{% elif (.+?) %}")
_re_conditional_pattern = re.compile(
    r"{% if (.+?) %}(.+?){% endif %}",
    flags=re.DOTALL
)

__all__ = (
    "TemplateParser",
)


class TemplateParser:
    def __init__(
        self,
        context: dict | None = None,
        *,
        conditionals: bool = True,
    ):
        """
        Parameters
        ----------
        context: `dict`
            The context dictionary to use for variable evaluation.
        conditionals: `bool`
            Whether to process if/else/elif blocks.
        """
        self.context: dict[str, Any] = context or {}

        self._conditionals = conditionals

    def render(self, template: str) -> str:
        """
        Render the template with placeholders, conditionals, and function calls.

        Parameters
        ----------
        template: `str`
            The template string to render.

        Returns
        -------
        `str`
            The rendered template string.
        """
        template = self._process_variables(template)  # Replace variables

        if self._conditionals:
            template = self._process_conditionals(template)  # Process if/else/elif blocks

        template = self._process_placeholders(template)  # Replace placeholders and function calls
        return template.strip()  # Remove any trailing whitespace

    def _process_variables(self, template: str) -> str:
        """
        Replace all variables in the template with their values.

        Parameters
        ----------
        template: `str`
            The template string to process.

        Returns
        -------
        `str`
            The processed template string.
        """
        for match in _re_variables.finditer(template):
            key, value = match.groups()
            self.context[key.strip()] = value.strip()

        return _re_variables.sub("", template)

    def _parse_placeholder(self, key: str) -> str:
        """
        Evaluate placeholders or function calls.

        Parameters
        ----------
        key: `str`
            The placeholder key to evaluate.

        Returns
        -------
        `str`
            The evaluated placeholder value.
        """
        safe_unused = "{" + str(key) + "}"

        parts = key.split(".")  # Split by dots to access nested keys/attributes
        current = self.context  # Start with the base context

        try:
            for part in parts:
                if "(" in part and part.endswith(")"):  # Check for a function call
                    func_name, args = self._parse_function_call(part)
                    if callable(current[func_name]):
                        current = current[func_name](*args)  # Call the function
                    else:
                        return safe_unused  # Not callable, return as-is
                else:
                    if isinstance(current, dict):
                        current = current.get(part, safe_unused)  # Dig into nested dicts
                    else:
                        return safe_unused  # Part is not accessible, return as-is
        except Exception as e:
            return f"[ ERROR:{key}: {e} ]"  # Handle any unexpected errors

        return str(current) if not callable(current) else safe_unused

    def _process_placeholders(self, template: str) -> str:
        """
        Replace all placeholders in the template with their values.

        Parameters
        ----------
        template: `str`
            The template string to process.

        Returns
        -------
        `str`
            The processed template string.
        """
        return _re_placeholder.sub(
            lambda m: self._parse_placeholder(m.group(1)),
            template
        )

    def _process_conditionals(self, template: str) -> str:
        """
        Handle if, elif, else conditionals in the template.

        Parameters
        ----------
        template: `str`
            The template string to process.

        Returns
        -------
        `str`
            The processed template string.
        """
        return _re_conditional_pattern.sub(
            self._evaluate_conditional_block,
            template
        )

    def _evaluate_conditional_block(self, match: re.Match) -> str:
        """
        Evaluate if, elif, and else conditions and return the appropriate block.

        Parameters
        ----------
        match: `re.Match`
            The match object for the conditional block.

        Returns
        -------
        `str`
            The processed template string.
        """
        condition, content = match.groups()
        blocks = _re_blocks.split(content)
        conditions = [condition] + _re_conditions.findall(content)

        for cond, block in zip(conditions, blocks):
            if self._evaluate_condition(cond.strip()):
                return block.strip()

        return blocks[-1].strip() if "{% else %}" in content else ""

    def _evaluate_condition(self, condition: str) -> bool:
        """
        Evaluate conditions safely without using eval.

        Parameters
        ----------
        condition: `str`
            The condition string to evaluate.

        Returns
        -------
        `bool`
            The evaluated condition result.
        """
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
        """
        Evaluate a single comparison expression like 'user == "Alice"'.

        Parameters
        ----------
        term: `str`
            The comparison expression to evaluate.

        Returns
        -------
        `bool`
            The evaluated comparison result.
        """
        match = _re_match.match(term)
        if not match:
            return False

        left, operator, right = match.groups()
        left_value = str(self.context.get(left, left))
        right_value = right.strip('"').strip("'")

        if left_value in self.context:
            left_value = str(self.context[left_value])
        if right_value in self.context:
            right_value = str(self.context[right_value])

        if left_value.isdigit() and right_value.isdigit():
            left_value = int(left_value)
            right_value = int(right_value)

        if operator == "==":
            return left_value == right_value

        elif operator == "!=":
            return left_value != right_value

        else:
            raise ValueError(f"Invalid operator: {operator}")

    def _parse_function_call(self, func_string: str) -> tuple[str, list[str]]:
        """
        Parse function calls like 'func_name(arg1, arg2)'.

        Parameters
        ----------
        func_string: `str`
            The function call string to parse.

        Returns
        -------
        `tuple[str, list[str]]`
            The function name and arguments.
        """
        func_name = func_string.split("(", 1)[0]
        args_string = func_string[len(func_name) + 1:-1]
        args = [arg.strip() for arg in args_string.split(",")]

        for i, g in enumerate(list(args)):
            if g in self.context:
                args[i] = str(self.context[g])

            else:
                args[i] = g.strip('"').strip("'")

        return func_name, args
