"""
Real-world error patterns from popular development tools

This module contains authentic error patterns collected from:
- npm (Node.js package manager)
- pytest (Python testing framework)
- cargo (Rust build tool)
- maven (Java build tool)
- docker (Container platform)
- git (Version control)

Each fixture includes:
- Realistic stdout/stderr output
- Expected pattern matches
- False positive scenarios
- Success scenarios for validation
"""

from typing import Dict, List, Any


# NPM Error Patterns
NPM_ERRORS = {
    'dependency_not_found': {
        'stdout': """
npm notice
npm notice New patch version of npm available! 9.8.0 -> 9.8.1
npm notice Changelog: https://github.com/npm/cli/releases/tag/v9.8.1
npm notice Run npm install -g npm@9.8.1 to update!
npm notice
""",
        'stderr': """
npm ERR! code ENOENT
npm ERR! syscall open
npm ERR! path /Users/developer/project/package.json
npm ERR! errno -2
npm ERR! enoent ENOENT: no such file or directory, open '/Users/developer/project/package.json'
npm ERR! enoent This is related to npm not being able to find a file.
npm ERR! enoent

npm ERR! A complete log of this run can be found in:
npm ERR!     /Users/developer/.npm/_logs/2024-01-15T10_30_45_123Z-debug-0.log
""",
        'expected_patterns': ['npm ERR!', 'ENOENT', 'no such file'],
        'should_match': True,
        'error_type': 'file_not_found'
    },
    
    'build_failure': {
        'stdout': """
> my-app@1.0.0 build
> webpack --config webpack.config.js

asset main.js 125 KiB [emitted] (name: main)
runtime modules 274 bytes 1 module
cacheable modules 50.3 KiB
  ./src/index.js 2.5 KiB [built] [code generated]
  ./src/app.js 45.2 KiB [built] [code generated] [1 error]
  ./node_modules/lodash/lodash.js 2.6 KiB [built] [code generated]
""",
        'stderr': """
ERROR in ./src/app.js
Module not found: Error: Can't resolve './missing-module' in '/Users/developer/project/src'
 @ ./src/index.js 5:0-25

webpack 5.88.2 compiled with 1 error in 1234 ms
npm ERR! code 1
npm ERR! path /Users/developer/project
npm ERR! command failed
npm ERR! command sh -c webpack --config webpack.config.js

npm ERR! A complete log of this run can be found in:
npm ERR!     /Users/developer/.npm/_logs/2024-01-15T10_31_22_456Z-debug-0.log
""",
        'expected_patterns': ['npm ERR!', 'ERROR in', 'Module not found', 'compiled with .* error'],
        'should_match': True,
        'error_type': 'compilation_error'
    },
    
    'test_failure': {
        'stdout': """
> my-app@1.0.0 test
> jest --coverage

 PASS  src/__tests__/utils.test.js
 FAIL  src/__tests__/app.test.js
  ● App › should render correctly

    expect(received).toBe(expected) // Object.is equality

    Expected: 200
    Received: 404

      15 |   it('should render correctly', () => {
      16 |     const response = app.get('/');
    > 17 |     expect(response.status).toBe(200);
         |                             ^
      18 |   });

      at Object.<anonymous> (src/__tests__/app.test.js:17:29)

Test Suites: 1 failed, 1 passed, 2 total
Tests:       1 failed, 5 passed, 6 total
Snapshots:   0 total
Time:        2.345 s
""",
        'stderr': """
npm ERR! code 1
npm ERR! path /Users/developer/project
npm ERR! command failed
npm ERR! command sh -c jest --coverage

npm ERR! A complete log of this run can be found in:
npm ERR!     /Users/developer/.npm/_logs/2024-01-15T10_32_00_789Z-debug-0.log
""",
        'expected_patterns': ['FAIL', 'Test Suites: .* failed', 'npm ERR!'],
        'should_match': True,
        'error_type': 'test_failure'
    },
    
    'success_with_warnings': {
        'stdout': """
> my-app@1.0.0 build
> webpack --config webpack.config.js

asset main.js 125 KiB [emitted] (name: main)
runtime modules 274 bytes 1 module
cacheable modules 50.3 KiB

WARNING in asset size limit: The following asset(s) exceed the recommended size limit (244 KiB).
This can impact web performance.
Assets: 
  main.js (125 KiB)

WARNING in webpack performance recommendations: 
You can limit the size of your bundles by using import() or require.ensure to lazy load some parts of your application.
For more info visit https://webpack.js.org/guides/code-splitting/

webpack 5.88.2 compiled with 2 warnings in 1234 ms
""",
        'stderr': "",
        'expected_patterns': ['WARNING', 'compiled with .* warnings'],
        'should_match': False,  # Warnings, not errors
        'error_type': 'success_with_warnings'
    }
}


# Pytest Error Patterns
PYTEST_ERRORS = {
    'test_failures': {
        'stdout': """
============================= test session starts ==============================
platform darwin -- Python 3.10.0, pytest-7.4.0, pluggy-1.2.0
rootdir: /Users/developer/project
collected 8 items

tests/test_utils.py ...                                                   [ 37%]
tests/test_models.py F..                                                  [ 75%]
tests/test_views.py FF                                                    [100%]

=================================== FAILURES ===================================
_______________________________ test_user_login ________________________________

    def test_user_login():
        response = client.post('/login', json={'username': 'test', 'password': 'wrong'})
>       assert response.status_code == 200
E       AssertionError: assert 401 == 200
E        +  where 401 = <Response [401]>.status_code

tests/test_views.py:45: AssertionError
______________________________ test_create_user _______________________________

    def test_create_user():
        data = {'username': 'newuser', 'email': 'test@example.com'}
        response = client.post('/users', json=data)
>       assert response.json()['id'] is not None
E       KeyError: 'id'

tests/test_views.py:52: KeyError
=========================== short test summary info ============================
FAILED tests/test_views.py::test_user_login - AssertionError: assert 401 == 200
FAILED tests/test_views.py::test_create_user - KeyError: 'id'
========================= 3 passed, 2 failed in 2.34s ==========================
""",
        'stderr': "",
        'expected_patterns': ['FAILED', 'AssertionError', 'passed, .* failed'],
        'should_match': True,
        'error_type': 'test_failure'
    },
    
    'import_error': {
        'stdout': """
============================= test session starts ==============================
platform darwin -- Python 3.10.0, pytest-7.4.0, pluggy-1.2.0
rootdir: /Users/developer/project
collected 0 items / 1 error

==================================== ERRORS ====================================
__________________ ERROR collecting tests/test_models.py _______________________
ImportError while importing test module '/Users/developer/project/tests/test_models.py'.
Hint: make sure your test modules/classes/functions follow the naming convention
tests/test_models.py:5: in <module>
    from app.models import User, Product
E   ModuleNotFoundError: No module named 'app.models'
=========================== short test summary info ============================
ERROR tests/test_models.py
!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
=============================== 1 error in 0.12s ===============================
""",
        'stderr': "",
        'expected_patterns': ['ERROR', 'ModuleNotFoundError', 'ImportError'],
        'should_match': True,
        'error_type': 'import_error'
    },
    
    'all_passed': {
        'stdout': """
============================= test session starts ==============================
platform darwin -- Python 3.10.0, pytest-7.4.0, pluggy-1.2.0
rootdir: /Users/developer/project
plugins: cov-4.1.0, django-4.5.2
collected 15 items

tests/test_utils.py .....                                                 [ 33%]
tests/test_models.py .....                                                [ 66%]
tests/test_views.py .....                                                 [100%]

---------- coverage: platform darwin, python 3.10.0-final-0 ----------
Name                     Stmts   Miss  Cover
--------------------------------------------
app/__init__.py             12      0   100%
app/models.py               45      2    96%
app/views.py                67      5    93%
--------------------------------------------
TOTAL                      124      7    94%

============================== 15 passed in 3.45s ===============================
""",
        'stderr': "",
        'expected_patterns': [],
        'should_match': False,  # All tests passed
        'error_type': 'success'
    }
}


# Cargo (Rust) Error Patterns
CARGO_ERRORS = {
    'compilation_error': {
        'stdout': """
   Compiling my-rust-app v0.1.0 (/Users/developer/project)
""",
        'stderr': """
error[E0425]: cannot find value `undefined_variable` in this scope
  --> src/main.rs:12:13
   |
12 |     println!("{}", undefined_variable);
   |                    ^^^^^^^^^^^^^^^^^^ not found in this scope

error[E0308]: mismatched types
  --> src/main.rs:25:24
   |
25 |     let result: i32 = "hello";
   |                 ---   ^^^^^^^ expected `i32`, found `&str`
   |                 |
   |                 expected due to this

error: aborting due to 2 previous errors

For more information about this error, try `rustc --explain E0425`.
error: could not compile `my-rust-app` due to 2 previous errors
""",
        'expected_patterns': ['error\\[E[0-9]+\\]', 'aborting due to', 'could not compile'],
        'should_match': True,
        'error_type': 'compilation_error'
    },
    
    'test_failure': {
        'stdout': """
   Compiling my-rust-app v0.1.0 (/Users/developer/project)
    Finished test [unoptimized + debuginfo] target(s) in 2.34s
     Running unittests src/lib.rs (target/debug/deps/my_rust_app-abc123)

running 5 tests
test tests::test_addition ... ok
test tests::test_subtraction ... ok
test tests::test_multiplication ... FAILED
test tests::test_division ... ok
test tests::test_modulo ... FAILED

failures:

---- tests::test_multiplication stdout ----
thread 'tests::test_multiplication' panicked at 'assertion failed: `(left == right)`
  left: `15`,
 right: `20`', src/lib.rs:45:9
note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace

---- tests::test_modulo stdout ----
thread 'tests::test_modulo' panicked at 'attempt to divide by zero', src/lib.rs:67:18

failures:
    tests::test_modulo
    tests::test_multiplication

test result: FAILED. 3 passed; 2 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s

error: test failed, to rerun pass `--lib`
""",
        'stderr': "",
        'expected_patterns': ['test result: FAILED', 'panicked at', 'error: test failed'],
        'should_match': True,
        'error_type': 'test_failure'
    }
}


# Docker Error Patterns
DOCKER_ERRORS = {
    'build_failure': {
        'stdout': """
Sending build context to Docker daemon  125.4MB
Step 1/8 : FROM node:18-alpine
 ---> abc123def456
Step 2/8 : WORKDIR /app
 ---> Using cache
 ---> def456ghi789
Step 3/8 : COPY package*.json ./
 ---> Using cache
 ---> ghi789jkl012
Step 4/8 : RUN npm ci --only=production
 ---> Running in mno345pqr678
""",
        'stderr': """
npm ERR! code ENOENT
npm ERR! syscall open
npm ERR! path /app/package.json
npm ERR! errno -2
npm ERR! enoent ENOENT: no such file or directory, open '/app/package.json'

npm ERR! A complete log of this run can be found in:
npm ERR!     /root/.npm/_logs/2024-01-15T10_35_00_123Z-debug-0.log
The command '/bin/sh -c npm ci --only=production' returned a non-zero code: 254
""",
        'expected_patterns': ['npm ERR!', 'returned a non-zero code'],
        'should_match': True,
        'error_type': 'build_failure'
    },
    
    'container_not_found': {
        'stdout': "",
        'stderr': """
Error: No such container: my-app-container
""",
        'expected_patterns': ['Error:', 'No such container'],
        'should_match': True,
        'error_type': 'container_not_found'
    }
}


# Maven (Java) Error Patterns
MAVEN_ERRORS = {
    'compilation_error': {
        'stdout': """
[INFO] Scanning for projects...
[INFO] 
[INFO] -------------------< com.example:my-java-app >-------------------
[INFO] Building my-java-app 1.0-SNAPSHOT
[INFO] --------------------------------[ jar ]---------------------------------
[INFO] 
[INFO] --- maven-compiler-plugin:3.8.0:compile (default-compile) @ my-java-app ---
[INFO] Changes detected - recompiling the module!
[INFO] Compiling 15 source files to /Users/developer/project/target/classes
""",
        'stderr': """
[ERROR] /Users/developer/project/src/main/java/com/example/App.java:[25,16] cannot find symbol
  symbol:   variable undefinedVar
  location: class com.example.App
[ERROR] /Users/developer/project/src/main/java/com/example/Utils.java:[42,12] incompatible types: java.lang.String cannot be converted to int
[INFO] ------------------------------------------------------------------------
[INFO] BUILD FAILURE
[INFO] ------------------------------------------------------------------------
[INFO] Total time:  2.345 s
[INFO] Finished at: 2024-01-15T10:40:00-08:00
[INFO] ------------------------------------------------------------------------
[ERROR] Failed to execute goal org.apache.maven.plugins:maven-compiler-plugin:3.8.0:compile (default-compile) on project my-java-app: Compilation failure: Compilation failure: 
[ERROR] /Users/developer/project/src/main/java/com/example/App.java:[25,16] cannot find symbol
[ERROR] /Users/developer/project/src/main/java/com/example/Utils.java:[42,12] incompatible types: java.lang.String cannot be converted to int
[ERROR] -> [Help 1]
""",
        'expected_patterns': ['\\[ERROR\\]', 'BUILD FAILURE', 'Compilation failure'],
        'should_match': True,
        'error_type': 'compilation_error'
    },
    
    'test_failure': {
        'stdout': """
[INFO] --- maven-surefire-plugin:2.22.0:test (default-test) @ my-java-app ---
[INFO] 
[INFO] -------------------------------------------------------
[INFO]  T E S T S
[INFO] -------------------------------------------------------
[INFO] Running com.example.AppTest
[ERROR] Tests run: 5, Failures: 2, Errors: 0, Skipped: 0, Time elapsed: 1.234 s <<< FAILURE! - in com.example.AppTest
[ERROR] testUserLogin(com.example.AppTest)  Time elapsed: 0.123 s  <<< FAILURE!
java.lang.AssertionError: expected: <200> but was: <404>
	at org.junit.Assert.fail(Assert.java:88)
	at com.example.AppTest.testUserLogin(AppTest.java:45)

[ERROR] testCreateUser(com.example.AppTest)  Time elapsed: 0.098 s  <<< FAILURE!
java.lang.NullPointerException: Cannot invoke "User.getId()" because "user" is null
	at com.example.AppTest.testCreateUser(AppTest.java:52)

[INFO] 
[INFO] Results:
[INFO] 
[ERROR] Failures: 
[ERROR]   AppTest.testUserLogin:45 expected: <200> but was: <404>
[ERROR]   AppTest.testCreateUser:52 NullPointerException
[INFO] 
[ERROR] Tests run: 5, Failures: 2, Errors: 0, Skipped: 0
[INFO] 
[INFO] ------------------------------------------------------------------------
[INFO] BUILD FAILURE
[INFO] ------------------------------------------------------------------------
""",
        'stderr': "",
        'expected_patterns': ['\\[ERROR\\] Tests run:', 'Failures:', 'BUILD FAILURE'],
        'should_match': True,
        'error_type': 'test_failure'
    }
}


# All fixtures combined
ALL_FIXTURES = {
    'npm': NPM_ERRORS,
    'pytest': PYTEST_ERRORS,
    'cargo': CARGO_ERRORS,
    'docker': DOCKER_ERRORS,
    'maven': MAVEN_ERRORS
}


def get_fixture(tool: str, scenario: str) -> Dict[str, Any]:
    """Get a specific test fixture"""
    return ALL_FIXTURES.get(tool, {}).get(scenario, {})


def get_all_error_fixtures() -> List[Dict[str, Any]]:
    """Get all error fixtures (should_match=True)"""
    fixtures = []
    for tool, scenarios in ALL_FIXTURES.items():
        for scenario_name, fixture in scenarios.items():
            if fixture.get('should_match'):
                fixture['tool'] = tool
                fixture['scenario'] = scenario_name
                fixtures.append(fixture)
    return fixtures


def get_all_success_fixtures() -> List[Dict[str, Any]]:
    """Get all success fixtures (should_match=False)"""
    fixtures = []
    for tool, scenarios in ALL_FIXTURES.items():
        for scenario_name, fixture in scenarios.items():
            if not fixture.get('should_match'):
                fixture['tool'] = tool
                fixture['scenario'] = scenario_name
                fixtures.append(fixture)
    return fixtures

