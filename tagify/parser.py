import re

from typing import Any

# RegEx patterns
_re_placeholder = re.compile(
    r"{\s*([\w\d.]+)*(?:\(([\s\S]+?)\))?\s*}",
    flags=re.MULTILINE | re.DOTALL
)
_re_blocks = re.compile(r"{% elif (.+?) %}|{% else %}")
_re_terms = re.compile(r"(\s&&\s|\s\|\|\s)")
_re_match = re.compile(r"([\w\(\)\.,]+)\s*(==|!=)\s*(.+)")
_re_variables = re.compile(r"{% set ([\w\d]+)\s*=\s*(.*) %}")
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

    def _process_quotes(self, key: str) -> tuple[bool, str]:
        """
        Replace all quotes in the template with their escaped equivalents.

        Parameters
        ----------
        key: `str`
            The template string to process.

        Returns
        -------
        `tuple[bool, str]`
            A tuple containing a boolean indicating if the key is quoted and the
            processed key.
        """
        is_quotes = False
        quotes = ("'", '"')

        for q in quotes:
            if key.startswith(q) and key.endswith(q):
                is_quotes = True
                key = str(key[1:-1])
                break

        return is_quotes, key

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

    def _resolve_key(self, key: str) -> str | int | bool | dict | None:
        """
        Resolve a key in the context.

        It's a more simple version of `_parse_placeholder` that only handles
        simple keys, not function calls.

        Parameters
        ----------
        key: `str`
            The key to resolve.

        Returns
        -------
        `Any`
            The resolved value.
        """
        is_quotes, key = self._process_quotes(key)
        if is_quotes:
            return key  # Already a string, return as-is

        parts = key.split(".")
        current = self.context

        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
                if current is None:
                    return None
            else:
                return None

        return current

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

        # Split content into conditional blocks
        blocks = []
        conditions = [condition]

        cursor = 0
        for m in _re_blocks.finditer(content):
            start, end = m.span()
            blocks.append(content[cursor:start])
            cursor = end

            # Append matched condition (elif or else)
            if m.group(1):  # elif condition
                conditions.append(m.group(1).strip())
            else:
                conditions.append(None)  # else block

        # Final block after last {% elif %} or {% else %}
        blocks.append(content[cursor:])

        for cond, block in zip(conditions, blocks, strict=False):
            if cond is None or self._evaluate_condition(cond.strip()):
                return block.strip()

        return ""

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
        Evaluate a single comparison expression like 'user.name == "Alice"'.

        Parameters
        ----------
        term: `str`
            The comparison expression to evaluate.

        Returns
        -------
        `bool`
            The evaluated comparison result.
        """
        term = term.strip()

        # Handle `not something`
        if term.startswith("not "):
            key = term[4:].strip()
            value = self._resolve_key(key)
            return not bool(value)

        # Handle simple truthy checks
        if (
            _re_match.match(term) is None and
            (term.isidentifier() or "." in term)
        ):
            value = self._resolve_key(term)
            return bool(value)

        match_eq = _re_match.match(term)
        if not match_eq:
            return False

        left_raw, operator, right_raw = match_eq.groups()

        # Clean quotes
        _, left_clean = self._process_quotes(left_raw.strip())
        _, right_clean = self._process_quotes(right_raw.strip())

        # Try to resolve both sides from context
        left_value = self._resolve_key(left_clean)
        right_value = self._resolve_key(right_clean)

        # Fallback to raw literal if resolution failed
        if left_value is None:
            left_value = left_clean
        if right_value is None:
            right_value = right_clean

        # Try to cast both to int (safely)
        for side, value in (("left", left_value), ("right", right_value)):
            if isinstance(value, str):
                try:
                    value = float(value) if "." in value else int(value)
                except ValueError:
                    pass
            if side == "left":
                left_value = value
            else:
                right_value = value

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
