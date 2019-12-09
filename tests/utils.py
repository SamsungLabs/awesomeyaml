def setUpModule():
    import os
    import sys
    new_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
    sys.path = [new_path] + sys.path
    try:
        import yamlfig
    finally:
        sys.path = sys.path[1:]
