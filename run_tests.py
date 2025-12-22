"""
测试运行脚本
提供便捷的测试运行方式
"""
import sys
import subprocess
import argparse


def run_tests(test_type='all', verbose=False, coverage=False):
    """运行测试"""
    cmd = ['pytest']
    
    if test_type == 'unit':
        cmd.append('tests/test_game_logic.py')
    elif test_type == 'integration':
        cmd.append('tests/test_backend_api.py')
    elif test_type == 'all':
        # pytest会自动从tests目录查找测试文件，所以也可以不指定路径
        pass  # 运行所有测试
    else:
        print(f"未知的测试类型: {test_type}")
        return False
    
    if verbose:
        cmd.append('-v')
    
    if coverage:
        cmd.extend([
            '--cov=game_logic',
            '--cov=backend',
            '--cov-report=term-missing',
            '--cov-report=html'
        ])
    
    print(f"运行命令: {' '.join(cmd)}")
    print("=" * 60)
    
    result = subprocess.run(cmd)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description='运行项目测试')
    parser.add_argument(
        '--type',
        choices=['all', 'unit', 'integration'],
        default='all',
        help='测试类型：all(全部), unit(单元测试), integration(集成测试)'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='显示详细输出'
    )
    parser.add_argument(
        '--coverage',
        action='store_true',
        help='生成代码覆盖率报告'
    )
    
    args = parser.parse_args()
    
    success = run_tests(
        test_type=args.type,
        verbose=args.verbose,
        coverage=args.coverage
    )
    
    if success:
        print("\n" + "=" * 60)
        print("✓ 所有测试通过！")
        if args.coverage:
            print("✓ 覆盖率报告已生成在 htmlcov 目录")
    else:
        print("\n" + "=" * 60)
        print("✗ 测试失败")
        sys.exit(1)


if __name__ == '__main__':
    main()

