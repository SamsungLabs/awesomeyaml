def setUpModule():
    import os
    import sys
    new_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
    sys.path = [new_path] + sys.path
    try:
        import yamlfig
    finally:
        sys.path = sys.path[1:]


def linear_f(x, *, a=1, b=0):
    return a*x + b


def cubic_f(x, *, a=1, b=0):
    return a*(x**3) + b


def square_f(x, a=1, b=0):
    return a*(x**2) + b
