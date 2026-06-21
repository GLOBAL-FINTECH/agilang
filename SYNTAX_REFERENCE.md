# AGILANG Syntax Reference

This reference reflects the current AGILANG translator surface.

## Comments

```agi
# Comment
```

## Imports

```agi
import "config.agi"
import "routes/web.agi"
import os
```

Use string imports for `.agi` files. The translator inlines imported `.agi` files before execution.

## Functions

```agi
fn name(param: string) -> string:
    return "Hello " + param
```

Accepted variants:

```agi
export fn public_api():
    return True

pub fn module_fn():
    return True
```

## Variables

```agi
let name = "AGILANG"
let total: i32 = 10
const APP_NAME = "My App"
```

## Types

Common aliases:

```text
i8 i16 i32 i64 -> int
u8 u16 u32 u64 -> int
f32 f64 -> float
str string -> str
bool -> bool
any -> Any
void none -> None
list -> list
dict -> dict
```

## Type Alias

```agi
type UserId = i64
let id: UserId = 1
```

## Struct

```agi
struct User:
    id: i32
    name: string
```

The translator lowers structs to Python dataclasses.

## Enum

```agi
enum Status:
    DRAFT
    PUBLISHED
```

Bare uppercase enum members are converted to `auto()`.

## Conditionals

```agi
if ok:
    print("yes")
elif retry:
    print("retry")
else:
    print("no")
```

## Loops

```agi
for item in items:
    print(item)

while running:
    print("tick")
```

## Try/Except

```agi
try:
    run_task()
except Exception as exc:
    print(str(exc))
```

## Dictionaries and Lists

```agi
let user = {"name": "Amina", "role": "admin"}
let names = ["Amina", "John"]
```

## Return Type Best Practice

Add return types to helper functions to reduce static-check warnings:

```agi
fn is_admin(role) -> bool:
    return role == "admin"

fn normalize_role(role) -> string:
    if role == "admin":
        return "admin"
    return "member"
```
