
def _get_test_content():
    file_content = '''
        test:
            bar: 12
            foo: 13

        test2:
            foo: False
            bar: True
    '''

    return file_content


def _check_test_obj(cfg):
    assert cfg.test.bar == 12
    assert cfg.test.foo == 13
    assert cfg.test2.foo == False
    assert cfg.test2.bar == True


def test_data():
    file = io.StringIO(_get_test_content())
    cfg = Config.from_data(file)
    _check_test_obj(cfg)


def test_filename():
    with tempfile.NamedTemporaryFile(mode='w+') as fp:
        fp.write(_get_test_content())
        fp.flush()
        fp.seek(0)
        cfg = Config.from_file(fp.name)
        _check_test_obj(cfg)


def test_fileobj():
    with tempfile.TemporaryFile(mode='w+') as fp:
        fp.write(_get_test_content())
        fp.flush()
        fp.seek(0)
        cfg = Config.from_file(fp)
        _check_test_obj(cfg)


if __name__ == '__main__':
    test_data()
    test_filename()
    test_fileobj()
