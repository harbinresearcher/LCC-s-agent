from calc import add, sub, mul, div


def test_add():
    assert add(1, 2) == 3
    assert add(-1, 1) == 0
    assert add(2.5, 2.5) == 5.0


def test_sub():
    assert sub(5, 3) == 2
    assert sub(0, 0) == 0
    assert sub(2.5, 0.5) == 2.0


def test_mul():
    assert mul(3, 4) == 12
    assert mul(-2, 3) == -6
    assert mul(0, 100) == 0


def test_div():
    assert div(10, 2) == 5
    assert div(7, 2) == 3.5
    assert div(-6, 3) == -2


def test_div_by_zero():
    try:
        div(1, 0)
    except ZeroDivisionError:
        pass
    else:
        raise AssertionError("div by zero should raise ZeroDivisionError")


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"{name} PASSED")
    print("ALL TESTS PASSED")
