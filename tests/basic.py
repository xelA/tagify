from tagify import TemplateParser


def add(a, b):
    return int(a) + int(b)


test = TemplateParser(
    context={
        "name": "Alice"
    },
    functions={
        "add": add
    }
)

print(
    test.render(
        """
        Hey there, my name is {name}, and 1+1 = {add(1a, 1)}.
        Exception test: {namea}

        {% if 3 == 3 %}
            This is true!
        {% else %}
            This is false.
        {% endif %}
        """
    )
)
