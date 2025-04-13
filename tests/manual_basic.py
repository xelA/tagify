from tagify import TemplateParser
import random


def add(a, b):
    return int(a) + int(b)


def sub(a, b):
    return int(a) - int(b)


def but_add(a, b):
    return add(int(a), -int(b))


def random_choice(*args):
    return random.choice(args)


test = TemplateParser(
    context={
        "user": {
            "name": "Alice",
            "age": 30,
            "funny": True,
        },
        "add": add,
        "sub": {
            "sub": sub,
            "but_add": but_add
        },
        "random": {
            "randint": random.randint,
            "choice": random_choice
        }
    }
)

print(
    test.render(
        """
        {% set lmao = looool %}
        {% set num = 2 %}
        {% set rand = {random.randint(1, 100)} %}
        {user.__init__}
        Hey there, my name is { user.name } and I am {user.age} years old
        and 1+1 = {add(1, 1)}.
        and 1-num = {sub.sub(1, num)}
        and 1+rand = {add(1, {rand})}
        and 1a+1 (invalid) is {add(1a, 1)}
        Exception test: {namea}
        also {lmao}

        {random.randint(1, 100)}
        {random.choice("a,2", "b", "c", f, {lmao})}
        {missing.value}
        but_add: {sub.but_add(1, 1)}

        {% if user.funny %}Defined{% endif %}
        {% if 2 == num %}This is true!{% else %}This is false.{% endif %}
        """
    )
)
