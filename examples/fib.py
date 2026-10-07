def fib(n: int) -> int:
    """返回斐波那契数列的第 n 项，n 从 0 开始。

    fib(0) = 0
    fib(1) = 1
    fib(n) = fib(n-1) + fib(n-2)
    """
    if not isinstance(n, int) or isinstance(n, bool):
        raise TypeError("n 必须是整数")
    if n < 0:
        raise ValueError("n 必须是非负整数")
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def run_tests():
    # (输入 n, 期望结果)
    cases = [
        (0, 0),
        (1, 1),
        (2, 1),
        (3, 2),
        (4, 3),
        (5, 5),
        (6, 8),
        (7, 13),
        (10, 55),
        (20, 6765),
        (30, 832040),
        (50, 12586269025),
    ]

    passed = 0
    failed = 0
    print("=" * 50)
    print("斐波那契数列测试")
    print("=" * 50)
    for n, expected in cases:
        got = fib(n)
        ok = got == expected
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1
        print(f"[{status}] fib({n}) = {got}  (期望 {expected})")

    # 边界 / 异常测试
    print("-" * 50)
    print("边界与异常测试")

    try:
        fib(-1)
        print("[FAIL] fib(-1) 应该抛出 ValueError")
        failed += 1
    except ValueError:
        print("[PASS] fib(-1) 正确抛出 ValueError")
        passed += 1

    try:
        fib(1.5)
        print("[FAIL] fib(1.5) 应该抛出 TypeError")
        failed += 1
    except TypeError:
        print("[PASS] fib(1.5) 正确抛出 TypeError")
        passed += 1

    print("=" * 50)
    print(f"总计: {passed} 通过, {failed} 失败")
    print("=" * 50)
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    raise SystemExit(0 if success else 1)
# tested by mini_agent
