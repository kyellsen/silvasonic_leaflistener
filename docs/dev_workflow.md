# Development Workflow

Silvasonic employs a **hybrid Cross-Architecture** workflow.

- **Development Host**: x86_64 (e.g., ThinkPad, Cloud VM).
- **Target Target**: aarch64 (Raspberry Pi 5).

## 1. The Environment (Simple & Flexible)

You can choose either path. Both use the same `setup.sh` and create a `.venv` folder.

### Option A: Local (Fastest on Fedora)

Since you are on Linux, you can run directly on your host.

1. **Bootstrap**: Run `./setup.sh` -> Creates `.venv`.
2. **Develop**: `source .venv/bin/activate` or let VS Code auto-detect it.

### Option B: DevContainer (Cleanest)

Isolates dependencies from your Fedora system.

1. Open VS Code -> "Reopen in Container".
2. The container automatically runs `./setup.sh` for you.
3. You are ready instantly.

**Why both?**

- `setup.sh` is the universal "Init" script.
- `.venv` ensures we never mess up your system python, even inside a container.

## 2. Toolchain Standard

We enforce strict quality gates using `uv`, `ruff`, and `mypy`.

- **Format**: `uv run ruff format`
- **Lint**: `uv run ruff check --fix`
- **Type Check**: `uv run mypy .`
- **Test**: `uv run pytest`

## 3. Building for Raspberry Pi (ARM64)

Since we develop on x86, we must cross-compile for the Pi.

**Using Podman**:

```bash
podman build --platform linux/arm64 -t silvasonic/recorder .
```

This requires `qemu-user-static` installed on your host system to emulate ARM64 instructions.
