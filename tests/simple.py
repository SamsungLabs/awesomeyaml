


def test_config():
    data = {
        'test': 1,
        'test2': 12,
        'test3': False,
        'test4': {
            'foo': 'placki',
            'bar': [ 'A', 'B', 'C']
        }
    }

    cfg = Config(data)
    assert cfg.test == 1
    assert cfg.test2 == 12
    assert cfg.test3 == False
    assert cfg.test4['foo'] == 'placki'
    assert cfg.test4.bar[1] == 'B'
    assert 'test' in cfg
    
    cfg.test = (1, 2)
    assert cfg['test'] == (1,2)

    del cfg.test2
    assert 'test2' not in cfg

    cfg.test2 = 13
    assert cfg['test2'] == cfg.text2 == 12


if __name__ == '__main__':
    test_config()
