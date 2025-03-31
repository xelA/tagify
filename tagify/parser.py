import re

from typing import Any

# RegEx patterns
_re_placeholder = re.compile(
    r"{\s*([\w\d.]+)*(?:\(([\s\S]+?)\))?\s*}",
    flags=re.MULTILINE | re.DOTALL
)
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
        The parser class for Tagify.

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
        # Strip any leading or trailing whitespace
        template = template.strip()

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
            self.context[key.strip()] = self._process_placeholders(value.strip())

        return _re_variables.sub("", template)

    def _parse_placeholder(self, m: re.Match) -> str:
        """
        Evaluate placeholders or function calls.

        Parameters
        ----------
        m: `re.Match`
            The match object for the placeholder.

        Returns
        -------
        `str`
            The evaluated placeholder value.
        """
        if len(m.groups()) == 1:
            func_key = m.group(1)
            value = ""
        else:
            func_key, value = m.groups()

        safe_unused = "{" + str(func_key) + "}"

        parts = func_key.split(".")  # Split by dots to access nested keys/attributes
        current = self.context  # Start with the base context

        try:
            for part in parts:
                if isinstance(current, dict):
                    current = current.get(part, safe_unused)

                if isinstance(current, dict):
                    # Continue digging for now
                    # There is probably a better way, but this works for now
                    continue

                if callable(current):
                    args = self._parse_function_call(value)
                    current = current(*args)  # Call the function

        except Exception as e:
            return f"[ ERROR:{func_key}: {e} ]"  # Handle any unexpected errors

        return str(current) if not callable(current) else safe_unused  # Return as-is

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
            self._parse_placeholder,
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
        conditions = [condition, *_re_conditions.findall(content)]

        for cond, block in zip(conditions, blocks, strict=False):
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

        match operator:
            case "==":
                return left_value == right_value

            case "!=":
                return left_value != right_value

            case _:
                raise ValueError(f"Invalid operator: {operator}")

    def _parse_function_call(self, expr: str) -> list[str | int]:
        """
        Parse function calls like 'func_name(arg1, arg2)'.

        Parameters
        ----------
        expr: `str`
            The function call string to parse.

        Returns
        -------
        `tuple[str, list[str]]`
            The function name and arguments.
        """
        args = []
        current_arg = []
        in_quotes = False
        quote_char = ""

        for char in expr:
            if char in ('"', "'"):
                if not in_quotes:
                    in_quotes = True
                    quote_char = char

                elif quote_char == char:
                    in_quotes = False
                    quote_char = ""

            if char == "," and not in_quotes:
                args.append("".join(current_arg).strip())
                current_arg = []

            else:
                current_arg.append(char)

        if current_arg:
            args.append("".join(current_arg).strip())

        for i, arg in enumerate(args):
            if arg in self.context:
                args[i] = str(self.context[arg])

            elif arg.isdigit():
                args[i] = int(arg)

            elif (
                (arg.startswith('"') and arg.endswith('"')) or
                (arg.startswith("'") and arg.endswith("'"))
            ):
                args[i] = arg[1:-1]

        return [
            # Process placeholders in the arguments as well
            self._process_placeholders(g)
            if isinstance(g, str) else g
            for g in args
        ]
