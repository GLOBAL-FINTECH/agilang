# AGILANG AGS Template Deep Reference

AGS templates are the view layer for AGILANG web apps. They are used to render pages, layouts, dashboards, forms, and error screens.

This guide teaches how to structure `.ags` files professionally, how to pass data into templates, how to handle escaping, and how to design pages for full-stack AGILANG apps.

---

## 1. What AGS is

AGS files are template files:

```text
resources/views/home.ags
resources/views/layout.ags
resources/views/login.ags
resources/views/dashboard.ags
resources/views/errors/404.ags
```

They are normally rendered from controllers:

```agi
fn home(request):
    return render_ags("home.ags", {
        "title": "Home",
        "user": null
    })
```

---

## 2. Basic page

```ags
@page home
@layout layout.ags

<h1>{{ title }}</h1>
<p>Welcome to AGILANG.</p>
```

Meaning:

```text
@page      declares the template/page name
@layout    tells AGS which layout to use
{{ }}      prints escaped values
```

---

## 3. Layouts

A layout defines the shared HTML shell.

`resources/views/layout.ags`:

```ags
<!doctype html>
<html>
<head>
    <title>{{ title }}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
    <header>
        <nav>
            <a href="/">Home</a>
            <a href="/dashboard">Dashboard</a>
            <a href="/login">Login</a>
        </nav>
    </header>

    <main>
        {{ content }}
    </main>

    <footer>
        <p>Powered by AGILANG</p>
    </footer>
</body>
</html>
```

A page using that layout:

```ags
@page dashboard
@layout layout.ags

<h1>{{ title }}</h1>
<p>Welcome back, {{ user.name }}</p>
```

---

## 4. Escaped output

Use escaped output for user-controlled data:

```ags
{{ user.name }}
{{ message }}
{{ title }}
```

Escaped output helps prevent script injection.

Example:

```ags
<p>{{ comment.body }}</p>
```

If a user writes HTML in a comment, it should display as text, not execute.

---

## 5. Raw trusted HTML

Use raw HTML only for content you fully trust and sanitize.

```ags
{{{ trusted_html }}}
```

Do not use raw output for:

```text
comments
profile bios
chat messages
uploaded content
external API content
```

Good use:

```ags
{{{ admin_configured_footer_html }}}
```

Only if sanitized and controlled by trusted administrators.

---

## 6. Passing data from controller to template

Controller:

```agi
fn profile(request):
    let user = find_user_by_id(request.params("id"))
    return render_ags("profile.ags", {
        "title": "User Profile",
        "user": user
    })
```

Template:

```ags
@page profile
@layout layout.ags

<h1>{{ user.name }}</h1>
<p>{{ user.email }}</p>
```

---

## 7. Recommended template data shape

Use predictable keys:

```agi
return render_ags("dashboard.ags", {
    "title": "Dashboard",
    "auth": {
        "user": user,
        "logged_in": true
    },
    "flash": flash_messages,
    "errors": errors,
    "data": dashboard_data
})
```

This makes templates easier to understand.

---

## 8. Forms in AGS

Login page:

```ags
@page login
@layout layout.ags

<h1>{{ title }}</h1>

<form method="POST" action="/login">
    <label>Email</label>
    <input type="email" name="email" value="{{ old.email }}" required>

    <label>Password</label>
    <input type="password" name="password" required>

    <button type="submit">Login</button>
</form>

<p>{{ error }}</p>
```

Controller:

```agi
fn login_page(request):
    return render_ags("login.ags", {
        "title": "Login",
        "old": {"email": ""},
        "error": ""
    })
```

---

## 9. Validation errors in templates

Controller:

```agi
if len(errors) > 0:
    return render_ags("register.ags", {
        "title": "Register",
        "errors": errors,
        "old": data
    }, 422)
```

Template pattern:

```ags
<p class="error">{{ errors.email }}</p>
<p class="error">{{ errors.password }}</p>
```

Professional rule: always return old form values except passwords.

---

## 10. Flash messages

Controller after successful action:

```agi
request.session_set("flash_success", "Profile updated")
return redirect("/dashboard")
```

Dashboard template:

```ags
<p class="success">{{ flash.success }}</p>
```

---

## 11. Error templates

404 page:

```ags
@page errors.404
@layout layout.ags

<h1>404 - Page not found</h1>
<p>The page you requested does not exist.</p>
<a href="/">Go home</a>
```

500 page:

```ags
@page errors.500
@layout layout.ags

<h1>500 - Server error</h1>
<p>Something went wrong. The error has been logged.</p>
<a href="/">Go home</a>
```

422 page/form error:

```ags
@page errors.422
@layout layout.ags

<h1>Validation error</h1>
<p>Please check your form and try again.</p>
```

---

## 12. Dashboard layout example

```ags
@page dashboard
@layout layout.ags

<section class="stats">
    <div>
        <h2>{{ stats.users }}</h2>
        <p>Users</p>
    </div>
    <div>
        <h2>{{ stats.transactions }}</h2>
        <p>Transactions</p>
    </div>
    <div>
        <h2>{{ stats.revenue }}</h2>
        <p>Revenue</p>
    </div>
</section>
```

Controller:

```agi
fn dashboard(request):
    return render_ags("dashboard.ags", {
        "title": "Dashboard",
        "stats": {
            "users": 120,
            "transactions": 450,
            "revenue": "K 15,000"
        }
    })
```

---

## 13. Template components pattern

If component/partial support is available in your runtime version, organize files like this:

```text
resources/views/components/navbar.ags
resources/views/components/footer.ags
resources/views/components/alert.ags
```

If partial includes are not available yet, render common sections through layouts and keep repeated HTML minimal.

---

## 14. Template logic boundary

Some template engines support loops and conditions inside templates. If your current AGS runtime version does not document loop syntax clearly, prefer preparing display-ready data in controllers.

Controller-prepared example:

```agi
let rows_html = ""
for user in users:
    rows_html = rows_html + "<tr><td>" + escape(user["name"]) + "</td></tr>"

return render_ags("users.ags", {
    "title": "Users",
    "rows_html": rows_html
})
```

Template:

```ags
<table>
    {{{ rows_html }}}
</table>
```

Important: only use raw HTML if you escape values before building it.

---

## 15. Safe page pattern

Professional template checklist:

```text
[ ] Use layout
[ ] Escape user data with {{ }}
[ ] Avoid raw HTML unless sanitized
[ ] Show validation errors clearly
[ ] Preserve old form input safely
[ ] Do not show passwords or secrets
[ ] Use semantic HTML
[ ] Add mobile viewport meta tag
[ ] Use consistent navigation
[ ] Add custom 404 and 500 pages
```

---

## 16. Complete page example

Controller:

```agi
fn users_index(request):
    let users = db.all("SELECT id, name, email FROM users ORDER BY id DESC", [])
    return render_ags("users/index.ags", {
        "title": "Users",
        "users": users,
        "error": ""
    })
```

Template:

```ags
@page users.index
@layout layout.ags

<h1>{{ title }}</h1>
<a href="/users/create">Create user</a>

<div>
    {{ error }}
</div>

<p>Render user rows using the supported AGS loop syntax for your runtime version, or pre-render safe row HTML in the controller.</p>
```

---

## Final AGS rule

AGS should remain simple. Controllers should prepare data. Templates should display data. Business logic belongs in services/controllers, not in HTML files.
