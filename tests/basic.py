from tagify import TemplateParser


def add(a, b):
    return int(a) + int(b)


def sub(a, b):
    return int(a) - int(b)


def but_add(a, b):
    return add(int(a), -int(b))


test = TemplateParser(
    context={
        "user": {
            "name": "Alice",
            "age": 30
        },
        "add": add,
        "sub": {
            "sub": sub,
            "but_add": but_add
        }
    }
)

print(
    test.render(
        """
        {% set lmao = looool %}
        {% set num = 2 %}
        {user.__init__}
        Hey there, my name is { user.name } and I am {user.age} years old
        and 1+1 = {add(1, 1)}.
        and 1-num = {sub.sub(1, num)}
        and 1a+1 (invalid) is {add(1a, 1)}
        Exception test: {namea}
        also {lmao}

        but_add: {sub.but_add(1, 1)}

        {% if 2 == num %}
            This is true!
        {% else %}
            This is false.
        {% endif %}
        """
    )
)
