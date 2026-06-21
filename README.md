# AGILANG

**AGILANG** is a lightweight programming language and application framework built for developers who want a simpler, faster, and more flexible way to build modern software.

AGILANG is designed to help users create backend systems, reactive web apps, real-time applications, blockchain-powered apps, social platforms, blogs, dashboards, APIs, and future-ready digital products without starting from heavy or complicated frameworks.

The goal is simple:

> Build powerful apps with clean syntax, reactive `.ags` templates, backend logic, live data, and portable runtime support.

---

## What is AGILANG?

AGILANG is a young but growing programming language focused on:

* Simple application development
* Backend logic
* Reactive web templates
* Live API data
* Real-time app experiences
* Blog and news platforms
* Social network starter apps
* Video feed apps
* Dating/discovery engine architecture
* Blockchain and Web3 experiments
* Portable deployment for local machines and shared hosting

AGILANG is built for users who like **simpler code, faster setup, lightweight apps, and flexible deployment**.

---

## Key Features

### 1. Simple Backend Programming

AGILANG supports backend-style programming with routes, APIs, app logic, database access, and server responses.

Example:

```agi
fn health(request):
    return json_response({
        "ok": true,
        "runtime": "agilang"
    })

app.get("/health", health)
```

---

### 2. Reactive `.ags` Templates

AGILANG uses `.ags` files as its default reactive web template format.

Instead of building pages only with static HTML, AGILANG supports reactive page structures that can load live data from APIs.

Example:

```ags
@page title="Home"
@fetch stats from "/api/home-stats"
@live stats from "/api/home-stats" every 5000

<section>
    <h1>Welcome to AGILANG</h1>
    <p>Total users: {{ stats.users }}</p>
    <p>Total posts: {{ stats.posts }}</p>
</section>
```

This allows AGILANG apps to update page data without requiring a full page refresh.

---

### 3. Live Data Support

AGILANG is designed for real-time and near-real-time app experiences.

Useful for:

* Dashboards
* Social feeds
* Notifications
* Chat systems
* Wallet balances
* Blockchain block height
* Payment activity
* Admin monitoring
* News feeds
* Video feeds

---

### 4. Full Web App Starter Kits

AGILANG includes starter app structures for:

* Blog apps
* News apps
* Social media apps
* TikTok-style short-video feeds
* Dashboard systems
* User authentication
* Profile management
* Messaging
* Follow/friend request systems
* Dating/discovery interfaces
* Blockchain/Web3 modules

The goal is to allow developers to create apps quickly with:

```bash
agilang new myapp
```

or:

```bash
agi new myapp
```

---

### 5. Portable Runtime

AGILANG is designed to be lightweight and portable.

Generated apps can include their own runtime in a local `vendor/agilang` folder so that projects can run even in hosting environments where the user may not have full server administration access.

This is useful for:

* Local development
* VPS hosting
* cPanel-style hosting
* Plesk-style hosting
* Shared hosting experiments
* Portable app bundles

---

## Example Project Structure

```text
myapp/
├─ src/
│  └─ main.agi
├─ resources/
│  ├─ views/
│  │  ├─ layout.ags
│  │  ├─ home.ags
│  │  ├─ dashboard.ags
│  │  ├─ social.ags
│  │  ├─ videos.ags
│  │  └─ dating.ags
│  └─ assets/
│     ├─ css/
│     │  └─ app.css
│     └─ js/
│        └─ ags-runtime.js
├─ storage/
│  └─ .gitkeep
├─ tests/
│  └─ test_main.agi
├─ vendor/
│  └─ agilang/
├─ public_html/
│  ├─ app.cgi
│  └─ app.fcgi
├─ passenger_wsgi.py
├─ .env.example
├─ .gitignore
└─ README.md
```

---

## Quick Start

### Create a new app

```bash
agilang new myapp
```

or:

```bash
agi new myapp
```

### Enter the project

```bash
cd myapp
```

### Run the app

```bash
agilang serve src/main.agi --host 127.0.0.1 --port 8000
```

or:

```bash
agi serve src/main.agi --8000
```

Then open:

```text
http://127.0.0.1:8000
```

---

## Run Tests

```bash
agilang test
```

or:

```bash
agi test
```

You can also run a specific test file:

```bash
agilang run tests/test_main.agi
```

---

## Why AGILANG?

AGILANG is being built for developers who want:

* A lightweight programming language
* Faster app bootstrapping
* Editable reactive templates
* Backend and frontend connection in one system
* Simple deployment
* Built-in starter kits
* Cleaner app structure
* Less framework complexity
* More control over app logic
* Future support for Web3, real-time systems, and AI/ML tooling

AGILANG is not trying to replace every language. It is designed to become a practical language for building apps quickly while keeping the project structure understandable.

---

## Current Status

AGILANG is an early-stage programming language and framework.

It is already capable of powering starter apps such as:

* Blog apps
* News apps
* Social media apps
* Reactive dashboards
* Short-video feed apps
* Basic dating/discovery apps
* API-driven web platforms

Because AGILANG is still young, developers should expect active improvements in:

* Runtime stability
* Error messages
* Documentation
* Template rendering
* Package management
* Hosting support
* Security hardening
* WebSocket/WebRTC tooling
* Blockchain tooling
* Machine learning integrations

---

## Roadmap

Planned development areas include:

* Improved `.ags` reactive template engine
* Better live data binding
* WebSocket support
* WebRTC starter modules
* Blockchain node and wallet starter kits
* Machine learning utility modules
* Package manager support
* More CLI generators
* Better shared-hosting deployment
* Production build tools
* Developer documentation
* VS Code language support
* Syntax highlighting
* Formatter and linter improvements

---

## Example Use Cases

AGILANG can be used to build:

* Personal blogs
* Company news platforms
* Social networks
* Video-sharing platforms
* Dating/discovery apps
* Admin dashboards
* Payment dashboards
* Blockchain explorers
* Web3 apps
* API services
* Internal business tools
* Lightweight SaaS platforms
* Real-time notification apps

---

## Philosophy

AGILANG follows a simple philosophy:

> Keep the language small, keep apps fast, keep templates editable, keep deployment flexible, and allow developers to build serious applications without unnecessary complexity.

---

## Contributing

AGILANG is open for contributors, testers, documentation writers, and developers who want to help grow the language.

Ways to contribute:

* Test the language
* Build starter apps
* Improve documentation
* Report bugs
* Suggest syntax improvements
* Add examples
* Improve deployment scripts
* Build `.ags` components
* Help with editor support

---

## License

This project is released under the license selected by the repository owner.

If no license is currently included, add a `LICENSE` file before public release.

---

## Project Vision

AGILANG aims to become a simple but powerful programming language for building modern apps with backend logic, reactive templates, real-time features, and portable deployment.

It is built for creators, developers, startups, students, and teams who want to build useful applications quickly while still having room to grow into more advanced systems such as blockchain, WebRTC, AI, and machine learning applications.
